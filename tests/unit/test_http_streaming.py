from __future__ import annotations

from email.message import Message
from io import BytesIO
from urllib.error import URLError

import pytest

from myyt.download.http import HTTPDownloader
from myyt.exceptions import DownloadError, StreamCancelledError, UnsafeResumeError


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        fail_after_first_read: bool = False,
    ) -> None:
        self.status = status
        self.headers = Message()
        for name, value in (headers or {}).items():
            self.headers[name] = value
        self._body = BytesIO(body)
        self._fail_after_first_read = fail_after_first_read
        self._reads = 0
        self.read_sizes: list[int] = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True

    def getcode(self) -> int:
        return self.status

    def read(self, size: int) -> bytes:
        self._reads += 1
        self.read_sizes.append(size)
        if self._fail_after_first_read and self._reads > 1:
            raise URLError("connection reset")
        return self._body.read(size)


class BrokenOutput:
    def write(self, _data) -> int:
        raise BrokenPipeError

    def flush(self) -> None:
        return


class PartialOutput(BytesIO):
    def write(self, data) -> int:
        return super().write(data[:2])


def test_stream_writes_exact_binary_bytes_in_bounded_chunks() -> None:
    media = bytes(range(256)) * 3
    response = FakeResponse(media, headers={"Content-Length": str(len(media))})
    output = BytesIO()
    downloader = HTTPDownloader(
        chunk_size=37,
        opener=lambda *_args, **_kwargs: response,
    )

    assert downloader.stream(
        "https://media.example/audio",
        output,
        expected_length=len(media),
    ) == len(media)
    assert output.getvalue() == media
    assert all(size == 37 for size in response.read_sizes)
    assert response.closed is True


def test_stream_completes_partial_output_writes_without_losing_bytes() -> None:
    response = FakeResponse(b"abcdef", headers={"Content-Length": "6"})
    output = PartialOutput()

    downloaded = HTTPDownloader(
        chunk_size=6,
        opener=lambda *_args, **_kwargs: response,
    ).stream("https://media.example/audio", output, expected_length=6)

    assert downloaded == 6
    assert output.getvalue() == b"abcdef"


def test_failure_before_first_byte_leaves_output_empty() -> None:
    output = BytesIO()
    downloader = HTTPDownloader(
        retries=0,
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline")),
    )

    with pytest.raises(DownloadError, match="after retries"):
        downloader.stream("https://media.example/audio", output, expected_length=4)

    assert output.getvalue() == b""


def test_stream_without_any_verifiable_length_fails_before_output() -> None:
    output = BytesIO()
    response = FakeResponse(b"unbounded")

    with pytest.raises(DownloadError, match="no byte length"):
        HTTPDownloader(opener=lambda *_args, **_kwargs: response).stream(
            "https://media.example/audio", output
        )

    assert output.getvalue() == b""


def test_transient_failure_before_output_retries_normally() -> None:
    response = FakeResponse(b"data", headers={"Content-Length": "4"})
    calls = 0

    def opener(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise URLError("temporary")
        return response

    output = BytesIO()
    downloader = HTTPDownloader(retries=1, opener=opener, sleeper=lambda _: None)

    assert downloader.stream(
        "https://media.example/audio", output, expected_length=4
    ) == 4
    assert output.getvalue() == b"data"
    assert calls == 2


def test_partial_stream_resumes_with_exact_206_without_duplication() -> None:
    first = FakeResponse(
        b"abcd",
        headers={"Content-Length": "10"},
        fail_after_first_read=True,
    )
    second = FakeResponse(
        b"efghij",
        status=206,
        headers={"Content-Length": "6", "Content-Range": "bytes 4-9/10"},
    )
    responses = iter([first, second])
    requests = []

    def opener(request, **_kwargs):
        requests.append(request)
        return next(responses)

    output = BytesIO()
    downloader = HTTPDownloader(
        chunk_size=4,
        retries=1,
        opener=opener,
        sleeper=lambda _: None,
    )

    assert downloader.stream(
        "https://media.example/audio", output, expected_length=10
    ) == 10
    assert output.getvalue() == b"abcdefghij"
    assert requests[1].get_header("Range") == "bytes=4-9"


def test_http_200_after_partial_output_fails_instead_of_restarting() -> None:
    responses = iter(
        [
            FakeResponse(
                b"abcd",
                headers={"Content-Length": "10"},
                fail_after_first_read=True,
            ),
            FakeResponse(b"abcdefghij", headers={"Content-Length": "10"}),
        ]
    )
    output = BytesIO()
    downloader = HTTPDownloader(
        chunk_size=4,
        retries=1,
        opener=lambda *_args, **_kwargs: next(responses),
        sleeper=lambda _: None,
    )

    with pytest.raises(UnsafeResumeError, match="ignored the resume range"):
        downloader.stream("https://media.example/audio", output, expected_length=10)

    assert output.getvalue() == b"abcd"


def test_mismatched_content_range_after_partial_output_fails() -> None:
    responses = iter(
        [
            FakeResponse(
                b"abcd",
                headers={"Content-Length": "10"},
                fail_after_first_read=True,
            ),
            FakeResponse(
                b"cdefghij",
                status=206,
                headers={"Content-Length": "8", "Content-Range": "bytes 2-9/10"},
            ),
        ]
    )
    output = BytesIO()
    downloader = HTTPDownloader(
        chunk_size=4,
        retries=1,
        opener=lambda *_args, **_kwargs: next(responses),
        sleeper=lambda _: None,
    )

    with pytest.raises(UnsafeResumeError, match="mismatched range"):
        downloader.stream("https://media.example/audio", output, expected_length=10)

    assert output.getvalue() == b"abcd"


def test_truncated_stream_is_not_reported_as_success() -> None:
    output = BytesIO()
    response = FakeResponse(b"part", headers={"Content-Length": "10"})
    downloader = HTTPDownloader(
        retries=0,
        opener=lambda *_args, **_kwargs: response,
    )

    with pytest.raises(DownloadError, match="after retries"):
        downloader.stream("https://media.example/audio", output, expected_length=10)

    assert output.getvalue() == b"part"


def test_broken_pipe_stops_without_retry_and_closes_response() -> None:
    response = FakeResponse(b"data", headers={"Content-Length": "4"})
    calls = 0

    def opener(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return response

    downloader = HTTPDownloader(retries=3, opener=opener, sleeper=lambda _: None)

    with pytest.raises(StreamCancelledError, match="downstream consumer"):
        downloader.stream(
            "https://media.example/audio", BrokenOutput(), expected_length=4
        )

    assert calls == 1
    assert response.closed is True
