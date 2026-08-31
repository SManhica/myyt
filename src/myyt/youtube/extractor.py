from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from myyt.exceptions import ExtractionError, VideoUnavailableError
from myyt.models import VideoInfo

from .client import YouTubeClient
from .url_parser import ParsedVideoURL, parse_video_url

_PLAYER_RESPONSE_MARKERS = (
    re.compile(r"(?:var\s+)?ytInitialPlayerResponse\s*=\s*"),
    re.compile(r"window\[['\"]ytInitialPlayerResponse['\"]\]\s*=\s*"),
)


class YouTubeExtractor:
    def __init__(self, client: YouTubeClient | None = None) -> None:
        self.client = client or YouTubeClient()

    def extract(self, url: str) -> VideoInfo:
        parsed = parse_video_url(url)
        html = self.client.get_text(
            parsed.webpage_url,
            params={"hl": "en"},
            headers={"Cookie": "SOCS=CAI; PREF=hl=en"},
        )
        player_response = extract_initial_player_response(html)
        return normalize_video_info(player_response, parsed)


def extract_initial_player_response(html: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for marker in _PLAYER_RESPONSE_MARKERS:
        for match in marker.finditer(html):
            try:
                decoded, _ = decoder.raw_decode(html, match.end())
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                return decoded
    raise ExtractionError("the watch page did not contain a usable player response")


def normalize_video_info(
    player_response: Mapping[str, Any], parsed: ParsedVideoURL
) -> VideoInfo:
    details = _mapping(player_response.get("videoDetails"))
    microformat = _player_microformat(player_response)
    playability = _mapping(player_response.get("playabilityStatus"))

    response_video_id = _string(details.get("videoId")) or _string(microformat.get("videoId"))
    if response_video_id and response_video_id != parsed.video_id:
        raise ExtractionError("the player response belongs to a different video")

    title = _string(details.get("title")) or _simple_text(microformat.get("title"))
    if not title:
        status = _string(playability.get("status"))
        reason = _string(playability.get("reason"))
        if status and status != "OK":
            raise VideoUnavailableError(reason or f"YouTube reported {status.lower()}")
        raise ExtractionError("the player response is missing the video title")

    channel = _string(details.get("author")) or _string(microformat.get("ownerChannelName"))
    channel_id = _string(details.get("channelId")) or _string(
        microformat.get("externalChannelId")
    )
    duration = _duration_seconds(details.get("lengthSeconds"))
    if duration is None:
        duration = _duration_seconds(microformat.get("lengthSeconds"))

    thumbnails = _thumbnails(details.get("thumbnail"))
    if not thumbnails:
        thumbnails = _thumbnails(microformat.get("thumbnail"))

    return VideoInfo(
        video_id=parsed.video_id,
        title=title,
        channel=channel,
        channel_id=channel_id,
        duration=duration,
        thumbnail=_best_thumbnail(thumbnails),
        webpage_url=parsed.webpage_url,
    )


def _player_microformat(player_response: Mapping[str, Any]) -> Mapping[str, Any]:
    microformat = _mapping(player_response.get("microformat"))
    return _mapping(microformat.get("playerMicroformatRenderer"))


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _simple_text(value: object) -> str | None:
    mapping = _mapping(value)
    simple = _string(mapping.get("simpleText"))
    if simple:
        return simple
    runs = mapping.get("runs")
    if not isinstance(runs, Sequence) or isinstance(runs, (str, bytes)):
        return None
    parts = [_string(_mapping(run).get("text")) for run in runs]
    combined = "".join(part for part in parts if part)
    return combined or None


def _duration_seconds(value: object) -> int | None:
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _thumbnails(value: object) -> list[Mapping[str, Any]]:
    items = _mapping(value).get("thumbnails")
    if not isinstance(items, list):
        return []
    return [_mapping(item) for item in items if isinstance(item, Mapping)]


def _best_thumbnail(thumbnails: list[Mapping[str, Any]]) -> str | None:
    usable = [item for item in thumbnails if _string(item.get("url"))]
    if not usable:
        return None

    def size(item: Mapping[str, Any]) -> tuple[int, int, int]:
        width = item.get("width") if isinstance(item.get("width"), int) else 0
        height = item.get("height") if isinstance(item.get("height"), int) else 0
        return width * height, width, height

    url = _string(max(usable, key=size).get("url"))
    if url and url.startswith("//"):
        return f"https:{url}"
    return url
