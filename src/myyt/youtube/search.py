from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from myyt.exceptions import InvalidQueryError, SearchError
from myyt.models import SearchResult

from .client import YouTubeClient
from .client_context import WebClientConfig, extract_web_client_config
from .parsing import (
    as_mapping,
    as_string,
    best_thumbnail_url,
    colon_duration_seconds,
    decode_json_object_after_markers,
    text_value,
)

_SEARCH_URL = "https://www.youtube.com/results"
_SEARCH_API_URL = "https://www.youtube.com/youtubei/v1/search"
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_INITIAL_DATA_MARKERS = (
    re.compile(r"(?:var\s+)?ytInitialData\s*=\s*"),
    re.compile(r"window\[['\"]ytInitialData['\"]\]\s*=\s*"),
)
_MAX_RESULTS = 100
_MAX_CONTINUATION_PAGES = 10


@dataclass(frozen=True, slots=True)
class SearchPage:
    results: tuple[SearchResult, ...]
    continuation_token: str | None


class YouTubeSearch:
    def __init__(self, client: YouTubeClient | None = None) -> None:
        self.client = client or YouTubeClient()

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        normalized_query = query.strip()
        if not normalized_query:
            raise InvalidQueryError("a non-empty search query is required")
        if not 1 <= limit <= _MAX_RESULTS:
            raise InvalidQueryError(f"search limit must be between 1 and {_MAX_RESULTS}")

        html = self.client.get_text(
            _SEARCH_URL,
            params={"search_query": normalized_query, "hl": "en"},
            headers={"Cookie": "SOCS=CAI; PREF=hl=en"},
        )
        initial_data = extract_initial_search_data(html)
        page = parse_initial_search_page(initial_data)
        results = list(page.results)
        seen_video_ids = {result.video_id for result in results}

        if len(results) >= limit or not page.continuation_token:
            return results[:limit]

        config = extract_web_client_config(html)
        if config is None:
            raise SearchError("the search page omitted web-client continuation configuration")

        token = page.continuation_token
        seen_tokens: set[str] = set()
        pages = 0
        while token and len(results) < limit and pages < _MAX_CONTINUATION_PAGES:
            if token in seen_tokens:
                break
            seen_tokens.add(token)
            continuation_data = self._request_continuation(token, config)
            continuation = parse_continuation_search_page(continuation_data)
            added = 0
            for result in continuation.results:
                if result.video_id in seen_video_ids:
                    continue
                seen_video_ids.add(result.video_id)
                results.append(result)
                added += 1
                if len(results) == limit:
                    break
            token = continuation.continuation_token
            pages += 1
            if added == 0:
                break

        return results[:limit]

    def _request_continuation(
        self, token: str, config: WebClientConfig
    ) -> dict[str, Any]:
        headers = {
            "Origin": "https://www.youtube.com",
            "Referer": "https://www.youtube.com/",
            "X-YouTube-Client-Name": config.client_name_header,
            "X-YouTube-Client-Version": config.client_version,
        }
        if config.visitor_data:
            headers["X-Goog-Visitor-Id"] = config.visitor_data
        return self.client.post_json(
            _SEARCH_API_URL,
            {"context": config.context, "continuation": token},
            params={"key": config.api_key, "prettyPrint": "false"},
            headers=headers,
        )


def extract_initial_search_data(html: str) -> dict[str, Any]:
    decoded = decode_json_object_after_markers(html, _INITIAL_DATA_MARKERS)
    if decoded is None:
        raise SearchError("the search page did not contain usable initial data")
    return decoded


def parse_initial_search_page(data: Mapping[str, Any]) -> SearchPage:
    contents = as_mapping(data.get("contents"))
    two_column = as_mapping(contents.get("twoColumnSearchResultsRenderer"))
    primary = as_mapping(two_column.get("primaryContents"))
    section_list = as_mapping(primary.get("sectionListRenderer"))
    items = section_list.get("contents")
    if not isinstance(items, list):
        raise SearchError("the search response is missing its primary result list")
    return _parse_search_items(items)


def parse_continuation_search_page(data: Mapping[str, Any]) -> SearchPage:
    commands = data.get("onResponseReceivedCommands")
    actions = data.get("onResponseReceivedActions")
    continuation_contents = data.get("continuationContents")
    if not isinstance(commands, list) and not isinstance(actions, list) and not isinstance(
        continuation_contents, Mapping
    ):
        raise SearchError("the continuation response is missing result commands")
    return _parse_search_items(data)


def _parse_search_items(value: object) -> SearchPage:
    results: list[SearchResult] = []
    seen: set[str] = set()
    for renderer in _renderer_values(value, "videoRenderer"):
        result = _normalize_video_renderer(renderer)
        if result is None or result.video_id in seen:
            continue
        seen.add(result.video_id)
        results.append(result)
    return SearchPage(tuple(results), _find_continuation_token(value))


def _normalize_video_renderer(renderer: Mapping[str, Any]) -> SearchResult | None:
    video_id = as_string(renderer.get("videoId"))
    title = text_value(renderer.get("title"))
    if not video_id or not _VIDEO_ID_RE.fullmatch(video_id) or not title:
        return None
    channel = (
        text_value(renderer.get("ownerText"))
        or text_value(renderer.get("longBylineText"))
        or text_value(renderer.get("shortBylineText"))
    )
    return SearchResult(
        video_id=video_id,
        title=title,
        channel=channel,
        thumbnail=best_thumbnail_url(renderer.get("thumbnail")),
        duration=colon_duration_seconds(renderer.get("lengthText")),
        webpage_url=f"https://www.youtube.com/watch?v={video_id}",
    )


def _renderer_values(value: object, renderer_name: str) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == renderer_name:
                renderer = as_mapping(child)
                if renderer:
                    yield renderer
            else:
                yield from _renderer_values(child, renderer_name)
    elif isinstance(value, list):
        for item in value:
            yield from _renderer_values(item, renderer_name)


def _find_continuation_token(value: object) -> str | None:
    for renderer in _renderer_values(value, "continuationItemRenderer"):
        for command in _renderer_values(renderer, "continuationCommand"):
            token = as_string(command.get("token"))
            if token:
                return token
    return None
