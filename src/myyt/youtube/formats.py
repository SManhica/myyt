from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from myyt.exceptions import FormatExtractionError
from myyt.models import MediaFormat

from .parsing import as_mapping, as_string, decimal_seconds

_CODECS_RE = re.compile(r"(?:^|;)\s*codecs\s*=\s*[\"']([^\"']+)[\"']", re.I)
_AUDIO_CODEC_PREFIXES = (
    "mp4a",
    "opus",
    "vorbis",
    "ac-3",
    "ec-3",
    "dtsc",
    "dtse",
)
_VIDEO_CODEC_PREFIXES = ("av01", "avc1", "hev1", "hvc1", "vp8", "vp9", "vp09")


def parse_streaming_formats(player_response: Mapping[str, Any]) -> tuple[MediaFormat, ...]:
    streaming_data = as_mapping(player_response.get("streamingData"))
    if not streaming_data:
        raise FormatExtractionError("the player response is missing streamingData")

    formats: list[MediaFormat] = []
    seen: set[int] = set()
    for key, adaptive in (("formats", False), ("adaptiveFormats", True)):
        raw_formats = streaming_data.get(key)
        if not isinstance(raw_formats, list):
            continue
        for raw_format in raw_formats:
            if not isinstance(raw_format, Mapping):
                continue
            normalized = normalize_format(raw_format, adaptive=adaptive)
            if normalized is None or normalized.itag in seen:
                continue
            seen.add(normalized.itag)
            formats.append(normalized)

    if not formats:
        raise FormatExtractionError("streamingData did not contain recognizable formats")
    return tuple(formats)


def normalize_format(raw_format: Mapping[str, Any], *, adaptive: bool) -> MediaFormat | None:
    itag = raw_format.get("itag")
    mime_value = as_string(raw_format.get("mimeType"))
    if not isinstance(itag, int) or not mime_value:
        return None

    mime_type, codecs = parse_mime_type(mime_value)
    audio_codec, video_codec = classify_codecs(mime_type, codecs)
    media_url, is_ciphered = _extract_media_url(raw_format)
    parsed_url = urlparse(media_url) if media_url else None
    query = parse_qs(parsed_url.query) if parsed_url else {}
    requires_n_transform = "n" in query

    has_audio = bool(
        audio_codec
        or mime_type.startswith("audio/")
        or raw_format.get("audioQuality")
        or raw_format.get("audioSampleRate")
    )
    has_video = bool(video_codec or mime_type.startswith("video/"))
    container = _container_for(mime_type, has_audio=has_audio, has_video=has_video)
    expires_at = _first_decimal(query.get("expire", []))

    return MediaFormat(
        format_id=str(itag),
        itag=itag,
        mime_type=mime_type,
        container=container,
        codecs=codecs,
        audio_codec=audio_codec,
        video_codec=video_codec,
        bitrate=_optional_int(raw_format.get("bitrate")),
        average_bitrate=_optional_int(raw_format.get("averageBitrate")),
        sample_rate=decimal_seconds(raw_format.get("audioSampleRate")),
        channels=_optional_int(raw_format.get("audioChannels")),
        content_length=decimal_seconds(raw_format.get("contentLength")),
        width=_optional_int(raw_format.get("width")),
        height=_optional_int(raw_format.get("height")),
        fps=_optional_int(raw_format.get("fps")),
        quality_label=as_string(raw_format.get("qualityLabel")),
        audio_quality=as_string(raw_format.get("audioQuality")),
        has_audio=has_audio,
        has_video=has_video,
        media_url=media_url,
        protocol=parsed_url.scheme.lower() if parsed_url and parsed_url.scheme else None,
        adaptive=adaptive,
        fragmented=bool(raw_format.get("initRange") or raw_format.get("indexRange")),
        is_ciphered=is_ciphered,
        requires_n_transform=requires_n_transform,
        expires_at=expires_at,
    )


def parse_mime_type(value: str) -> tuple[str, tuple[str, ...]]:
    mime_type = value.split(";", 1)[0].strip().lower()
    match = _CODECS_RE.search(value)
    if not match:
        return mime_type, ()
    codecs = tuple(codec.strip() for codec in match.group(1).split(",") if codec.strip())
    return mime_type, codecs


def classify_codecs(mime_type: str, codecs: tuple[str, ...]) -> tuple[str | None, str | None]:
    audio_codec = next(
        (codec for codec in codecs if codec.lower().startswith(_AUDIO_CODEC_PREFIXES)),
        None,
    )
    video_codec = next(
        (codec for codec in codecs if codec.lower().startswith(_VIDEO_CODEC_PREFIXES)),
        None,
    )
    if len(codecs) == 1 and not audio_codec and not video_codec:
        if mime_type.startswith("audio/"):
            audio_codec = codecs[0]
        elif mime_type.startswith("video/"):
            video_codec = codecs[0]
    return audio_codec, video_codec


def manifest_urls(player_response: Mapping[str, Any]) -> tuple[str | None, str | None]:
    streaming_data = as_mapping(player_response.get("streamingData"))
    return (
        as_string(streaming_data.get("dashManifestUrl")),
        as_string(streaming_data.get("hlsManifestUrl")),
    )


def _extract_media_url(raw_format: Mapping[str, Any]) -> tuple[str | None, bool]:
    direct_url = as_string(raw_format.get("url"))
    if direct_url:
        return direct_url, False

    cipher = as_string(raw_format.get("signatureCipher")) or as_string(raw_format.get("cipher"))
    if not cipher:
        return None, False
    fields = parse_qs(cipher)
    media_url = _first_string(fields.get("url", []))
    if not media_url:
        return None, True
    encrypted_signature = _first_string(fields.get("s", []))
    if encrypted_signature:
        return None, True
    signature = _first_string(fields.get("sig", [])) or _first_string(fields.get("signature", []))
    if signature:
        parameter = _first_string(fields.get("sp", [])) or "signature"
        media_url = _append_query(media_url, parameter, signature)
    return media_url, True


def _append_query(url: str, name: str, value: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query[name] = [value]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _container_for(mime_type: str, *, has_audio: bool, has_video: bool) -> str | None:
    subtype = mime_type.partition("/")[2]
    if subtype == "mp4" and has_audio and not has_video:
        return "m4a"
    return subtype or None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def _first_string(values: list[str]) -> str | None:
    return values[0] if values else None


def _first_decimal(values: list[str]) -> int | None:
    value = _first_string(values)
    return int(value) if value and value.isdecimal() else None
