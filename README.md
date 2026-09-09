# myyt

`myyt` is a YouTube-only metadata extractor and media downloader written from
scratch in Python. It does not import, wrap, or invoke yt-dlp or another downloader.

Version 1.0 adds a production-oriented binary streaming command to the existing
metadata, search, format inspection, audio selection, and MP3 download features.

## Capabilities

- Parse common watch, short-link, Shorts, mobile, live, and embed URLs.
- Extract normalized public video metadata and search results.
- Resolve and normalize muxed and adaptive player formats.
- Rank directly usable audio representations with an explicit selector.
- Download source media incrementally with bounded retries and HTTP range resume.
- Convert complete downloads to MP3 through a separately managed FFmpeg process.
- Stream selected source audio bytes directly to stdout without FFmpeg or temporary
  media files.
- Refresh rejected media URLs while preserving byte-stream integrity.
- Keep JSON, binary data, progress, and diagnostics on predictable output channels.
- Run deterministic unit tests plus opt-in live integration tests.

Only normally public media is in scope. Private or account-gated access, DRM,
paywalls, CAPTCHAs, and attestation bypasses are not supported.

## Requirements

- Python 3.11 or newer
- FFmpeg on `PATH` only for `myyt download`
- `pytest` for development and tests

The Python runtime uses only the standard library.

## Installation

```console
python -m pip install -e .
```

For development:

```console
python -m pip install -e ".[dev]"
```

## Usage

```console
myyt info "https://youtu.be/M7lc1UVf-VE" --json
myyt search "Coldplay Yellow" --limit 5 --json
myyt formats "https://youtu.be/M7lc1UVf-VE" --json
myyt bestaudio "https://youtu.be/M7lc1UVf-VE" --json
myyt download "https://youtu.be/jNQXAC9IVRw" -o ./downloads
myyt stream "https://youtu.be/jNQXAC9IVRw" --no-progress > source-audio.bin
```

`stream` stdout is a binary protocol: it contains only the selected source audio
representation. Progress and errors go to stderr. The bytes are not transcoded and
may use MP4/M4A or WebM according to selection. `myyt` itself creates no output file;
a shell or consumer may choose to store the bytes. A successful, validated transfer
exits 0; failures are non-zero. PowerShell version-specific redirection guidance is
in the runbook linked below.

Commands accepting `--json` write exactly one JSON document to stdout. `download`
writes only the completed absolute path to stdout. These contracts make all commands
safe to invoke from another process with stdout and stderr captured separately.

## Tests

```console
pytest -m "not integration"
```

Live access is opt-in. PowerShell:

```powershell
$env:MYYT_RUN_INTEGRATION = "1"
pytest -m integration
```

Linux/macOS:

```sh
MYYT_RUN_INTEGRATION=1 pytest -m integration
```

See [How to Run and Test](docs/how_to_Run.md),
[Architecture](docs/ARCHITECTURE.md), and [Versions](docs/VERSIONS.md) for the full
cross-platform guide, design, guarantees, limitations, and roadmap.
