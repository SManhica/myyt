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
