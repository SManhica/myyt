from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from myyt.exceptions import InvalidURLError

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
_PATH_VIDEO_PREFIXES = {"shorts", "embed", "live", "v"}


@dataclass(frozen=True, slots=True)
class ParsedVideoURL:
    video_id: str
    webpage_url: str


def parse_video_url(value: str) -> ParsedVideoURL:
    candidate = value.strip()
    if not candidate:
        raise InvalidURLError("a YouTube video URL is required")

    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.hostname or "").lower().rstrip(".")
    video_id: str | None = None

    if host in _SHORT_HOSTS:
        video_id = _first_path_segment(parsed.path)
    elif host in _YOUTUBE_HOSTS:
        segments = [segment for segment in parsed.path.split("/") if segment]
        if parsed.path.rstrip("/") == "/watch":
            video_id = _single_query_value(parsed.query, "v")
        elif len(segments) >= 2 and segments[0].lower() in _PATH_VIDEO_PREFIXES:
            video_id = segments[1]
    else:
        raise InvalidURLError(f"unsupported YouTube host: {host or '<missing>'}")

    if not video_id or not _VIDEO_ID_RE.fullmatch(video_id):
        raise InvalidURLError("the URL does not contain a valid 11-character YouTube video ID")

    return ParsedVideoURL(
        video_id=video_id,
        webpage_url=f"https://www.youtube.com/watch?v={video_id}",
    )


def _first_path_segment(path: str) -> str | None:
    segments = [segment for segment in path.split("/") if segment]
    return segments[0] if segments else None


def _single_query_value(query: str, name: str) -> str | None:
    values = parse_qs(query, keep_blank_values=True).get(name, [])
    return values[0] if values else None
