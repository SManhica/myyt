from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from myyt.exceptions import FFmpegError, FFmpegNotFoundError


class FFmpegProcessor:
    def __init__(
        self,
        executable: str | None = None,
        *,
        which: Callable[[str], str | None] = shutil.which,
        popen_factory: Callable[..., Any] = subprocess.Popen,
    ) -> None:
        self._configured_executable = executable
        self._which = which
        self._popen_factory = popen_factory
        self._resolved_executable: str | None = None

    def ensure_available(self) -> str:
        if self._resolved_executable is None:
            self._resolved_executable = self._resolve_executable()
        return self._resolved_executable

    def convert_to_mp3(self, source: Path, destination: Path) -> None:
        executable = self.ensure_available()
        command = [
            executable,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            "-f",
            "mp3",
            str(destination),
        ]
        try:
            process = self._popen_factory(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            raise FFmpegError(f"could not start FFmpeg: {exc}") from exc

        try:
            _, stderr = process.communicate()
        except KeyboardInterrupt:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise

        if process.returncode != 0:
            detail = (stderr or "").strip() or "no diagnostic output"
            raise FFmpegError(f"FFmpeg failed with exit code {process.returncode}: {detail}")
        try:
            valid_output = destination.is_file() and destination.stat().st_size > 0
        except OSError as exc:
            raise FFmpegError(f"could not inspect FFmpeg output: {exc}") from exc
        if not valid_output:
            raise FFmpegError("FFmpeg completed without creating a non-empty MP3")

    def _resolve_executable(self) -> str:
        if self._configured_executable:
            return self._configured_executable
        executable = self._which("ffmpeg")
        if not executable:
            raise FFmpegNotFoundError(
                "FFmpeg was not found on PATH; install FFmpeg before using download"
            )
        return executable
