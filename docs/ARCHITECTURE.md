# Architecture

## Version 0.3 boundaries

The implementation deliberately creates modules only when they own a real
responsibility; roadmap placeholders are not created as empty files.

### `myyt.models`

`VideoInfo`, `SearchResult`, `MediaFormat`, and `PlayerInfo` are normalized public
results. Raw YouTube dictionaries do not cross their extraction boundaries. Models
are immutable so selection and future download code cannot alter extraction results.

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

### `myyt.youtube.client_context`

Decodes public `ytcfg` assignments and normalizes the API key, visitor data, client
version, and request context used by first-party search/player endpoints. It supports
direct-object and quoted-JSON assignment forms without evaluating JavaScript.

### `myyt.youtube.extractor`

Obtains a watch page, locates its embedded player response, checks response identity,
and normalizes `videoDetails` with `microformat` fallbacks into `VideoInfo`.
`extract_player` additionally orchestrates player-client resolution and format
normalization into `PlayerInfo`. It does not download media bytes or choose a format.

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

### `myyt.youtube.player`

Answers: "Which public player response gives us directly usable audio URLs?" It first
accepts a usable WEB response. When the WEB response contains metadata/SABR without
ordinary URLs, it calls isolated ANDROID and IOS public player profiles in order. The
module owns profile versions, headers, and response suitability checks. It does not
parse fields into formats or rank audio.

### `myyt.youtube.formats`

Answers: "What normalized media formats are present?" It parses `formats` and
`adaptiveFormats`, MIME types, codecs, quality, dimensions, length, URL expiry,
transport, range-fragment state, and cipher/`n` state. DASH/HLS manifest URLs are
preserved separately on `PlayerInfo`.

### `myyt.youtube.selector`

Answers: "Which available format is the best usable audio?" `select_best_audio` is a
pure function over `MediaFormat` values. It has no network, YouTube-response, CLI, or
downloader knowledge.

### `myyt.cli`

Parses commands, invokes the extractor, renders human or JSON output, and maps domain
errors to process status. JSON stdout contains no diagnostics.

## Dependency direction

`cli -> extractor/search -> client`

`extractor -> player -> client/client_context`

`extractor -> formats`

`cli -> selector -> models`

`cli -> models <- extractor/search/formats`

`extractor/search/formats/client_context -> parsing`

`url_parser -> exceptions <- client/extractor/search/cli`

The network layer knows nothing about normalized video models. The model knows
nothing about HTTP or command-line concerns.

## Deferred packages

Downloading, fragment transfer, progress, and FFmpeg modules are absent until v0.4.
Player-JavaScript signature and `n` transformation code is also absent because the
verified player fallback returns signed URLs that need neither transformation. Cipher
and `n` states remain explicit so upstream changes fail honestly.
