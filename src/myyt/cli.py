from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence

from myyt import __version__
from myyt.exceptions import MyytError
from myyt.models import SearchResult, VideoInfo
from myyt.youtube.extractor import YouTubeExtractor
from myyt.youtube.search import YouTubeSearch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="myyt", description="Extract and search public YouTube video information."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    info = subparsers.add_parser("info", help="extract normalized video metadata")
    info.add_argument("url", help="public YouTube video URL")
    info.add_argument("--json", action="store_true", dest="as_json", help="emit JSON only")

    search = subparsers.add_parser("search", help="search for public YouTube videos")
    search.add_argument("query", help="YouTube search query")
    search.add_argument("--limit", type=_positive_integer, default=10, help="maximum results")
    search.add_argument("--json", action="store_true", dest="as_json", help="emit JSON only")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    extractor: YouTubeExtractor | None = None,
    searcher: YouTubeSearch | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

    try:
        if args.command == "info":
            info = (extractor or YouTubeExtractor()).extract(args.url)
            _render_info(info, as_json=args.as_json)
            return 0
        if args.command == "search":
            results = (searcher or YouTubeSearch()).search(args.query, limit=args.limit)
            _render_search(results, as_json=args.as_json)
            return 0
    except MyytError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    return 1


def run() -> None:
    raise SystemExit(main())


def _render_info(info: VideoInfo, *, as_json: bool) -> None:
    if as_json:
        json.dump(info.to_dict(), sys.stdout, ensure_ascii=False, separators=(",", ":"))
        sys.stdout.write("\n")
        return

    fields = (
        ("Video ID", info.video_id),
        ("Title", info.title),
        ("Channel", info.channel or "unknown"),
        ("Channel ID", info.channel_id or "unknown"),
        ("Duration", _format_duration(info.duration)),
        ("Thumbnail", info.thumbnail or "unknown"),
        ("URL", info.webpage_url),
    )
    for label, value in fields:
        print(f"{label}: {value}")


def _render_search(results: Sequence[SearchResult], *, as_json: bool) -> None:
    if as_json:
        json.dump(
            [result.to_dict() for result in results],
            sys.stdout,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        sys.stdout.write("\n")
        return

    if not results:
        print("No videos found.")
        return
    for index, result in enumerate(results, start=1):
        print(f"{index}. {result.title}")
        print(f"   Channel: {result.channel or 'unknown'}")
        print(f"   Duration: {_format_duration(result.duration)}")
        print(f"   URL: {result.webpage_url}")


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{remaining_seconds:02d}"
    return f"{minutes}:{remaining_seconds:02d}"


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed
