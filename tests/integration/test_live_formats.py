import os

import pytest

from myyt.youtube.client import YouTubeClient
from myyt.youtube.extractor import YouTubeExtractor
from myyt.youtube.selector import select_best_audio

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("MYYT_RUN_INTEGRATION") != "1",
    reason="set MYYT_RUN_INTEGRATION=1 to access live YouTube",
)
@pytest.mark.parametrize("video_id", ["M7lc1UVf-VE", "yKNxeF4KMsY", "dQw4w9WgXcQ"])
def test_extract_formats_from_public_video_categories(video_id: str) -> None:
    player_info = YouTubeExtractor().extract_player(
        f"https://www.youtube.com/watch?v={video_id}"
    )
    selected = select_best_audio(player_info.formats)

    assert player_info.formats
    assert player_info.player_client in {"WEB", "ANDROID", "IOS"}
    assert selected.has_audio is True
    assert selected.media_url.startswith("https://")
    assert selected.expires_at is not None


@pytest.mark.skipif(
    os.environ.get("MYYT_RUN_INTEGRATION") != "1",
    reason="set MYYT_RUN_INTEGRATION=1 to access live YouTube",
)
def test_selected_audio_url_supports_http_range() -> None:
    player_info = YouTubeExtractor().extract_player(
        "https://www.youtube.com/watch?v=M7lc1UVf-VE"
    )
    selected = select_best_audio(player_info.formats)

    response = YouTubeClient().request(
        "GET",
        selected.media_url,
        headers={"Range": "bytes=0-1023"},
    )

    assert response.status == 206
    assert len(response.body) == 1024
    assert response.content_type and response.content_type.startswith("audio/")
