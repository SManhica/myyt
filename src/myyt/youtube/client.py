from __future__ import annotations

import json
import random
import socket
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from myyt.exceptions import NetworkError

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


@dataclass(frozen=True, slots=True)
class HTTPResult:
    body: bytes
    url: str
    status: int
    content_type: str | None
    charset: str

    def text(self) -> str:
        return self.body.decode(self.charset, errors="replace")


class YouTubeClient:
    def __init__(
        self,
        *,
        timeout: float = 20.0,
        retries: int = 2,
        user_agent: str = DEFAULT_USER_AGENT,
        opener: Callable[..., HTTPResponse] = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if retries < 0:
            raise ValueError("retries cannot be negative")
        self.timeout = timeout
        self.retries = retries
        self.user_agent = user_agent
        self._opener = opener
        self._sleeper = sleeper

    def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        result = self.request("GET", self._add_query(url, params), headers=headers)
        return result.text()

    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        result = self.request(
            "POST",
            self._add_query(url, params),
            data=encoded,
            headers=request_headers,
        )
        try:
            decoded = json.loads(result.text())
        except json.JSONDecodeError as exc:
            raise NetworkError("YouTube returned malformed JSON") from exc
        if not isinstance(decoded, dict):
            raise NetworkError("YouTube returned an unexpected JSON document")
        return decoded

    def request(
        self,
        method: str,
        url: str,
        *,
        data: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HTTPResult:
        request_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": self.user_agent,
            **(headers or {}),
        }
        request = Request(url, data=data, headers=request_headers, method=method)
        last_error: BaseException | None = None

        for attempt in range(self.retries + 1):
            try:
                with self._opener(request, timeout=self.timeout) as response:
                    body = response.read()
                    content_type = response.headers.get("Content-Type")
                    charset = response.headers.get_content_charset() or "utf-8"
                    return HTTPResult(
                        body=body,
                        url=response.geturl(),
                        status=response.status,
                        content_type=content_type,
                        charset=charset,
                    )
            except HTTPError as exc:
                last_error = exc
                if exc.code not in _RETRYABLE_STATUS or attempt == self.retries:
                    exc.close()
                    raise NetworkError(f"YouTube request failed with HTTP {exc.code}") from exc
                exc.close()
            except (URLError, TimeoutError, socket.timeout, OSError) as exc:
                last_error = exc
                if attempt == self.retries:
                    raise NetworkError(f"YouTube request failed: {_network_reason(exc)}") from exc

            self._sleeper(self._retry_delay(attempt))

        raise NetworkError("YouTube request failed after retries") from last_error

    @staticmethod
    def _add_query(url: str, params: Mapping[str, str] | None) -> str:
        if not params:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{urlencode(params)}"

    @staticmethod
    def _retry_delay(attempt: int) -> float:
        return (0.5 * (2**attempt)) + random.uniform(0.0, 0.25)


def _network_reason(exc: BaseException) -> str:
    if isinstance(exc, URLError) and exc.reason:
        return str(exc.reason)
    return str(exc) or exc.__class__.__name__
