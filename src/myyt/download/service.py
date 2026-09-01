from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from myyt.config import MEDIA_URL_REFRESH_MARGIN
from myyt.exceptions import DownloadError, MediaURLExpiredError
from myyt.media.ffmpeg import FFmpegProcessor
from myyt.models import DownloadResult, MediaFormat, PlayerInfo
from myyt.youtube.extractor import YouTubeExtractor
from myyt.youtube.selector import select_best_audio

from .filenames import available_output_path, sanitize_filename
from .http import HTTPDownloader
from .progress import TransferProgress


class DownloadService:
    def __init__(
        self,
        *,
        extractor: YouTubeExtractor | None = None,
        downloader: HTTPDownloader | None = None,
        ffmpeg: FFmpegProcessor | None = None,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self.extractor = extractor or YouTubeExtractor()
        self.downloader = downloader or HTTPDownloader()
        self.ffmpeg = ffmpeg or FFmpegProcessor()
        self._wall_clock = wall_clock

    def download(
        self,
        url: str,
        *,
        output_directory: Path,
        audio_format: str = "mp3",
        progress: Callable[[TransferProgress], None] | None = None,
        status: Callable[[str], None] | None = None,
    ) -> DownloadResult:
        if audio_format != "mp3":
            raise DownloadError(f"unsupported audio output format: {audio_format}")
        directory = self._prepare_output_directory(output_directory)
        self.ffmpeg.ensure_available()
        player_info, selected = self._extract_selection(url)
        if _expires_soon(selected, self._wall_clock()):
            player_info, selected = self._extract_selection(url)

        stem = sanitize_filename(
            player_info.video.title,
            fallback=player_info.video.video_id,
        )
        try:
            temporary_directory = tempfile.TemporaryDirectory(
                prefix=".myyt-",
                dir=directory,
            )
        except OSError as exc:
            raise DownloadError(f"cannot create a temporary download directory: {exc}") from exc

        with temporary_directory as temporary_name:
            temporary_path = Path(temporary_name)
            source_path = temporary_path / f"source.{selected.container or 'media'}"
            source_bytes, player_info, selected = self._download_with_refresh(
                url,
                source_path,
                player_info,
                selected,
                progress,
            )
            processed_path = temporary_path / "processed.mp3"
            if status:
                status("Processing audio with FFmpeg...")
            self.ffmpeg.convert_to_mp3(source_path, processed_path)
            final_path = available_output_path(directory, stem, ".mp3")
            try:
                os.replace(processed_path, final_path)
            except OSError as exc:
                raise DownloadError(f"cannot finalize output file: {exc}") from exc

        return DownloadResult(
            output_path=str(final_path.resolve()),
            video_id=player_info.video.video_id,
            title=player_info.video.title,
            format_id=selected.format_id,
            source_bytes=source_bytes,
            audio_format=audio_format,
        )

    def _download_with_refresh(
        self,
        url: str,
        source_path: Path,
        player_info: PlayerInfo,
        selected: MediaFormat,
        progress: Callable[[TransferProgress], None] | None,
    ) -> tuple[int, PlayerInfo, MediaFormat]:
        try:
            downloaded = self.downloader.download(
                selected.media_url,
                source_path,
                expected_length=selected.content_length,
                progress=progress,
            )
            return downloaded, player_info, selected
        except MediaURLExpiredError:
            refreshed_info = self.extractor.extract_player(url)
            refreshed = _matching_usable_format(refreshed_info, selected.itag)
            if refreshed is None:
                refreshed = select_best_audio(refreshed_info.formats)
            if refreshed.itag != selected.itag:
                try:
                    source_path.unlink(missing_ok=True)
                except OSError as exc:
                    raise DownloadError(f"cannot reset partial media file: {exc}") from exc
            downloaded = self.downloader.download(
                refreshed.media_url,
                source_path,
                expected_length=refreshed.content_length,
                progress=progress,
            )
            return downloaded, refreshed_info, refreshed

    def _extract_selection(self, url: str) -> tuple[PlayerInfo, MediaFormat]:
        player_info = self.extractor.extract_player(url)
        return player_info, select_best_audio(player_info.formats)

    @staticmethod
    def _prepare_output_directory(output_directory: Path) -> Path:
        directory = output_directory.expanduser()
        try:
            directory.mkdir(parents=True, exist_ok=True)
            if not directory.is_dir():
                raise DownloadError(f"output path is not a directory: {directory}")
            return directory.resolve()
        except DownloadError:
            raise
        except OSError as exc:
            raise DownloadError(f"cannot prepare output directory: {exc}") from exc


def _expires_soon(media_format: MediaFormat, now: float) -> bool:
    return bool(
        media_format.expires_at is not None
        and media_format.expires_at <= int(now) + MEDIA_URL_REFRESH_MARGIN
    )


def _matching_usable_format(player_info: PlayerInfo, itag: int) -> MediaFormat | None:
    for media_format in player_info.formats:
        if (
            media_format.itag == itag
            and media_format.media_url
            and not media_format.requires_n_transform
            and media_format.protocol in {"http", "https"}
        ):
            return media_format
    return None
