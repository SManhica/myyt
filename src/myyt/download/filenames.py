from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def sanitize_filename(value: str, *, fallback: str, max_length: int = 180) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    sanitized = _INVALID_FILENAME.sub("_", normalized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    if not sanitized:
        sanitized = fallback
    if sanitized.upper() in _RESERVED_NAMES:
        sanitized = f"_{sanitized}"
    sanitized = sanitized[:max_length].rstrip(" .")
    return sanitized or fallback


def available_output_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    for number in range(1, 10_000):
        candidate = directory / f"{stem} ({number}){suffix}"
        if not candidate.exists():
            return candidate
    raise OSError("could not allocate a unique output filename")
