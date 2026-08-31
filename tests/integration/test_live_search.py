import os

import pytest

from myyt.youtube.search import YouTubeSearch

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("MYYT_RUN_INTEGRATION") != "1",
    reason="set MYYT_RUN_INTEGRATION=1 to access live YouTube",
)
def test_search_public_youtube_with_continuation() -> None:
    results = YouTubeSearch().search("Coldplay Yellow", limit=21)

    assert len(results) == 21
    assert len({result.video_id for result in results}) == 21
    assert all(result.title for result in results)
