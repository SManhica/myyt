from pathlib import Path

import pytest

from myyt.exceptions import FFmpegError, FFmpegNotFoundError
from myyt.media.ffmpeg import FFmpegProcessor


class FakeProcess:
    def __init__(self, command: list[str], *, returncode: int = 0, stderr: str = "") -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        self.terminated = False
        self.killed = False
        if returncode == 0:
            Path(command[-1]).write_bytes(b"ID3fixture")

    def communicate(self):
        return None, self.stderr

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout=None):
        return self.returncode


def test_builds_ffmpeg_mp3_command_and_validates_output(tmp_path: Path) -> None:
    commands = []

    def popen(command, **kwargs):
        commands.append((command, kwargs))
        return FakeProcess(command)

    source = tmp_path / "source.webm"
    source.write_bytes(b"media")
    destination = tmp_path / "output.mp3"
    processor = FFmpegProcessor(which=lambda _: "/usr/bin/ffmpeg", popen_factory=popen)

    processor.convert_to_mp3(source, destination)

    command, kwargs = commands[0]
    assert command[0] == "/usr/bin/ffmpeg"
    assert command[command.index("-f") + 1] == "mp3"
    assert "libmp3lame" in command
    assert kwargs["text"] is True
    assert destination.read_bytes().startswith(b"ID3")


def test_reports_missing_ffmpeg() -> None:
    with pytest.raises(FFmpegNotFoundError, match="not found"):
        FFmpegProcessor(which=lambda _: None).ensure_available()


def test_includes_collected_ffmpeg_stderr_on_failure(tmp_path: Path) -> None:
    source = tmp_path / "source.webm"
    source.write_bytes(b"media")

    def popen(command, **kwargs):
        return FakeProcess(command, returncode=1, stderr="invalid input")

    processor = FFmpegProcessor(executable="ffmpeg", popen_factory=popen)

    with pytest.raises(FFmpegError, match="invalid input"):
        processor.convert_to_mp3(source, tmp_path / "output.mp3")


def test_terminates_ffmpeg_when_cancelled(tmp_path: Path) -> None:
    source = tmp_path / "source.webm"
    source.write_bytes(b"media")

    class InterruptedProcess(FakeProcess):
        def communicate(self):
            raise KeyboardInterrupt

    process = InterruptedProcess(["ffmpeg", str(tmp_path / "output.mp3")], returncode=1)
    processor = FFmpegProcessor(
        executable="ffmpeg",
        popen_factory=lambda *_args, **_kwargs: process,
    )

    with pytest.raises(KeyboardInterrupt):
        processor.convert_to_mp3(source, tmp_path / "output.mp3")

    assert process.terminated is True
    assert process.killed is False
