from __future__ import annotations

import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import pytest

from myyt.download.stream import StreamService

pytestmark = pytest.mark.integration
_SHORT_PUBLIC_VIDEO = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
_RUN_LIVE = os.environ.get("MYYT_RUN_INTEGRATION") == "1"


@pytest.mark.skipif(not _RUN_LIVE, reason="set MYYT_RUN_INTEGRATION=1 to access live YouTube")
def test_streams_complete_short_public_audio_representation() -> None:
    output = BytesIO()

    result = StreamService().stream(_SHORT_PUBLIC_VIDEO, output=output)

    assert result.bytes_streamed == output.getbuffer().nbytes
    assert result.bytes_streamed > 10_000
    assert _looks_like_media_container(bytes(output.getbuffer()[:32]))


@pytest.mark.skipif(not _RUN_LIVE, reason="set MYYT_RUN_INTEGRATION=1 to access live YouTube")
def test_stream_cli_survives_binary_process_redirection(tmp_path: Path) -> None:
    destination = tmp_path / "source-audio.bin"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")

    with destination.open("wb") as output:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "myyt",
                "stream",
                _SHORT_PUBLIC_VIDEO,
                "--no-progress",
            ],
            stdout=output,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )

    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert completed.stderr == b""
    assert destination.stat().st_size > 10_000
    assert _looks_like_media_container(destination.read_bytes()[:32])


def _looks_like_media_container(prefix: bytes) -> bool:
    return b"ftyp" in prefix or prefix.startswith(b"\x1aE\xdf\xa3")
