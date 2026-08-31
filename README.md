# myyt

`myyt` is a YouTube-only metadata extraction and media downloading project written
from scratch in Python. Version 0.3 provides metadata, search, player-format
extraction, and explicit best-audio selection. It does not import, wrap, or invoke
yt-dlp or another downloader.

## Current capabilities (v0.3)

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
- Rank and select the best directly usable audio format.
- Emit readable terminal output or JSON-only stdout.
- Run deterministic fixture-based tests; live tests are opt-in.

Full media downloading, FFmpeg processing, and binary stdout streaming are
intentionally not implemented yet.

## Requirements

- Python 3.11 or newer
- `pytest` for development and tests

The runtime through v0.3 uses only the Python standard library.

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
```

JSON mode writes exactly one JSON document to stdout: an object for `info` and an
array for `search`. Errors and diagnostics are written to stderr and failures return
a non-zero exit status.

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
