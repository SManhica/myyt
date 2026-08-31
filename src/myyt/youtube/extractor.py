from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from myyt.exceptions import ExtractionError, VideoUnavailableError
from myyt.models import VideoInfo

from .client import YouTubeClient
from .parsing import (
    as_mapping,
    as_string,
    best_thumbnail_url,
    decimal_seconds,
    decode_json_object_after_markers,
    text_value,
)
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
    decoded = decode_json_object_after_markers(html, _PLAYER_RESPONSE_MARKERS)
    if decoded is not None:
        return decoded
    raise ExtractionError("the watch page did not contain a usable player response")


def normalize_video_info(
    player_response: Mapping[str, Any], parsed: ParsedVideoURL
) -> VideoInfo:
    details = as_mapping(player_response.get("videoDetails"))
    microformat = _player_microformat(player_response)
    playability = as_mapping(player_response.get("playabilityStatus"))

    response_video_id = as_string(details.get("videoId")) or as_string(
        microformat.get("videoId")
    )
    if response_video_id and response_video_id != parsed.video_id:
        raise ExtractionError("the player response belongs to a different video")

    title = as_string(details.get("title")) or text_value(microformat.get("title"))
    if not title:
        status = as_string(playability.get("status"))
        reason = as_string(playability.get("reason"))
        if status and status != "OK":
            raise VideoUnavailableError(reason or f"YouTube reported {status.lower()}")
        raise ExtractionError("the player response is missing the video title")

    channel = as_string(details.get("author")) or as_string(
        microformat.get("ownerChannelName")
    )
    channel_id = as_string(details.get("channelId")) or as_string(
        microformat.get("externalChannelId")
    )
    duration = decimal_seconds(details.get("lengthSeconds"))
    if duration is None:
        duration = decimal_seconds(microformat.get("lengthSeconds"))
    thumbnail = best_thumbnail_url(details.get("thumbnail")) or best_thumbnail_url(
        microformat.get("thumbnail")
    )

    return VideoInfo(
        video_id=parsed.video_id,
        title=title,
        channel=channel,
        channel_id=channel_id,
        duration=duration,
        thumbnail=thumbnail,
        webpage_url=parsed.webpage_url,
    )


def _player_microformat(player_response: Mapping[str, Any]) -> Mapping[str, Any]:
    microformat = as_mapping(player_response.get("microformat"))
    return as_mapping(microformat.get("playerMicroformatRenderer"))
