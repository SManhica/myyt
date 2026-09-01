from io import StringIO

from myyt.download.progress import ProgressReporter, TransferProgress


def test_interactive_progress_uses_stderr_style_single_line_updates() -> None:
    stream = StringIO()
    reporter = ProgressReporter(
        stream=stream,
        interactive=True,
        min_interval=0,
    )

    reporter(TransferProgress(512, 1024, 1.0, 512.0, 1.0))
    reporter(TransferProgress(1024, 1024, 2.0, 512.0, 0.0, True))

    output = stream.getvalue()
    assert "50.0%" in output
    assert "100.0%" in output
    assert output.endswith("\n")


def test_noninteractive_progress_emits_only_final_summary() -> None:
    stream = StringIO()
    reporter = ProgressReporter(stream=stream, interactive=False)

    reporter(TransferProgress(512, 1024, 1.0, 512.0, 1.0))
    reporter(TransferProgress(1024, 1024, 2.0, 512.0, 0.0, True))

    assert stream.getvalue().count("\n") == 1
    assert stream.getvalue().startswith("Downloaded:")
