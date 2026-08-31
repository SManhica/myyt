"""Domain exceptions exposed by myyt's public layers."""


class MyytError(Exception):
    """Base class for expected, user-facing failures."""

    exit_code = 1


class InvalidURLError(MyytError):
    """The input is not a supported YouTube video URL."""

    exit_code = 2


class NetworkError(MyytError):
    """A request failed before a usable YouTube response was obtained."""

    exit_code = 3


class VideoUnavailableError(MyytError):
    """YouTube reports that the requested public video is unavailable."""

    exit_code = 4


class ExtractionError(MyytError):
    """YouTube returned data that the current extractor could not normalize."""

    exit_code = 5
