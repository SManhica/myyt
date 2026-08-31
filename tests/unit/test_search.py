import json
from pathlib import Path

import pytest

from myyt.exceptions import InvalidQueryError, SearchError
from myyt.youtube.search import (
    YouTubeSearch,
    extract_initial_search_data,
    extract_web_client_config,
    parse_continuation_search_page,
    parse_initial_search_page,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class StubClient:
    def __init__(self, html: str, continuation: dict | None = None) -> None:
        self.html = html
        self.continuation = continuation or {}
        self.get_calls: list[tuple[str, dict, dict]] = []
        self.post_calls: list[tuple[str, dict, dict, dict]] = []

    def get_text(self, url: str, *, params: dict, headers: dict) -> str:
        self.get_calls.append((url, params, headers))
        return self.html

    def post_json(
        self,
        url: str,
        payload: dict,
        *,
        params: dict,
        headers: dict,
    ) -> dict:
        self.post_calls.append((url, payload, params, headers))
        return self.continuation


def test_parses_video_renderers_and_ignores_other_result_types() -> None:
    data = extract_initial_search_data(fixture("search_page_standard.html"))

    page = parse_initial_search_page(data)

    assert [result.video_id for result in page.results] == [
        "yKNxeF4KMsY",
        "dQw4w9WgXcQ",
    ]
    assert page.results[0].title == "Coldplay - Yellow"
    assert page.results[0].channel == "Coldplay"
    assert page.results[0].duration == 273
    assert page.results[0].thumbnail == "https://example.test/large.jpg"
    assert page.results[1].title == "Nested result"
    assert page.results[1].duration == 3723
    assert page.results[1].thumbnail == "https://example.test/nested.jpg"
    assert page.continuation_token == "fixture-token-1"


def test_extracts_quoted_web_client_configuration() -> None:
    config = extract_web_client_config(fixture("search_page_standard.html"))

    assert config is not None
    assert config.api_key == "fixture-key"
    assert config.client_version == "2.fixture"
    assert config.visitor_data == "fixture=visitor"


def test_search_fetches_continuation_to_satisfy_limit() -> None:
    continuation = json.loads(fixture("search_continuation.json"))
    client = StubClient(fixture("search_page_standard.html"), continuation)

    results = YouTubeSearch(client=client).search("  Coldplay Yellow  ", limit=3)

    assert [result.video_id for result in results] == [
        "yKNxeF4KMsY",
        "dQw4w9WgXcQ",
        "M7lc1UVf-VE",
    ]
    assert client.get_calls[0][1]["search_query"] == "Coldplay Yellow"
    assert client.post_calls[0][1]["continuation"] == "fixture-token-1"
    assert client.post_calls[0][2]["key"] == "fixture-key"
    assert client.post_calls[0][3]["X-Goog-Visitor-Id"] == "fixture=visitor"
    assert results[2].duration is None


def test_extracts_direct_object_web_client_configuration() -> None:
    html = (
        '<script>ytcfg.set({"INNERTUBE_API_KEY":"key",'
        '"INNERTUBE_CLIENT_VERSION":"version",'
        '"INNERTUBE_CONTEXT":{"client":{"clientName":"WEB"}}})</script>'
    )

    config = extract_web_client_config(html)

    assert config is not None
    assert config.api_key == "key"
    assert config.client_version == "version"


def test_no_results_is_a_valid_empty_page() -> None:
    data = {
        "contents": {
            "twoColumnSearchResultsRenderer": {
                "primaryContents": {"sectionListRenderer": {"contents": []}}
            }
        }
    }

    assert parse_initial_search_page(data).results == ()


def test_continuation_requires_known_command_container() -> None:
    with pytest.raises(SearchError, match="result commands"):
        parse_continuation_search_page({"responseContext": {}})


def test_malformed_initial_response_is_reported() -> None:
    with pytest.raises(SearchError, match="primary result list"):
        parse_initial_search_page({"contents": {}})


@pytest.mark.parametrize(("query", "limit"), [("", 10), ("   ", 10), ("query", 0), ("query", 101)])
def test_rejects_invalid_search_input(query: str, limit: int) -> None:
    with pytest.raises(InvalidQueryError):
        YouTubeSearch(client=StubClient("")).search(query, limit=limit)
