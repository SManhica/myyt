from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .parsing import as_mapping, as_string


@dataclass(frozen=True, slots=True)
class WebClientConfig:
    api_key: str
    client_version: str
    context: Mapping[str, Any]
    client_name_header: str = "1"

    @property
    def visitor_data(self) -> str | None:
        return as_string(as_mapping(self.context.get("client")).get("visitorData"))


def extract_web_client_config(html: str) -> WebClientConfig | None:
    combined: dict[str, Any] = {}
    marker = "ytcfg.set("
    offset = 0
    while True:
        marker_index = html.find(marker, offset)
        if marker_index < 0:
            break
        value_index = _skip_whitespace(html, marker_index + len(marker))
        decoded, end_index = _decode_ytcfg_value(html, value_index)
        if isinstance(decoded, Mapping):
            combined.update(decoded)
        offset = max(end_index, value_index + 1)

    api_key = as_string(combined.get("INNERTUBE_API_KEY"))
    context = as_mapping(combined.get("INNERTUBE_CONTEXT"))
    client = as_mapping(context.get("client"))
    client_version = as_string(combined.get("INNERTUBE_CLIENT_VERSION")) or as_string(
        client.get("clientVersion")
    )
    if not api_key or not client_version or not context:
        return None
    client_name_header = as_string(combined.get("INNERTUBE_CONTEXT_CLIENT_NAME")) or "1"
    return WebClientConfig(
        api_key=api_key,
        client_version=client_version,
        context=context,
        client_name_header=client_name_header,
    )


def _decode_ytcfg_value(source: str, index: int) -> tuple[object | None, int]:
    if index >= len(source):
        return None, index
    if source[index] == "{":
        try:
            return json.JSONDecoder().raw_decode(source, index)
        except json.JSONDecodeError:
            return None, index + 1
    if source[index] not in {"'", '"'}:
        return None, index + 1
    string_value, end_index = _decode_javascript_string(source, index)
    if string_value is None:
        return None, end_index
    try:
        return json.loads(string_value), end_index
    except json.JSONDecodeError:
        return None, end_index


def _decode_javascript_string(source: str, index: int) -> tuple[str | None, int]:
    quote = source[index]
    characters: list[str] = []
    cursor = index + 1
    escapes = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
    while cursor < len(source):
        character = source[cursor]
        if character == quote:
            return "".join(characters), cursor + 1
        if character != "\\":
            characters.append(character)
            cursor += 1
            continue
        cursor += 1
        if cursor >= len(source):
            break
        escaped = source[cursor]
        if escaped in {"x", "u"}:
            width = 2 if escaped == "x" else 4
            digits = source[cursor + 1 : cursor + 1 + width]
            if len(digits) == width and all(char in "0123456789abcdefABCDEF" for char in digits):
                characters.append(chr(int(digits, 16)))
                cursor += width + 1
                continue
        characters.append(escapes.get(escaped, escaped))
        cursor += 1
    return None, cursor


def _skip_whitespace(source: str, index: int) -> int:
    while index < len(source) and source[index].isspace():
        index += 1
    return index
