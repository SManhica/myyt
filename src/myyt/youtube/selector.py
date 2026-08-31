from __future__ import annotations

from collections.abc import Iterable

from myyt.exceptions import NoSuitableFormatError
from myyt.models import MediaFormat

_SUPPORTED_AUDIO_PREFIXES = ("opus", "mp4a", "vorbis", "ac-3", "ec-3")
_AUDIO_QUALITY = {"AUDIO_QUALITY_LOW": 1, "AUDIO_QUALITY_MEDIUM": 2, "AUDIO_QUALITY_HIGH": 3}
_CODEC_PREFERENCE = {"vorbis": 1, "mp4a": 2, "opus": 3, "ac-3": 2, "ec-3": 2}
_PROTOCOL_PREFERENCE = {"http": 1, "https": 2}


def select_best_audio(formats: Iterable[MediaFormat]) -> MediaFormat:
    candidates = [
        media_format
        for media_format in formats
        if media_format.has_audio
        and media_format.media_url
        and not media_format.requires_n_transform
        and media_format.protocol in _PROTOCOL_PREFERENCE
    ]
    if not candidates:
        raise NoSuitableFormatError("no directly usable audio format is available")
    return max(candidates, key=_audio_rank)


def _audio_rank(media_format: MediaFormat) -> tuple[int, int, int, int, int, int, int, int]:
    codec = (media_format.audio_codec or "").lower()
    codec_family = next(
        (prefix for prefix in _SUPPORTED_AUDIO_PREFIXES if codec.startswith(prefix)),
        "",
    )
    effective_bitrate = media_format.average_bitrate or media_format.bitrate or 0
    return (
        int(not media_format.has_video),
        int(bool(codec_family)),
        _AUDIO_QUALITY.get(media_format.audio_quality or "", 0),
        effective_bitrate,
        _CODEC_PREFERENCE.get(codec_family, 0),
        _PROTOCOL_PREFERENCE.get(media_format.protocol or "", 0),
        media_format.sample_rate or 0,
        int(media_format.content_length is not None),
    )
