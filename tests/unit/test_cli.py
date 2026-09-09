import json
from io import BytesIO
from pathlib import Path

from myyt.cli import main
from myyt.download.progress import TransferProgress
from myyt.exceptions import (
    DownloadError,
    ExtractionError,
    FFmpegNotFoundError,
    SearchError,
    StreamCancelledError,
)
from myyt.models import DownloadResult, PlayerInfo, SearchResult, VideoInfo
from myyt.youtube.formats import manifest_urls, parse_streaming_formats


class SuccessfulExtractor:
    def extract(self, _url: str) -> VideoInfo:
        return VideoInfo(
            video_id="M7lc1UVf-VE",
            title="Example",
            channel="Channel",
            channel_id="UC123",
            duration=125,
            thumbnail="https://example.test/thumb.jpg",
            webpage_url="https://www.youtube.com/watch?v=M7lc1UVf-VE",
        )


class FailingExtractor:
    def extract(self, _url: str) -> VideoInfo:
        raise ExtractionError("fixture failure")


class SuccessfulSearch:
    def search(self, _query: str, *, limit: int) -> list[SearchResult]:
        assert limit == 2
        return [
            SearchResult(
                video_id="yKNxeF4KMsY",
                title="Coldplay - Yellow",
                channel="Coldplay",
                thumbnail="https://example.test/yellow.jpg",
                duration=273,
                webpage_url="https://www.youtube.com/watch?v=yKNxeF4KMsY",
            )
        ]


class EmptySearch:
    def search(self, _query: str, *, limit: int) -> list[SearchResult]:
        return []


class FailingSearch:
    def search(self, _query: str, *, limit: int) -> list[SearchResult]:
        raise SearchError("malformed search fixture")


class PlayerExtractor:
    def extract_player(self, _url: str) -> PlayerInfo:
        fixture_path = Path(__file__).parents[1] / "fixtures" / "player_android_formats.json"
        response = json.loads(fixture_path.read_text(encoding="utf-8"))
        dash, hls = manifest_urls(response)
        return PlayerInfo(
            video=SuccessfulExtractor().extract(_url),
            formats=parse_streaming_formats(response),
            player_client="ANDROID",
            dash_manifest_url=dash,
            hls_manifest_url=hls,
        )


class SuccessfulDownloadService:
    def download(
        self,
        _url,
        *,
        output_directory,
        audio_format,
        progress,
        status,
    ) -> DownloadResult:
        assert output_directory == Path("downloads")
        assert audio_format == "mp3"
        assert progress is not None
        assert status is None
        return DownloadResult(
            output_path="D:\\downloads\\Example.mp3",
            video_id="M7lc1UVf-VE",
            title="Example",
            format_id="140",
            source_bytes=100,
            audio_format="mp3",
        )


class FailingDownloadService:
    def download(self, _url, **_kwargs) -> DownloadResult:
        raise FFmpegNotFoundError("FFmpeg missing")


class InterruptedDownloadService:
    def download(self, _url, **_kwargs) -> DownloadResult:
        raise KeyboardInterrupt


class SuccessfulStreamService:
    def stream(self, _url, *, output, progress):
        output.write(b"\x00media\xff")
        if progress is not None:
            progress(TransferProgress(7, 7, 1.0, 7.0, 0.0, True))


class FailingStreamService:
    def stream(self, _url, **_kwargs):
        raise DownloadError("fixture stream failure")


class ExtractionFailingStreamService:
    def stream(self, _url, **_kwargs):
        raise ExtractionError("fixture extraction failure")


class ClosedStreamService:
    def stream(self, _url, **_kwargs):
        raise StreamCancelledError("downstream consumer closed the stream")


