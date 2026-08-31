from dataclasses import replace

import pytest

from myyt.exceptions import NoSuitableFormatError
from myyt.models import MediaFormat
from myyt.youtube.selector import select_best_audio


def media_format(**changes) -> MediaFormat:
    base = MediaFormat(
        format_id="140",
        itag=140,
        mime_type="audio/mp4",
        container="m4a",
        codecs=("mp4a.40.2",),
        audio_codec="mp4a.40.2",
        video_codec=None,
        bitrate=128000,
        average_bitrate=127000,
        sample_rate=44100,
        channels=2,
        content_length=3000000,
        width=None,
        height=None,
        fps=None,
        quality_label=None,
        audio_quality="AUDIO_QUALITY_MEDIUM",
        has_audio=True,
        has_video=False,
        media_url="https://example.test/audio",
        protocol="https",
        adaptive=True,
        fragmented=True,
        is_ciphered=False,
        requires_n_transform=False,
        expires_at=2000000000,
    )
    return replace(base, **changes)


def test_prefers_audio_only_over_higher_bitrate_muxed_format() -> None:
    muxed = media_format(
        format_id="18",
        itag=18,
        has_video=True,
        video_codec="avc1.42001E",
        bitrate=500000,
        average_bitrate=500000,
    )
    audio = media_format()

    assert select_best_audio([muxed, audio]) == audio


def test_prefers_quality_and_bitrate_then_codec() -> None:
    aac = media_format()
    opus = media_format(
        format_id="251",
        itag=251,
        mime_type="audio/webm",
        container="webm",
        codecs=("opus",),
        audio_codec="opus",
        bitrate=160000,
        average_bitrate=158000,
        sample_rate=48000,
    )

    assert select_best_audio([aac, opus]) == opus


def test_rejects_missing_throttled_or_unsupported_transport_urls() -> None:
    with pytest.raises(NoSuitableFormatError):
        select_best_audio(
            [
                media_format(media_url=None),
                media_format(requires_n_transform=True),
                media_format(protocol="m3u8"),
            ]
        )
