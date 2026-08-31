from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from myyt.exceptions import FormatExtractionError

from .client import YouTubeClient
from .client_context import WebClientConfig, extract_web_client_config
from .parsing import as_mapping, as_string

_PLAYER_API_URL = "https://www.youtube.com/youtubei/v1/player"


@dataclass(frozen=True, slots=True)
class PlayerClientProfile:
    name: str
    version: str
    header_name: str
    user_agent: str
    fields: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ResolvedPlayerResponse:
    response: Mapping[str, Any]
    client_name: str


_PLAYER_CLIENTS = (
    PlayerClientProfile(
        name="ANDROID",
        version="20.10.38",
        header_name="3",
        user_agent="com.google.android.youtube/20.10.38 (Linux; U; Android 11) gzip",
        fields={"androidSdkVersion": 30},
    ),
    PlayerClientProfile(
        name="IOS",
        version="20.10.4",
        header_name="5",
        user_agent="com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3_1 like Mac OS X)",
        fields={
            "deviceMake": "Apple",
            "deviceModel": "iPhone16,2",
            "osName": "iPhone",
            "osVersion": "18.3.1.22D72",
        },
    ),
)


class YouTubePlayer:
    def __init__(self, client: YouTubeClient | None = None) -> None:
        self.client = client or YouTubeClient()

    def resolve(
        self,
        video_id: str,
        watch_html: str,
        initial_response: Mapping[str, Any],
    ) -> ResolvedPlayerResponse:
        if _has_direct_audio_url(initial_response):
            return ResolvedPlayerResponse(initial_response, "WEB")

        config = extract_web_client_config(watch_html)
        if config is None:
            raise FormatExtractionError(
                "the watch page omitted player client configuration required for formats"
            )

        failure_reasons: list[str] = []
        for profile in _PLAYER_CLIENTS:
            response = self._request_player(video_id, profile, config)
            if _has_direct_audio_url(response):
                return ResolvedPlayerResponse(response, profile.name)
            playability = as_mapping(response.get("playabilityStatus"))
            status = as_string(playability.get("status")) or "unknown"
            reason = as_string(playability.get("reason"))
            failure_reasons.append(f"{profile.name}: {reason or status}")

        detail = "; ".join(failure_reasons)
        raise FormatExtractionError(
            f"no player client returned a directly usable audio URL ({detail})"
        )

    def _request_player(
        self,
        video_id: str,
        profile: PlayerClientProfile,
        config: WebClientConfig,
    ) -> dict[str, Any]:
        client_context: dict[str, Any] = {
            "clientName": profile.name,
            "clientVersion": profile.version,
            "hl": "en",
            "gl": "US",
            **profile.fields,
        }
        if config.visitor_data:
            client_context["visitorData"] = config.visitor_data
        headers = {
            "User-Agent": profile.user_agent,
            "X-YouTube-Client-Name": profile.header_name,
            "X-YouTube-Client-Version": profile.version,
        }
        if config.visitor_data:
            headers["X-Goog-Visitor-Id"] = config.visitor_data
        return self.client.post_json(
            _PLAYER_API_URL,
            {"videoId": video_id, "context": {"client": client_context}},
            params={"key": config.api_key, "prettyPrint": "false"},
            headers=headers,
        )


def _has_direct_audio_url(player_response: Mapping[str, Any]) -> bool:
    streaming_data = as_mapping(player_response.get("streamingData"))
    raw_formats = []
    for key in ("formats", "adaptiveFormats"):
        values = streaming_data.get(key)
        if isinstance(values, list):
            raw_formats.extend(item for item in values if isinstance(item, Mapping))
    for media_format in raw_formats:
        mime_type = as_string(media_format.get("mimeType")) or ""
        media_url = as_string(media_format.get("url"))
        if not mime_type.startswith("audio/") or not media_url:
            continue
        if "n" not in parse_qs(urlparse(media_url).query):
            return True
    return False
