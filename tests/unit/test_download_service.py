from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from myyt.download.service import DownloadService
from myyt.exceptions import FFmpegError, MediaURLExpiredError
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
        content_length=10,
        width=None,
        height=None,
        fps=None,
        quality_label=None,
        audio_quality="AUDIO_QUALITY_MEDIUM",
        has_audio=True,
        has_video=False,
        media_url="https://media.example.test/first",
        protocol="https",
        adaptive=True,
        fragmented=True,
        is_ciphered=False,
        requires_n_transform=False,
        expires_at=2_000_000_000,
    )
    return replace(base, **changes)


def player_info(media: MediaFormat, *, title: str = "Fixture Song") -> PlayerInfo:
    return PlayerInfo(
        video=VideoInfo(
            video_id="M7lc1UVf-VE",
            title=title,
            channel="Channel",
            channel_id="UC_fixture",
            duration=10,
            thumbnail=None,
            webpage_url="https://www.youtube.com/watch?v=M7lc1UVf-VE",
        ),
        formats=(media,),
        player_client="ANDROID",
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


class FakeDownloader:
    def __init__(self, *, expire_first: bool = False) -> None:
        self.expire_first = expire_first
        self.calls: list[str] = []

    def download(self, url, destination, *, expected_length, progress):
        self.calls.append(url)
        if self.expire_first and len(self.calls) == 1:
            destination.write_bytes(b"part")
            raise MediaURLExpiredError("expired")
        destination.write_bytes(b"source-data")
        return len(b"source-data")


class FakeFFmpeg:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    def ensure_available(self) -> str:
        return "ffmpeg"

    def convert_to_mp3(self, source: Path, destination: Path) -> None:
        self.calls.append((source, destination))
        if self.fail:
            raise FFmpegError("fixture failure")
        assert source.read_bytes() == b"source-data"
        destination.write_bytes(b"ID3-result")


def test_downloads_processes_sanitizes_and_cleans_temporary_files(tmp_path: Path) -> None:
    extractor = FakeExtractor([player_info(media_format(), title="CON")])
    downloader = FakeDownloader()
    ffmpeg = FakeFFmpeg()
    service = DownloadService(
        extractor=extractor,
        downloader=downloader,
        ffmpeg=ffmpeg,
        wall_clock=lambda: 1_000_000_000,
    )

    result = service.download(
        "https://youtu.be/M7lc1UVf-VE",
        output_directory=tmp_path,
    )

    assert Path(result.output_path).name == "_CON.mp3"
    assert Path(result.output_path).read_bytes() == b"ID3-result"
    assert result.source_bytes == len(b"source-data")
    assert not list(tmp_path.glob(".myyt-*"))


def test_reextracts_before_transfer_when_url_expires_soon(tmp_path: Path) -> None:
    old = media_format(media_url="https://media.example.test/old", expires_at=100)
    new = media_format(media_url="https://media.example.test/new", expires_at=2000)
    extractor = FakeExtractor([player_info(old), player_info(new)])
    downloader = FakeDownloader()
    service = DownloadService(
        extractor=extractor,
        downloader=downloader,
        ffmpeg=FakeFFmpeg(),
        wall_clock=lambda: 1000,
    )

    service.download("https://youtu.be/M7lc1UVf-VE", output_directory=tmp_path)

    assert extractor.calls == 2
    assert downloader.calls == ["https://media.example.test/new"]


def test_refreshes_and_resumes_same_itag_after_403(tmp_path: Path) -> None:
    old = media_format(media_url="https://media.example.test/old")
    new = media_format(media_url="https://media.example.test/new")
    extractor = FakeExtractor([player_info(old), player_info(new)])
    downloader = FakeDownloader(expire_first=True)
    service = DownloadService(
        extractor=extractor,
        downloader=downloader,
        ffmpeg=FakeFFmpeg(),
        wall_clock=lambda: 1_000_000_000,
    )

    service.download("https://youtu.be/M7lc1UVf-VE", output_directory=tmp_path)

    assert downloader.calls == [
        "https://media.example.test/old",
        "https://media.example.test/new",
    ]


def test_ffmpeg_failure_removes_all_partial_artifacts(tmp_path: Path) -> None:
    service = DownloadService(
        extractor=FakeExtractor([player_info(media_format())]),
        downloader=FakeDownloader(),
        ffmpeg=FakeFFmpeg(fail=True),
        wall_clock=lambda: 1_000_000_000,
    )

    with pytest.raises(FFmpegError, match="fixture failure"):
        service.download("https://youtu.be/M7lc1UVf-VE", output_directory=tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_ffmpeg_is_checked_before_extraction_or_transfer(tmp_path: Path) -> None:
    extractor = FakeExtractor([player_info(media_format())])
    downloader = FakeDownloader()

    class MissingFFmpeg(FakeFFmpeg):
        def ensure_available(self) -> str:
            raise FFmpegError("missing")

    service = DownloadService(
        extractor=extractor,
        downloader=downloader,
        ffmpeg=MissingFFmpeg(),
    )

    with pytest.raises(FFmpegError, match="missing"):
        service.download("https://youtu.be/M7lc1UVf-VE", output_directory=tmp_path)

    assert extractor.calls == 0
    assert downloader.calls == []


def test_cancellation_removes_partial_artifacts(tmp_path: Path) -> None:
    class InterruptedFFmpeg(FakeFFmpeg):
        def convert_to_mp3(self, source: Path, destination: Path) -> None:
            raise KeyboardInterrupt

    service = DownloadService(
        extractor=FakeExtractor([player_info(media_format())]),
        downloader=FakeDownloader(),
        ffmpeg=InterruptedFFmpeg(),
        wall_clock=lambda: 1_000_000_000,
    )

    with pytest.raises(KeyboardInterrupt):
        service.download("https://youtu.be/M7lc1UVf-VE", output_directory=tmp_path)

    assert list(tmp_path.iterdir()) == []
