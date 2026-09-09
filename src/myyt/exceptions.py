"""Domain exceptions exposed by myyt's public layers."""


class MyytError(Exception):
    """Base class for expected, user-facing failures."""

    exit_code = 1


class InvalidURLError(MyytError):
    """The input is not a supported YouTube video URL."""

    exit_code = 2


class InvalidQueryError(MyytError):
    """A search query or requested result count is invalid."""

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


class SearchError(ExtractionError):
    """YouTube returned search data that could not be normalized."""


class FormatExtractionError(ExtractionError):
    """Playable media formats could not be obtained or normalized."""


class NoSuitableFormatError(MyytError):
    """No available format satisfies the requested selection policy."""

    exit_code = 6


class DownloadError(MyytError):
    """Media bytes could not be transferred or finalized."""

    exit_code = 7


class MediaURLExpiredError(DownloadError):
    """The selected temporary media URL is no longer accepted upstream."""


class UnsafeResumeError(DownloadError):
    """A byte stream cannot be resumed without risking corrupt output."""


class StreamCancelledError(DownloadError):
    """The downstream stream consumer closed before transfer completion."""

    exit_code = 130


class FFmpegError(MyytError):
    """FFmpeg discovery or post-processing failed."""

    exit_code = 8


class FFmpegNotFoundError(FFmpegError):
    """No usable FFmpeg executable was found."""
