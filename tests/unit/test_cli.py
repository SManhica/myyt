import json

from myyt.cli import main
from myyt.exceptions import ExtractionError
from myyt.models import VideoInfo


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
