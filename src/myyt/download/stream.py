from __future__ import annotations

import time
from collections.abc import Callable
from typing import BinaryIO

from myyt.exceptions import MediaURLExpiredError, UnsafeResumeError
from myyt.models import MediaFormat, PlayerInfo, StreamResult
from myyt.youtube.extractor import YouTubeExtractor
from myyt.youtube.selector import select_best_audio

from .http import BinaryStreamSink, HTTPDownloader
from .progress import TransferProgress
from .selection import (
    expires_soon,
    extract_selection,
    is_exact_resume_match,
    matching_usable_format,
)


class StreamService:
    def __init__(
        self,
        *,
        extractor: YouTubeExtractor | None = None,
        downloader: HTTPDownloader | None = None,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self.extractor = extractor or YouTubeExtractor()
        self.downloader = downloader or HTTPDownloader()
        self._wall_clock = wall_clock

    def stream(
        self,
        url: str,
        *,
        output: BinaryIO,
        progress: Callable[[TransferProgress], None] | None = None,
    ) -> StreamResult:
        player_info, selected = extract_selection(self.extractor, url)
        if expires_soon(selected, self._wall_clock()):
            player_info, selected = extract_selection(self.extractor, url)

        sink = BinaryStreamSink(output)
        try:
            streamed = self.downloader.transfer(
                selected.media_url,
                sink,
                expected_length=selected.content_length,
                progress=progress,
            )
        except MediaURLExpiredError:
            player_info, selected = self._refresh_selection(
                url,
                selected,
                bytes_emitted=sink.position,
            )
            streamed = self.downloader.transfer(
                selected.media_url,
                sink,
                expected_length=selected.content_length,
                progress=progress,
            )

        return StreamResult(
            video_id=player_info.video.video_id,
            format_id=selected.format_id,
            bytes_streamed=streamed,
        )

    def _refresh_selection(
        self,
        url: str,
        previous: MediaFormat,
        *,
        bytes_emitted: int,
    ) -> tuple[PlayerInfo, MediaFormat]:
        refreshed_info = self.extractor.extract_player(url)
        matching = matching_usable_format(refreshed_info, previous.itag)

        if bytes_emitted:
            if matching is None or not is_exact_resume_match(previous, matching):
                raise UnsafeResumeError(
                    "media representation changed after stream output began; refusing "
                    "to mix formats"
                )
            return refreshed_info, matching

        return refreshed_info, matching or select_best_audio(refreshed_info.formats)
