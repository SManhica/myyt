from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


def decode_json_object_after_markers(
    source: str, markers: Sequence[re.Pattern[str]]
) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for marker in markers:
        for match in marker.finditer(source):
            try:
                decoded, _ = decoder.raw_decode(source, match.end())
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                return decoded
    return None


def as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def as_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def text_value(value: object) -> str | None:
    mapping = as_mapping(value)
    simple = as_string(mapping.get("simpleText"))
    if simple:
        return simple
    runs = mapping.get("runs")
    if not isinstance(runs, Sequence) or isinstance(runs, (str, bytes)):
        return None
    parts = [as_string(as_mapping(run).get("text")) for run in runs]
    combined = "".join(part for part in parts if part)
    return combined or None


def decimal_seconds(value: object) -> int | None:
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def colon_duration_seconds(value: object) -> int | None:
    text = text_value(value)
    if not text:
        return None
    parts = text.split(":")
    if not 2 <= len(parts) <= 3 or not all(part.isdecimal() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    if any(part >= 60 for part in numbers[1:]):
        return None
    total = 0
    for part in numbers:
        total = (total * 60) + part
    return total


def best_thumbnail_url(value: object) -> str | None:
    items = as_mapping(value).get("thumbnails")
    if not isinstance(items, list):
        return None
    usable = [as_mapping(item) for item in items if as_string(as_mapping(item).get("url"))]
    if not usable:
        return None

    def size(item: Mapping[str, Any]) -> tuple[int, int, int]:
        width = item.get("width") if isinstance(item.get("width"), int) else 0
        height = item.get("height") if isinstance(item.get("height"), int) else 0
        return width * height, width, height

    url = as_string(max(usable, key=size).get("url"))
    if url and url.startswith("//"):
        return f"https:{url}"
    return url
