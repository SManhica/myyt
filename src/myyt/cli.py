from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence

from myyt import __version__
from myyt.exceptions import MyytError
from myyt.models import MediaFormat, PlayerInfo, SearchResult, VideoInfo
from myyt.youtube.extractor import YouTubeExtractor
from myyt.youtube.search import YouTubeSearch
from myyt.youtube.selector import select_best_audio


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

    formats = subparsers.add_parser("formats", help="list playable YouTube media formats")
    formats.add_argument("url", help="public YouTube video URL")
    formats.add_argument("--json", action="store_true", dest="as_json", help="emit JSON only")

    bestaudio = subparsers.add_parser("bestaudio", help="select the best usable audio format")
    bestaudio.add_argument("url", help="public YouTube video URL")
    bestaudio.add_argument("--json", action="store_true", dest="as_json", help="emit JSON only")
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
        if args.command in {"formats", "bestaudio"}:
            player_info = (extractor or YouTubeExtractor()).extract_player(args.url)
            if args.command == "formats":
                _render_formats(player_info, as_json=args.as_json)
            else:
                selected = select_best_audio(player_info.formats)
                _render_best_audio(player_info, selected, as_json=args.as_json)
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


def _render_formats(player_info: PlayerInfo, *, as_json: bool) -> None:
    if as_json:
        _write_json(player_info.to_dict())
        return
    print(f"Title: {player_info.video.title}")
    print(f"Player client: {player_info.player_client}")
    print("ID   Kind        Container  Codec                 Bitrate     Size       Protocol")
    for media_format in player_info.formats:
        kind = _format_kind(media_format)
        codec = media_format.audio_codec or media_format.video_codec or "unknown"
        bitrate = _format_bitrate(media_format.average_bitrate or media_format.bitrate)
        size = _format_size(media_format.content_length)
        print(
            f"{media_format.format_id:<4} {kind:<11} {media_format.container or '-':<10} "
            f"{codec:<21} {bitrate:<11} {size:<10} {media_format.protocol or '-'}"
        )


def _render_best_audio(
    player_info: PlayerInfo,
    media_format: MediaFormat,
    *,
    as_json: bool,
) -> None:
    if as_json:
        _write_json(
            {
                "video": player_info.video.to_dict(),
                "player_client": player_info.player_client,
                "format": media_format.to_dict(),
            }
        )
        return
    fields = (
        ("Title", player_info.video.title),
        ("Format ID", media_format.format_id),
        ("Container", media_format.container or "unknown"),
        ("Audio codec", media_format.audio_codec or "unknown"),
        ("Bitrate", _format_bitrate(media_format.average_bitrate or media_format.bitrate)),
        (
            "Sample rate",
            f"{media_format.sample_rate} Hz" if media_format.sample_rate else "unknown",
        ),
        ("Channels", str(media_format.channels) if media_format.channels else "unknown"),
        ("Content length", _format_size(media_format.content_length)),
        ("Expires at", str(media_format.expires_at) if media_format.expires_at else "unknown"),
        ("Media URL", media_format.media_url or "unavailable"),
    )
    for label, value in fields:
        print(f"{label}: {value}")


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


def _write_json(value: object) -> None:
    json.dump(value, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


def _format_kind(media_format: MediaFormat) -> str:
    if media_format.has_audio and media_format.has_video:
        return "audio+video"
    if media_format.has_audio:
        return "audio-only"
    if media_format.has_video:
        return "video-only"
    return "unknown"


def _format_bitrate(value: int | None) -> str:
    return f"{value / 1000:.1f} kbps" if value is not None else "unknown"


def _format_size(value: int | None) -> str:
    return f"{value / (1024 * 1024):.2f} MiB" if value is not None else "unknown"
