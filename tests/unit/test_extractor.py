from pathlib import Path

import pytest

from myyt.exceptions import ExtractionError, VideoUnavailableError
from myyt.youtube.extractor import (
    YouTubeExtractor,
    extract_initial_player_response,
    normalize_video_info,
)
from myyt.youtube.url_parser import parse_video_url

FIXTURES = Path(__file__).parents[1] / "fixtures"


class StubClient:
    def __init__(self, html: str) -> None:
        self.html = html
        self.calls: list[tuple[str, dict[str, str], dict[str, str]]] = []

    def get_text(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> str:
        self.calls.append((url, params, headers))
        return self.html


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_extracts_and_normalizes_video_details() -> None:
    client = StubClient(fixture("watch_page_standard.html"))

    info = YouTubeExtractor(client=client).extract("https://youtu.be/M7lc1UVf-VE")

    assert info.video_id == "M7lc1UVf-VE"
    assert info.title.startswith("YouTube Developers Live")
    assert info.channel == "Google for Developers"
    assert info.channel_id == "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    assert info.duration == 221
    assert info.thumbnail == "https://i.ytimg.com/vi/M7lc1UVf-VE/hqdefault.jpg"
    assert info.webpage_url == "https://www.youtube.com/watch?v=M7lc1UVf-VE"
    assert client.calls[0][1] == {"hl": "en"}


def test_microformat_fills_missing_video_details() -> None:
    response = extract_initial_player_response(fixture("watch_page_microformat.html"))
    parsed = parse_video_url("https://youtube.com/watch?v=dQw4w9WgXcQ")

    info = normalize_video_info(response, parsed)

    assert info.title == "Microformat Title"
    assert info.channel == "Example Channel"
    assert info.channel_id == "UC-example"
    assert info.duration == 42


def test_reports_unavailable_reason_when_metadata_is_absent() -> None:
    response = {"playabilityStatus": {"status": "ERROR", "reason": "Video unavailable"}}
    parsed = parse_video_url("https://youtube.com/watch?v=dQw4w9WgXcQ")

    with pytest.raises(VideoUnavailableError, match="Video unavailable"):
        normalize_video_info(response, parsed)


def test_rejects_missing_player_response() -> None:
    with pytest.raises(ExtractionError, match="player response"):
        extract_initial_player_response("<html><title>No data</title></html>")


def test_rejects_mismatched_response_video_id() -> None:
    response = {"videoDetails": {"videoId": "M7lc1UVf-VE", "title": "Wrong"}}
    parsed = parse_video_url("https://youtube.com/watch?v=dQw4w9WgXcQ")

    with pytest.raises(ExtractionError, match="different video"):
        normalize_video_info(response, parsed)
