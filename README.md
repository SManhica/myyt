# myyt

`myyt` is a YouTube-only metadata extraction and media downloading project written
from scratch in Python. Version 0.4.1 adds resumable media transfer and FFmpeg MP3
post-processing to the metadata, search, player-format, and best-audio foundation.
It does not import, wrap, or invoke yt-dlp or another downloader.

## Current capabilities (v0.4.1)

- Parse `youtube.com/watch`, `youtu.be`, and `youtube.com/shorts` URLs, plus common
  mobile, live, and embed variants.
- Retrieve a public watch page through a retrying YouTube HTTP client.
- Normalize embedded player metadata into a typed `VideoInfo` model.
- Search public YouTube results and normalize video entries into `SearchResult`.
- Follow first-party YouTube continuation responses when a limit needs more than the
  initial result page.
- Normalize muxed, adaptive audio, and adaptive video formats from player responses.
- Obtain direct public media URLs through an isolated player-client fallback when the
  WEB response exposes SABR metadata without per-format URLs.
- Prefer a current public player profile whose direct media does not require a GVS
  Proof-of-Origin token; token-requiring Android/iOS URLs are not treated as usable.
- Rank and select the best directly usable audio format.
- Download media incrementally with bounded retries and HTTP range resume.
- Refresh an expiring or rejected media URL through fresh player extraction.
- Sanitize cross-platform filenames, avoid overwrites, and clean temporary files.
- Convert selected audio to MP3 through a separately managed FFmpeg process.
- Report transfer progress to stderr while keeping the final path on stdout.
- Emit readable terminal output or JSON-only stdout.
- Run deterministic fixture-based tests; live tests are opt-in.

Binary media streaming to stdout and manifest-specific fragment transfer are
intentionally deferred to v1.0.

## Requirements

- Python 3.11 or newer
- FFmpeg on `PATH` for `myyt download`
- `pytest` for development and tests

The Python runtime uses only the standard library. FFmpeg is an external executable,
not a Python extraction dependency.

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
myyt info "https://www.youtube.com/watch?v=M7lc1UVf-VE"
myyt info "https://youtu.be/M7lc1UVf-VE" --json
python -m myyt info "https://www.youtube.com/shorts/M7lc1UVf-VE" --json
myyt search "Coldplay Yellow"
myyt search "Coldplay Yellow" --limit 5 --json
myyt formats "https://youtu.be/M7lc1UVf-VE" --json
myyt bestaudio "https://youtu.be/M7lc1UVf-VE" --json
myyt download "https://youtu.be/jNQXAC9IVRw"
myyt download "https://youtu.be/M7lc1UVf-VE" -o ./downloads
```

Commands that accept `--json` write exactly one JSON document to stdout: an object
for `info`, `formats`, and `bestaudio`, and an array for `search`. `download` writes
only the completed absolute path to stdout. Errors, diagnostics, and progress are
written to stderr and failures return a non-zero exit status.

## Tests

```console
pytest
```

Live YouTube access is disabled by default:

```console
$env:MYYT_RUN_INTEGRATION = "1"
pytest -m integration
```

See [docs/VERSIONS.md](docs/VERSIONS.md) for roadmap status and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design details. Complete Windows,
Linux/macOS, Docker, JSON-validation, testing, and VPS instructions are in
[docs/how_to_Run.md](docs/how_to_Run.md).
