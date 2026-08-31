# myyt

`myyt` is a YouTube-only metadata extraction and media downloading project written
from scratch in Python. Version 0.1 provides public video URL parsing and metadata
extraction. It does not import, wrap, or invoke yt-dlp or another downloader.

## Current capabilities (v0.1)

- Parse `youtube.com/watch`, `youtu.be`, and `youtube.com/shorts` URLs, plus common
  mobile, live, and embed variants.
- Retrieve a public watch page through a retrying YouTube HTTP client.
- Normalize embedded player metadata into a typed `VideoInfo` model.
- Emit readable terminal output or JSON-only stdout.
- Run deterministic fixture-based tests; live tests are opt-in.

Search, format discovery, downloading, FFmpeg processing, and binary stdout
streaming are intentionally not implemented yet.

## Requirements

- Python 3.11 or newer
- `pytest` for development and tests

The v0.1 runtime uses only the Python standard library.

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
```

JSON mode writes exactly one JSON object to stdout. Errors and diagnostics are
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
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design details.
