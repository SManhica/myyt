# Architecture

## Version 0.4.1 boundaries

The implementation deliberately creates modules only when they own a real
responsibility; roadmap placeholders are not created as empty files.

### `myyt.models`

`VideoInfo`, `SearchResult`, `MediaFormat`, `PlayerInfo`, and `DownloadResult` are
normalized public results. Raw YouTube dictionaries do not cross their extraction
boundaries. Models are immutable so selection and transfer code cannot alter
extraction results.

### `myyt.exceptions`

Expected failures have domain-specific types and stable process exit codes. Low-level
network and JSON errors are translated before they reach the CLI.

### `myyt.config`

Holds shared default timeout, retry, user-agent, chunk-size, and URL-refresh values.
It contains no environment loading or mutable global state; a fuller user-facing
configuration system remains a v1.0 concern.

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

Answers: "Which public player response gives us directly usable audio URLs?" The WEB,
Android, and iOS clients can expose URLs that now require a GVS Proof-of-Origin token;
the presence of a URL alone is therefore insufficient. V0.4.1 requests an isolated
public visionOS profile whose current GVS policy does not require that token. The
module owns profile versions, headers, and response suitability checks. It does not
generate attestation tokens, parse fields into formats, or rank audio.

### `myyt.youtube.formats`

Answers: "What normalized media formats are present?" It parses `formats` and
`adaptiveFormats`, MIME types, codecs, quality, dimensions, length, URL expiry,
transport, range-fragment state, and cipher/`n` state. DASH/HLS manifest URLs are
preserved separately on `PlayerInfo`.

### `myyt.youtube.selector`

Answers: "Which available format is the best usable audio?" `select_best_audio` is a
pure function over `MediaFormat` values. It has no network, YouTube-response, CLI, or
downloader knowledge.

### `myyt.download.http`

Answers: "Given a direct media URL, how are its bytes transferred?" `HTTPDownloader`
streams bounded chunks to a file, reports normalized progress, retries recoverable
failures, uses bounded byte ranges when length is known, resumes partial files,
validates the returned content range,
and distinguishes expired/rejected URLs from ordinary transfer failures. It knows
nothing about YouTube metadata, format selection, or FFmpeg.

### `myyt.download.progress`

Defines transfer progress data and the terminal renderer. Interactive terminals get
rate-limited in-place updates; redirected stderr receives only a final summary. This
keeps transport accounting separate from presentation.

### `myyt.download.filenames`

Sanitizes untrusted video titles for Windows, Linux, and macOS path rules, handles
reserved Windows device names, limits component length, and chooses collision-free
output names without overwriting an existing download.

### `myyt.download.service`

Owns the v0.4 use case: extract, select, refresh expiring URLs, transfer to an isolated
temporary directory, invoke FFmpeg, atomically move the result into place, and return
`DownloadResult`. It is the only component that coordinates YouTube extraction,
generic transfer, and post-processing.

### `myyt.media.ffmpeg`

Discovers the FFmpeg executable before network transfer and converts one local input
into MP3. It captures stderr, validates the exit code and output, and terminates the
child on cancellation.
It contains no YouTube, selection, HTTP, or filename policy.

### `myyt.cli`

Parses commands, invokes the extractor, renders human or JSON output, and maps domain
errors to process status. JSON stdout contains no diagnostics.

## Dependency direction

`cli -> extractor/search -> client`

`extractor -> player -> client/client_context`

`extractor -> formats`

`cli -> download.service -> extractor/selector/download.http/media.ffmpeg`

`cli -> download.progress`

`download.service -> download.filenames`

`download.http -> download.progress`

`cli -> selector -> models`

`cli -> models <- extractor/search/formats`

`extractor/search/formats/client_context -> parsing`

`url_parser -> exceptions <- client/extractor/search/cli`

The network layer knows nothing about normalized video models. The model knows
nothing about HTTP or command-line concerns.

## Deferred responsibilities

Direct adaptive MP4/WebM representations are fragmented containers internally, but
their signed URLs can currently be transferred as complete range-addressable HTTP
resources. A dedicated fragment scheduler is therefore not introduced prematurely.
DASH/HLS manifest expansion and segment scheduling remain deferred until a tested
content case requires them. Binary stdout streaming belongs to v1.0.

Player-JavaScript signature and `n` transformation code also remains absent because
the verified player fallback returns signed URLs that need neither transformation.
Cipher and `n` states remain explicit so upstream changes fail honestly.
