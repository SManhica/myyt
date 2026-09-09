from __future__ import annotations

import subprocess
import tempfile
from dataclasses import replace
from io import BytesIO

import pytest

from myyt.download.stream import StreamService
from myyt.exceptions import MediaURLExpiredError, NoSuitableFormatError, UnsafeResumeError
from myyt.models import MediaFormat, PlayerInfo, VideoInfo


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
        content_length=6,
        width=None,
        height=None,
        fps=None,
        quality_label=None,
        audio_quality="AUDIO_QUALITY_MEDIUM",
        has_audio=True,
        has_video=False,
        media_url="https://media.example/old",
        protocol="https",
        adaptive=True,
        fragmented=True,
        is_ciphered=False,
        requires_n_transform=False,
        expires_at=2_000_000_000,
    )
    return replace(base, **changes)


def player_info(*formats: MediaFormat) -> PlayerInfo:
    return PlayerInfo(
        video=VideoInfo(
            video_id="M7lc1UVf-VE",
            title="Fixture",
            channel="Channel",
            channel_id="UC_fixture",
            duration=1,
            thumbnail=None,
            webpage_url="https://www.youtube.com/watch?v=M7lc1UVf-VE",
        ),
        formats=formats,
        player_client="VISIONOS",
        dash_manifest_url=None,
        hls_manifest_url=None,
    )


class FakeExtractor:
    def __init__(self, responses: list[PlayerInfo]) -> None:
        self.responses = responses
        self.calls = 0

    def extract_player(self, _url: str) -> PlayerInfo:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


class SuccessfulTransfer:
    def __init__(self, data: bytes = b"abcdef") -> None:
        self.data = data
        self.calls: list[tuple[str, int, int | None]] = []

    def transfer(self, url, sink, *, expected_length, progress):
        self.calls.append((url, sink.position, expected_length))
        sink.write(self.data[sink.position :])
        sink.flush()
        return sink.position


class ExpiringTransfer(SuccessfulTransfer):
    def __init__(self, *, emit_before_expiry: bytes) -> None:
        super().__init__()
        self.emit_before_expiry = emit_before_expiry

    def transfer(self, url, sink, *, expected_length, progress):
        self.calls.append((url, sink.position, expected_length))
        if len(self.calls) == 1:
            if self.emit_before_expiry:
                sink.write(self.emit_before_expiry)
            raise MediaURLExpiredError("expired")
        sink.write(self.data[sink.position :])
        sink.flush()
        return sink.position


def test_stream_service_uses_transfer_directly_without_file_or_ffmpeg(monkeypatch) -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("streaming must not create a temporary directory or process")

    monkeypatch.setattr(tempfile, "TemporaryDirectory", unexpected)
    monkeypatch.setattr(subprocess, "Popen", unexpected)
    selected = media_format()
    transfer = SuccessfulTransfer()
    output = BytesIO()
    service = StreamService(
        extractor=FakeExtractor([player_info(selected)]),
        downloader=transfer,
        wall_clock=lambda: 1_000_000_000,
    )

    result = service.stream("https://youtu.be/M7lc1UVf-VE", output=output)

    assert output.getvalue() == b"abcdef"
    assert result.bytes_streamed == 6
    assert result.format_id == "140"
    assert transfer.calls == [(selected.media_url, 0, 6)]


def test_selection_failure_before_transfer_leaves_output_empty() -> None:
    transfer = SuccessfulTransfer()
    output = BytesIO()
    service = StreamService(
        extractor=FakeExtractor([player_info()]),
        downloader=transfer,
    )

    with pytest.raises(NoSuitableFormatError):
        service.stream("https://youtu.be/M7lc1UVf-VE", output=output)

    assert output.getvalue() == b""
    assert transfer.calls == []


def test_expired_url_before_output_can_refresh_and_reselect() -> None:
    old = media_format()
    replacement = media_format(
        format_id="251",
        itag=251,
        mime_type="audio/webm",
        container="webm",
        codecs=("opus",),
        audio_codec="opus",
        media_url="https://media.example/new",
    )
    transfer = ExpiringTransfer(emit_before_expiry=b"")
    service = StreamService(
        extractor=FakeExtractor([player_info(old), player_info(replacement)]),
        downloader=transfer,
        wall_clock=lambda: 1_000_000_000,
    )
    output = BytesIO()

    result = service.stream("https://youtu.be/M7lc1UVf-VE", output=output)

    assert result.format_id == "251"
    assert output.getvalue() == b"abcdef"
    assert transfer.calls[1] == (replacement.media_url, 0, 6)


def test_expired_url_after_output_resumes_same_exact_representation() -> None:
    old = media_format()
    refreshed = media_format(media_url="https://media.example/refreshed")
    transfer = ExpiringTransfer(emit_before_expiry=b"ab")
    service = StreamService(
        extractor=FakeExtractor([player_info(old), player_info(refreshed)]),
        downloader=transfer,
        wall_clock=lambda: 1_000_000_000,
    )
    output = BytesIO()

    result = service.stream("https://youtu.be/M7lc1UVf-VE", output=output)

    assert result.bytes_streamed == 6
    assert output.getvalue() == b"abcdef"
    assert transfer.calls[1] == (refreshed.media_url, 2, 6)


def test_format_change_after_output_fails_without_mixing_bytes() -> None:
    old = media_format()
    changed = media_format(
        format_id="251",
        itag=251,
        mime_type="audio/webm",
        container="webm",
        codecs=("opus",),
        audio_codec="opus",
        media_url="https://media.example/new",
    )
    transfer = ExpiringTransfer(emit_before_expiry=b"ab")
    service = StreamService(
        extractor=FakeExtractor([player_info(old), player_info(changed)]),
        downloader=transfer,
        wall_clock=lambda: 1_000_000_000,
    )
    output = BytesIO()

    with pytest.raises(UnsafeResumeError, match="refusing to mix formats"):
        service.stream("https://youtu.be/M7lc1UVf-VE", output=output)

    assert output.getvalue() == b"ab"
    assert len(transfer.calls) == 1


def test_same_itag_with_changed_length_after_output_is_not_compatible() -> None:
    old = media_format()
    changed = media_format(
        media_url="https://media.example/new",
        content_length=7,
    )
    transfer = ExpiringTransfer(emit_before_expiry=b"ab")
    service = StreamService(
        extractor=FakeExtractor([player_info(old), player_info(changed)]),
        downloader=transfer,
        wall_clock=lambda: 1_000_000_000,
    )

    with pytest.raises(UnsafeResumeError):
        service.stream("https://youtu.be/M7lc1UVf-VE", output=BytesIO())
