import os
import shutil
from pathlib import Path

import pytest

from myyt.download.http import HTTPDownloader
from myyt.download.service import DownloadService
from myyt.youtube.extractor import YouTubeExtractor
from myyt.youtube.selector import select_best_audio

pytestmark = pytest.mark.integration
_SHORT_PUBLIC_VIDEO = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


@pytest.mark.skipif(
    os.environ.get("MYYT_RUN_INTEGRATION") != "1",
    reason="set MYYT_RUN_INTEGRATION=1 to access live YouTube",
)
def test_download_complete_short_public_audio_source(tmp_path: Path) -> None:
    player_info = YouTubeExtractor().extract_player(_SHORT_PUBLIC_VIDEO)
    selected = select_best_audio(player_info.formats)
    destination = tmp_path / f"source.{selected.container or 'media'}"

    downloaded = HTTPDownloader().download(
        selected.media_url,
        destination,
        expected_length=selected.content_length,
    )

    assert destination.is_file()
    assert downloaded == destination.stat().st_size
    assert downloaded > 10_000
    if selected.content_length is not None:
        assert downloaded == selected.content_length


@pytest.mark.skipif(
    os.environ.get("MYYT_RUN_INTEGRATION") != "1" or shutil.which("ffmpeg") is None,
    reason="set MYYT_RUN_INTEGRATION=1 and install FFmpeg for live MP3 download",
)
def test_download_short_public_video_to_mp3(tmp_path: Path) -> None:
    result = DownloadService().download(
        _SHORT_PUBLIC_VIDEO,
        output_directory=tmp_path,
    )

    output = Path(result.output_path)
    assert output.suffix == ".mp3"
    assert output.is_file()
    assert output.stat().st_size > 10_000
    assert not list(tmp_path.glob(".myyt-*"))
