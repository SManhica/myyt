# Architecture

## Version 0.1 boundaries

The v0.1 implementation deliberately has few modules. Each exists because it owns
a real responsibility; roadmap placeholders are not created as empty files.

### `myyt.models`

`VideoInfo` is the normalized public result. Raw YouTube dictionaries do not cross
the extractor boundary. It is immutable so downstream selection and download code
cannot accidentally change extraction results.

### `myyt.exceptions`

Expected failures have domain-specific types and stable process exit codes. Low-level
network and JSON errors are translated before they reach the CLI.

### `myyt.youtube.url_parser`

Validates supported YouTube hosts and path shapes, extracts the 11-character video
ID, and produces one canonical watch URL. It contains no network logic.

### `myyt.youtube.client`

Owns HTTP headers, timeouts, retry policy, response decoding, query encoding, and
JSON POST support. The injected opener and sleeper make retry behavior testable.
Future cookies and YouTube client context belong at or above this boundary, not in
individual extractors.

### `myyt.youtube.extractor`

Obtains a watch page, locates its embedded player response, checks response identity,
and normalizes `videoDetails` with `microformat` fallbacks into `VideoInfo`. It does
not download media bytes or select formats.

### `myyt.cli`

Parses commands, invokes the extractor, renders human or JSON output, and maps domain
errors to process status. JSON stdout contains no diagnostics.

## Dependency direction

`cli -> extractor -> client`

`cli -> models <- extractor`

`url_parser -> exceptions <- client/extractor/cli`

The network layer knows nothing about normalized video models. The model knows
nothing about HTTP or command-line concerns.

## Deferred packages

Search, player/format processing, selection, downloading, fragments, progress, and
FFmpeg modules are absent until their versions require them. This prevents premature
interfaces from becoming accidental compatibility constraints.
