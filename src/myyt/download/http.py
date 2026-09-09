from __future__ import annotations

import errno
import random
import socket
import time
from collections.abc import Callable, Mapping
from http.client import IncompleteRead
from pathlib import Path
from typing import BinaryIO, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from myyt.config import (
    DEFAULT_HTTP_RETRIES,
    DEFAULT_HTTP_TIMEOUT,
    DEFAULT_MEDIA_CHUNK_SIZE,
    DEFAULT_MEDIA_RANGE_SIZE,
    DEFAULT_USER_AGENT,
)
from myyt.exceptions import (
    DownloadError,
    MediaURLExpiredError,
    StreamCancelledError,
    UnsafeResumeError,
)

from .progress import TransferProgress

_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
_EXPIRED_STATUS = {403, 410}


class _IncompleteTransfer(Exception):
    pass


class TransferSink(Protocol):
    @property
    def position(self) -> int: ...

    @property
    def restartable(self) -> bool: ...

    def write(self, data: bytes) -> None: ...

    def reset(self) -> None: ...

    def flush(self) -> None: ...

    def close(self) -> None: ...


class FileSink:
    def __init__(self, path: Path) -> None:
        self.path = path
        try:
            self._position = path.stat().st_size if path.exists() else 0
        except OSError as exc:
            raise DownloadError(f"cannot inspect partial download: {exc}") from exc
        self._output: BinaryIO | None = None

    @property
    def position(self) -> int:
        return self._position

    @property
    def restartable(self) -> bool:
        return True

    def write(self, data: bytes) -> None:
        if self._output is None:
            try:
                self._output = self.path.open("ab" if self._position else "wb")
            except OSError as exc:
                raise DownloadError(f"cannot open temporary media file: {exc}") from exc
        try:
            written = self._output.write(data)
        except OSError as exc:
            raise DownloadError(f"cannot write temporary media file: {exc}") from exc
        if written != len(data):
            raise DownloadError("temporary media file accepted only part of a transfer chunk")
        self._position += written

    def reset(self) -> None:
        self.close()
        try:
            with self.path.open("wb"):
                pass
        except OSError as exc:
            raise DownloadError(f"cannot reset partial media file: {exc}") from exc
        self._position = 0

    def flush(self) -> None:
        if self._output is None:
            return
        try:
            self._output.flush()
        except OSError as exc:
            raise DownloadError(f"cannot flush temporary media file: {exc}") from exc

    def close(self) -> None:
        if self._output is not None:
            self._output.close()
            self._output = None


class BinaryStreamSink:
    def __init__(self, output: BinaryIO) -> None:
        self.output = output
        self._position = 0

    @property
    def position(self) -> int:
        return self._position

    @property
    def restartable(self) -> bool:
        return False

    def write(self, data: bytes) -> None:
        remaining = memoryview(data)
        while remaining:
            try:
                written = self.output.write(remaining)
            except BrokenPipeError as exc:
                raise StreamCancelledError("downstream consumer closed the stream") from exc
            except OSError as exc:
                if exc.errno == errno.EPIPE:
                    raise StreamCancelledError(
                        "downstream consumer closed the stream"
                    ) from exc
                raise DownloadError(f"cannot write media stream: {exc}") from exc
            if written is None or written <= 0:
                raise DownloadError("media stream output accepted no bytes")
            self._position += written
            remaining = remaining[written:]

    def reset(self) -> None:
        if self._position:
            raise UnsafeResumeError(
                "cannot restart a media response after bytes were written to stdout"
            )

    def flush(self) -> None:
        try:
            self.output.flush()
        except BrokenPipeError as exc:
            raise StreamCancelledError("downstream consumer closed the stream") from exc
        except OSError as exc:
            if exc.errno == errno.EPIPE:
                raise StreamCancelledError("downstream consumer closed the stream") from exc
            raise DownloadError(f"cannot flush media stream: {exc}") from exc

    def close(self) -> None:
        return


