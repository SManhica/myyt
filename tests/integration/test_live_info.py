import os

import pytest

from myyt.youtube.extractor import YouTubeExtractor

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("MYYT_RUN_INTEGRATION") != "1",
    reason="set MYYT_RUN_INTEGRATION=1 to access live YouTube",
)
def test_extract_public_youtube_player_demo() -> None:
    info = YouTubeExtractor().extract("https://www.youtube.com/watch?v=M7lc1UVf-VE")

    assert info.video_id == "M7lc1UVf-VE"
    assert info.title
    assert info.webpage_url.endswith(info.video_id)
