from email.message import Message
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from myyt.exceptions import NetworkError
from myyt.youtube.client import YouTubeClient


class FakeResponse:
    def __init__(self, body: bytes, url: str = "https://example.test/final") -> None:
        self._body = BytesIO(body)
        self._url = url
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = "text/plain; charset=utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return self._body.read()

    def geturl(self) -> str:
        return self._url


def test_client_retries_recoverable_network_error() -> None:
    calls = 0
    delays: list[float] = []

    def opener(_request, *, timeout):
        nonlocal calls
        calls += 1
        assert timeout == 3
        if calls == 1:
            raise URLError("temporary")
        return FakeResponse(b"ok")

    client = YouTubeClient(timeout=3, retries=1, opener=opener, sleeper=delays.append)

    assert client.get_text("https://example.test") == "ok"
    assert calls == 2
    assert len(delays) == 1


def test_client_does_not_retry_nonrecoverable_http_status() -> None:
    calls = 0

    def opener(request, *, timeout):
        nonlocal calls
        calls += 1
        raise HTTPError(request.full_url, 404, "Not Found", {}, None)

    client = YouTubeClient(retries=3, opener=opener, sleeper=lambda _: None)

    with pytest.raises(NetworkError, match="HTTP 404"):
        client.get_text("https://example.test")
    assert calls == 1


def test_post_json_rejects_non_object_document() -> None:
    client = YouTubeClient(opener=lambda *_args, **_kwargs: FakeResponse(b"[]"))

    with pytest.raises(NetworkError, match="unexpected JSON"):
        client.post_json("https://example.test", {"videoId": "abc"})