def test_json_mode_writes_only_valid_json_to_stdout(capsys) -> None:
    exit_code = main(
        ["info", "https://youtu.be/M7lc1UVf-VE", "--json"],
        extractor=SuccessfulExtractor(),
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["duration"] == 125
    assert captured.err == ""


def test_human_mode_formats_duration(capsys) -> None:
    exit_code = main(
        ["info", "https://youtu.be/M7lc1UVf-VE"], extractor=SuccessfulExtractor()
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Duration: 2:05" in captured.out


def test_expected_error_uses_stderr_and_nonzero_status(capsys) -> None:
    exit_code = main(
        ["info", "https://youtu.be/M7lc1UVf-VE", "--json"],
        extractor=FailingExtractor(),
    )

    captured = capsys.readouterr()
    assert exit_code == ExtractionError.exit_code
    assert captured.out == ""
    assert "fixture failure" in captured.err


def test_search_json_is_an_array_with_normalized_results(capsys) -> None:
    exit_code = main(
        ["search", "Coldplay Yellow", "--limit", "2", "--json"],
        searcher=SuccessfulSearch(),
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload[0]["video_id"] == "yKNxeF4KMsY"
    assert payload[0]["duration"] == 273
    assert captured.err == ""


def test_empty_human_search_is_not_an_error(capsys) -> None:
    exit_code = main(["search", "no results"], searcher=EmptySearch())

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "No videos found.\n"


def test_search_error_preserves_machine_readable_stdout(capsys) -> None:
    exit_code = main(
        ["search", "query", "--json"],
        searcher=FailingSearch(),
    )

    captured = capsys.readouterr()
    assert exit_code == SearchError.exit_code
    assert captured.out == ""
    assert captured.err == "error: malformed search fixture\n"


def test_formats_json_contains_video_client_and_normalized_formats(capsys) -> None:
    exit_code = main(
        ["formats", "https://youtu.be/M7lc1UVf-VE", "--json"],
        extractor=PlayerExtractor(),
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["video"]["video_id"] == "M7lc1UVf-VE"
    assert payload["player_client"] == "ANDROID"
    assert {item["itag"] for item in payload["formats"]} == {18, 137, 140, 251}
    assert captured.err == ""


def test_bestaudio_json_uses_explicit_selector(capsys) -> None:
    exit_code = main(
        ["bestaudio", "https://youtu.be/M7lc1UVf-VE", "--json"],
        extractor=PlayerExtractor(),
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["format"]["itag"] == 251
    assert payload["format"]["audio_codec"] == "opus"
    assert payload["format"]["media_url"].startswith("https://")


def test_download_writes_only_final_path_to_stdout_when_progress_disabled(capsys) -> None:
    exit_code = main(
        [
            "download",
            "https://youtu.be/M7lc1UVf-VE",
            "-o",
            "downloads",
            "--audio-format",
            "mp3",
            "--no-progress",
        ],
        download_service=SuccessfulDownloadService(),
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "D:\\downloads\\Example.mp3\n"
    assert captured.err == ""


def test_download_failure_preserves_stdout_and_exit_code(capsys) -> None:
    exit_code = main(
        ["download", "https://youtu.be/M7lc1UVf-VE", "--no-progress"],
        download_service=FailingDownloadService(),
    )

    captured = capsys.readouterr()
    assert exit_code == FFmpegNotFoundError.exit_code
    assert captured.out == ""
    assert captured.err == "error: FFmpeg missing\n"


def test_download_cancellation_returns_130_without_stdout(capsys) -> None:
    exit_code = main(
        ["download", "https://youtu.be/M7lc1UVf-VE", "--no-progress"],
        download_service=InterruptedDownloadService(),
    )

    captured = capsys.readouterr()
    assert exit_code == 130
    assert captured.out == ""
    assert captured.err == "error: cancelled\n"


def test_stream_writes_binary_only_and_no_progress_keeps_stderr_empty(capsys) -> None:
    output = BytesIO()

    exit_code = main(
        ["stream", "https://youtu.be/M7lc1UVf-VE", "--no-progress"],
        stream_service=SuccessfulStreamService(),
        binary_stdout=output,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output.getvalue() == b"\x00media\xff"
    assert captured.out == ""
    assert captured.err == ""


def test_stream_progress_is_written_to_stderr_only(capsys) -> None:
    output = BytesIO()

    exit_code = main(
        ["stream", "https://youtu.be/M7lc1UVf-VE"],
        stream_service=SuccessfulStreamService(),
        binary_stdout=output,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output.getvalue() == b"\x00media\xff"
    assert captured.out == ""
    assert "Downloaded:" in captured.err


def test_stream_failure_preserves_binary_stdout_and_uses_stderr(capsys) -> None:
    output = BytesIO()

    exit_code = main(
        ["stream", "https://youtu.be/M7lc1UVf-VE", "--no-progress"],
        stream_service=FailingStreamService(),
        binary_stdout=output,
    )

    captured = capsys.readouterr()
    assert exit_code == DownloadError.exit_code
    assert output.getvalue() == b""
    assert captured.out == ""
    assert captured.err == "error: fixture stream failure\n"


def test_stream_extraction_failure_keeps_stdout_empty_and_returns_domain_exit(capsys) -> None:
    output = BytesIO()

    exit_code = main(
        ["stream", "https://youtu.be/M7lc1UVf-VE", "--no-progress"],
        stream_service=ExtractionFailingStreamService(),
        binary_stdout=output,
    )

    captured = capsys.readouterr()
    assert exit_code == ExtractionError.exit_code
    assert output.getvalue() == b""
    assert captured.out == ""
    assert captured.err == "error: fixture extraction failure\n"


def test_stream_broken_pipe_uses_cancellation_exit_without_traceback(capsys) -> None:
    exit_code = main(
        ["stream", "https://youtu.be/M7lc1UVf-VE", "--no-progress"],
        stream_service=ClosedStreamService(),
        binary_stdout=BytesIO(),
    )

    captured = capsys.readouterr()
    assert exit_code == 130
    assert captured.out == ""
    assert "downstream consumer closed" in captured.err
    assert "Traceback" not in captured.err
