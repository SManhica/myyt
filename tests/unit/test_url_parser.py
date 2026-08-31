import pytest

from myyt.exceptions import InvalidURLError
from myyt.youtube.url_parser import parse_video_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=M7lc1UVf-VE",
        "https://youtube.com/watch?feature=share&v=M7lc1UVf-VE&t=3",
        "https://youtu.be/M7lc1UVf-VE?t=3",
        "youtu.be/M7lc1UVf-VE",
        "https://m.youtube.com/shorts/M7lc1UVf-VE",
        "https://www.youtube.com/live/M7lc1UVf-VE?feature=share",
        "https://www.youtube-nocookie.com/embed/M7lc1UVf-VE",
    ],
)
def test_parse_common_video_urls(url: str) -> None:
    parsed = parse_video_url(url)

    assert parsed.video_id == "M7lc1UVf-VE"
    assert parsed.webpage_url == "https://www.youtube.com/watch?v=M7lc1UVf-VE"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://example.com/watch?v=M7lc1UVf-VE",
        "https://youtube.com/watch",
        "https://youtube.com/watch?v=too-short",
        "https://youtube.com.evil.test/watch?v=M7lc1UVf-VE",
        "M7lc1UVf-VE",
    ],
)
def test_reject_invalid_or_unsupported_inputs(url: str) -> None:
    with pytest.raises(InvalidURLError):
        parse_video_url(url)
