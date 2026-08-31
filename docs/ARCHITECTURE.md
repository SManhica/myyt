# Architecture

## Version 0.2 boundaries

The v0.1 implementation deliberately has few modules. Each exists because it owns
a real responsibility; roadmap placeholders are not created as empty files.

### `myyt.models`

`VideoInfo` and `SearchResult` are normalized public results. Raw YouTube dictionaries
do not cross their extraction boundaries. Both models are immutable so downstream
code cannot accidentally change returned data.

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

### `myyt.youtube.parsing`

Contains schema-neutral primitives shared by watch-page and search parsing: embedded
JSON decoding, text runs, scalar validation, duration conversion, and thumbnail
selection. It has no HTTP or command-specific policy.

### `myyt.youtube.search`

`YouTubeSearch` retrieves the public search page, parses only video renderers from the
primary results, follows first-party continuation commands when necessary, removes
duplicate video IDs, and returns `SearchResult` values. `SearchPage` and
`WebClientConfig` keep continuation tokens and volatile client configuration internal.
The CLI never exposes either one as stable application data.

### `myyt.cli`

Parses commands, invokes the extractor, renders human or JSON output, and maps domain
errors to process status. JSON stdout contains no diagnostics.

## Dependency direction

`cli -> extractor/search -> client`

`cli -> models <- extractor/search`

`extractor/search -> parsing`

`url_parser -> exceptions <- client/extractor/search/cli`

The network layer knows nothing about normalized video models. The model knows
nothing about HTTP or command-line concerns.

## Deferred packages

Player/format processing, selection, downloading, fragments, progress, and FFmpeg
modules are absent until their versions require them. This prevents premature
interfaces from becoming accidental compatibility constraints.
