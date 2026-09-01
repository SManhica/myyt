from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True, slots=True)
class TransferProgress:
    downloaded: int
    total: int | None
    elapsed: float
    speed: float
    eta: float | None
    done: bool = False


class ProgressReporter:
    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        enabled: bool = True,
        min_interval: float = 0.1,
        interactive: bool | None = None,
    ) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self.enabled = enabled
        self.min_interval = min_interval
        self.interactive = self.stream.isatty() if interactive is None else interactive
        self._last_elapsed = -min_interval
        self._active_line = False

    def __call__(self, progress: TransferProgress) -> None:
        if not self.enabled:
            return
        if not progress.done and not self.interactive:
            return
        if not progress.done and progress.elapsed - self._last_elapsed < self.min_interval:
            return
        self._last_elapsed = progress.elapsed
        line = _progress_line(progress)
        if self.interactive:
            ending = "\n" if progress.done else ""
            print(f"\r{line}", end=ending, file=self.stream, flush=True)
            self._active_line = not progress.done
        elif progress.done:
            print(line, file=self.stream, flush=True)

    def close(self) -> None:
        if self.enabled and self.interactive and self._active_line:
            print(file=self.stream, flush=True)
            self._active_line = False


def _progress_line(progress: TransferProgress) -> str:
    downloaded = _format_bytes(progress.downloaded)
    speed = f"{_format_bytes(int(progress.speed))}/s" if progress.speed > 0 else "--/s"
    if progress.total:
        percentage = min(100.0, progress.downloaded * 100 / progress.total)
        total = _format_bytes(progress.total)
        eta = _format_time(progress.eta) if progress.eta is not None else "--:--"
        prefix = "Downloaded" if progress.done else "Downloading"
        return f"{prefix}: {percentage:5.1f}% {downloaded}/{total} {speed} ETA {eta}"
    prefix = "Downloaded" if progress.done else "Downloading"
    return f"{prefix}: {downloaded} {speed}"


def _format_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if amount < 1024 or unit == "GiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} GiB"


def _format_time(value: float | None) -> str:
    if value is None:
        return "--:--"
    seconds = max(0, int(value))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
