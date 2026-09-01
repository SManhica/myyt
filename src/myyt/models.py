from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class VideoInfo:
    video_id: str
    title: str
    channel: str | None
    channel_id: str | None
    duration: int | None
    thumbnail: str | None
    webpage_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SearchResult:
    video_id: str
    title: str
    channel: str | None
    thumbnail: str | None
    duration: int | None
    webpage_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MediaFormat:
    format_id: str
    itag: int
    mime_type: str
    container: str | None
    codecs: tuple[str, ...]
    audio_codec: str | None
    video_codec: str | None
    bitrate: int | None
    average_bitrate: int | None
    sample_rate: int | None
    channels: int | None
    content_length: int | None
    width: int | None
    height: int | None
    fps: int | None
    quality_label: str | None
    audio_quality: str | None
    has_audio: bool
    has_video: bool
    media_url: str | None
    protocol: str | None
    adaptive: bool
    fragmented: bool
    is_ciphered: bool
    requires_n_transform: bool
    expires_at: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PlayerInfo:
    video: VideoInfo
    formats: tuple[MediaFormat, ...]
    player_client: str
    dash_manifest_url: str | None
    hls_manifest_url: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "video": self.video.to_dict(),
            "player_client": self.player_client,
            "dash_manifest_url": self.dash_manifest_url,
            "hls_manifest_url": self.hls_manifest_url,
            "formats": [media_format.to_dict() for media_format in self.formats],
        }


@dataclass(frozen=True, slots=True)
class DownloadResult:
    output_path: str
    video_id: str
    title: str
    format_id: str
    source_bytes: int
    audio_format: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
