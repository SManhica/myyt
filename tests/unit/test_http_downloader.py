from __future__ import annotations

from email.message import Message
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from myyt.exceptions import MediaURLExpiredError
from myyt.download.http import HTTPDownloader


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

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def getcode(self) -> int:
        return self.status

    def read(self, size: int) -> bytes:
        self._reads += 1
        self.read_sizes.append(size)
        if self._fail_after_first_read and self._reads > 1:
            raise URLError("connection reset")
        return self._body.read(size)


def test_downloads_in_bounded_chunks_and_reports_completion(tmp_path: Path) -> None:
    response = FakeResponse(b"abcdefghij", headers={"Content-Length": "10"})
    progress = []
    downloader = HTTPDownloader(
        chunk_size=4,
        opener=lambda *_args, **_kwargs: response,
        monotonic=lambda: 1.0,
    )
    destination = tmp_path / "audio.part"

    downloaded = downloader.download(
        "https://media.example.test/audio",
        destination,
        expected_length=10,
        progress=progress.append,
    )

    assert downloaded == 10
    assert destination.read_bytes() == b"abcdefghij"
    assert all(size == 4 for size in response.read_sizes)
    assert progress[-1].done is True
    assert progress[-1].downloaded == 10


def test_resumes_after_recoverable_read_failure(tmp_path: Path) -> None:
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

    def opener(request, *, timeout):
        requests.append(request)
        return next(responses)

    destination = tmp_path / "audio.part"
    downloader = HTTPDownloader(
        chunk_size=4,
        retries=1,
        opener=opener,
        sleeper=lambda _: None,
    )

    assert downloader.download("https://media.example.test/audio", destination) == 10
    assert destination.read_bytes() == b"abcdefghij"
    assert requests[1].get_header("Range") == "bytes=4-"


def test_restarts_when_server_ignores_range(tmp_path: Path) -> None:
    destination = tmp_path / "audio.part"
    destination.write_bytes(b"old")
    response = FakeResponse(b"replacement", status=200, headers={"Content-Length": "11"})
    downloader = HTTPDownloader(opener=lambda *_args, **_kwargs: response)

    downloader.download("https://media.example.test/audio", destination)

    assert destination.read_bytes() == b"replacement"


def test_incompatible_content_range_resets_before_retry(tmp_path: Path) -> None:
    destination = tmp_path / "audio.bin"
    destination.write_bytes(b"part")
    responses = iter(
        [
            FakeResponse(
                b"wrong",
                status=206,
                headers={"Content-Range": "bytes 2-6/9", "Content-Length": "5"},
            ),
            FakeResponse(b"complete!", headers={"Content-Length": "9"}),
        ]
    )
    downloader = HTTPDownloader(
        opener=lambda *_args, **_kwargs: next(responses),
        sleeper=lambda _: None,
    )

    assert downloader.download("https://media.example/audio", destination) == 9
    assert destination.read_bytes() == b"complete!"


def test_maps_403_to_expired_media_url(tmp_path: Path) -> None:
    def opener(request, *, timeout):
        raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

    downloader = HTTPDownloader(opener=opener)

    with pytest.raises(MediaURLExpiredError, match="HTTP 403"):
        downloader.download("https://media.example.test/audio", tmp_path / "audio.part")
