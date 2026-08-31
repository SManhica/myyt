import json

from myyt.cli import main
from myyt.exceptions import ExtractionError, SearchError
from myyt.models import SearchResult, VideoInfo


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
