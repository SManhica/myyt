from pathlib import Path

from myyt.download.filenames import available_output_path, sanitize_filename


def test_sanitizes_cross_platform_filename_characters() -> None:
    assert sanitize_filename('  Song: "Live" / 2026?  ', fallback="video") == "Song_ _Live_ _ 2026_"


def test_handles_empty_reserved_and_overlong_names() -> None:
    assert sanitize_filename("...", fallback="abc123") == "abc123"
    assert sanitize_filename("CON", fallback="abc123") == "_CON"
    assert len(sanitize_filename("x" * 500, fallback="abc123", max_length=80)) == 80


def test_allocates_non_overwriting_output_path(tmp_path: Path) -> None:
    (tmp_path / "Song.mp3").write_bytes(b"existing")
    (tmp_path / "Song (1).mp3").write_bytes(b"existing")

    assert available_output_path(tmp_path, "Song", ".mp3").name == "Song (2).mp3"