class HTTPDownloader:
    def __init__(
        self,
        *,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
        retries: int = DEFAULT_HTTP_RETRIES,
        chunk_size: int = DEFAULT_MEDIA_CHUNK_SIZE,
        range_size: int = DEFAULT_MEDIA_RANGE_SIZE,
        user_agent: str = DEFAULT_USER_AGENT,
        opener: Callable[..., object] = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if retries < 0:
            raise ValueError("retries cannot be negative")
        if chunk_size <= 0:
            raise ValueError("chunk size must be positive")
        if range_size <= 0:
            raise ValueError("range size must be positive")
        self.timeout = timeout
        self.retries = retries
        self.chunk_size = chunk_size
        self.range_size = range_size
        self.user_agent = user_agent
        self._opener = opener
        self._sleeper = sleeper
        self._monotonic = monotonic

    def download(
        self,
        url: str,
        destination: Path,
        *,
        expected_length: int | None = None,
        progress: Callable[[TransferProgress], None] | None = None,
    ) -> int:
        sink = FileSink(destination)
        try:
            return self.transfer(
                url,
                sink,
                expected_length=expected_length,
                progress=progress,
            )
        finally:
            sink.close()

    def stream(
        self,
        url: str,
        output: BinaryIO,
        *,
        expected_length: int | None = None,
        progress: Callable[[TransferProgress], None] | None = None,
    ) -> int:
        return self.transfer(
            url,
            BinaryStreamSink(output),
            expected_length=expected_length,
            progress=progress,
        )

    def transfer(
        self,
        url: str,
        sink: TransferSink,
        *,
        expected_length: int | None = None,
        progress: Callable[[TransferProgress], None] | None = None,
    ) -> int:
        started = self._monotonic()
        last_error: BaseException | None = None
        for attempt in range(self.retries + 1):
            try:
                downloaded = self._transfer(
                    url,
                    sink,
                    expected_length=expected_length,
                    progress=progress,
                    started=started,
                )
                sink.flush()
                return downloaded
            except (MediaURLExpiredError, DownloadError):
                raise
            except (
                URLError,
                TimeoutError,
                socket.timeout,
                IncompleteRead,
                _IncompleteTransfer,
            ) as exc:
                last_error = exc
            except OSError as exc:
                last_error = exc

            if attempt == self.retries:
                break
            self._sleeper(_retry_delay(attempt))

        reason = (
            str(last_error) or last_error.__class__.__name__
            if last_error
            else "unknown error"
        )
        raise DownloadError(f"media transfer failed after retries: {reason}") from last_error

    def _transfer(
        self,
        url: str,
        sink: TransferSink,
        *,
        expected_length: int | None,
        progress: Callable[[TransferProgress], None] | None,
        started: float,
    ) -> int:
        offset = sink.position
        if expected_length is not None and offset > expected_length:
            raise DownloadError(
                f"partial media output is larger than the expected {expected_length} bytes"
            )
        if expected_length is not None and offset == expected_length:
            self._notify(progress, offset, expected_length, started, done=True)
            return offset

        while True:
            range_end = (
                min(offset + self.range_size - 1, expected_length - 1)
                if expected_length is not None
                else None
            )
            headers = {"Accept": "*/*", "User-Agent": self.user_agent}
            if range_end is not None:
                headers["Range"] = f"bytes={offset}-{range_end}"
            elif offset:
                headers["Range"] = f"bytes={offset}-"
            request = Request(url, headers=headers, method="GET")

            try:
                response_context = self._opener(request, timeout=self.timeout)
            except HTTPError as exc:
                if exc.code in _EXPIRED_STATUS:
                    exc.close()
                    raise MediaURLExpiredError(
                        f"media URL was rejected with HTTP {exc.code} while requesting "
                        f"{headers.get('Range', 'the full response')}; the URL may be expired "
                        "or require client playback proof"
                    ) from exc
                if exc.code == 416 and expected_length is not None and offset == expected_length:
                    exc.close()
                    self._notify(progress, offset, expected_length, started, done=True)
                    return offset
                if exc.code not in _RETRYABLE_STATUS:
                    exc.close()
                    raise DownloadError(f"media request failed with HTTP {exc.code}") from exc
                exc.close()
                raise

            with response_context as response:
                status = getattr(response, "status", None)
                if status is None:
                    status = response.getcode()
                if status in _EXPIRED_STATUS:
                    raise MediaURLExpiredError(f"media URL was rejected with HTTP {status}")
                if status not in {200, 206}:
                    if status in _RETRYABLE_STATUS:
                        raise _IncompleteTransfer(f"retryable HTTP {status}")
                    raise DownloadError(f"media request failed with HTTP {status}")

                if status == 206 and _content_range_start(response.headers) != offset:
                    if offset and not sink.restartable:
                        raise UnsafeResumeError(
                            "server returned a mismatched range after stream output began"
                        )
                    sink.reset()
                    raise _IncompleteTransfer("server returned an incompatible content range")
                if offset > 0 and status == 200:
                    if not sink.restartable:
                        raise UnsafeResumeError(
                            "server ignored the resume range after stream output began"
                        )
                    sink.reset()
                    offset = 0

                total = _response_total(response.headers, offset, expected_length)
                response_total = _content_range_total(response.headers)
                if (
                    expected_length is not None
                    and status == 206
                    and response_total != expected_length
                ):
                    raise DownloadError(
                        "server content range does not match the selected representation length"
                    )
                if (
                    expected_length is not None
                    and status == 200
                    and _content_length(response.headers) is not None
                    and total != expected_length
                ):
                    if total is not None and total > expected_length:
                        raise DownloadError(
                            "server returned a content length exceeding the expected "
                            "representation length"
                        )
                    raise DownloadError(
                        "server content length does not match the selected representation length"
                    )
                if not sink.restartable and total is None:
                    raise DownloadError(
                        "cannot validate stream completion because no byte length is available"
                    )
                downloaded = offset

                while True:
                    chunk = response.read(self.chunk_size)
                    if not chunk:
                        break
                    if expected_length is not None and downloaded + len(chunk) > expected_length:
                        raise DownloadError(
                            "server returned bytes exceeding the expected representation length"
                        )
                    sink.write(chunk)
                    downloaded = sink.position
                    self._notify(progress, downloaded, total, started, done=False)

            if expected_length is None:
                if total is not None and downloaded < total:
                    raise _IncompleteTransfer(
                        f"connection ended at {downloaded} of {total} bytes"
                    )
                self._notify(progress, downloaded, total, started, done=True)
                return downloaded

            requested_stop = (
                range_end + 1
                if status == 206 and range_end is not None
                else expected_length
            )
            if downloaded < requested_stop:
                raise _IncompleteTransfer(
                    f"connection ended at {downloaded} of {requested_stop} requested bytes"
                )
            if downloaded >= expected_length:
                self._notify(progress, downloaded, expected_length, started, done=True)
                return downloaded
            offset = downloaded

    def _notify(
        self,
        callback: Callable[[TransferProgress], None] | None,
        downloaded: int,
        total: int | None,
        started: float,
        *,
        done: bool,
    ) -> None:
        if callback is None:
            return
        elapsed = max(0.0, self._monotonic() - started)
        speed = downloaded / elapsed if elapsed > 0 else 0.0
        remaining = max(0, total - downloaded) if total is not None else None
        eta = remaining / speed if remaining is not None and speed > 0 else None
        callback(TransferProgress(downloaded, total, elapsed, speed, eta, done))


def _response_total(
    headers: Mapping[str, str], offset: int, expected_length: int | None
) -> int | None:
    content_range_total = _content_range_total(headers)
    if content_range_total is not None:
        return content_range_total
    content_length = headers.get("Content-Length")
    if content_length and content_length.isdecimal():
        return offset + int(content_length)
    return expected_length


def _content_range_start(headers: Mapping[str, str]) -> int | None:
    content_range = headers.get("Content-Range", "")
    if not content_range.startswith("bytes ") or "-" not in content_range:
        return None
    start = content_range[6:].split("-", 1)[0]
    return int(start) if start.isdecimal() else None


def _content_range_total(headers: Mapping[str, str]) -> int | None:
    content_range = headers.get("Content-Range", "")
    if "/" not in content_range:
        return None
    total = content_range.rsplit("/", 1)[1]
    return int(total) if total.isdecimal() else None


def _content_length(headers: Mapping[str, str]) -> int | None:
    content_length = headers.get("Content-Length", "")
    return int(content_length) if content_length.isdecimal() else None


def _retry_delay(attempt: int) -> float:
    return (0.5 * (2**attempt)) + random.uniform(0.0, 0.25)
