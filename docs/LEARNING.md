# Learning Guide

## Version 0.1 — URL and metadata extraction

### Concepts introduced

- Python packages and `src/` layout
- Immutable, slotted dataclasses
- Type annotations and narrow internal interfaces
- Domain-specific exception hierarchies
- Dependency injection for deterministic tests
- Separating transport data from normalized application data

### Important Python APIs used

- `urllib.parse` for URL decomposition and query parsing
- `urllib.request` for HTTP requests without a runtime dependency
- `json.JSONDecoder.raw_decode` for decoding one JSON value embedded in HTML
- `dataclasses` for `VideoInfo` and `HTTPResult`
- `argparse` for command dispatch and usage errors
- `sys.stdout` and `sys.stderr` for separate data and diagnostic channels

### Important networking concepts

An HTTP request can fail before a response, fail with a retryable status, or return
content whose structure is unexpected. `YouTubeClient` applies a bounded retry policy
to transient failures and never retries every error indiscriminately. Timeouts prevent
a request from waiting forever. Headers provide a stable language preference so
diagnostic and metadata variations are reduced.

Retries use exponential delay plus jitter. Increasing pauses reduce repeated load on
a struggling service; jitter keeps multiple clients from retrying in lockstep.

### How this version works internally

The CLI validates the URL through the extractor. The URL parser reduces supported
forms to a video ID and canonical watch URL. The client retrieves the watch page.
The extractor locates the JavaScript assignment containing the initial player
response, decodes the JSON object, combines `videoDetails` and microformat fields,
and returns `VideoInfo`. Only the CLI decides how to display it.

### Functions and classes worth studying

- `parse_video_url`: strict host and ID validation
- `YouTubeClient.request`: bounded retry and error translation
- `extract_initial_player_response`: parsing JSON without a brittle regular
  expression for nested braces
- `normalize_video_info`: defensive normalization of a variable external schema
- `main`: exit codes and clean stdout/stderr contracts

### Suggested exercises

1. Add table-driven tests for more URL query parameter orders.
2. Inject a fake HTTP 503 twice, then success, and inspect retry counts.
3. Add a fixture with missing channel metadata and observe the JSON `null` values.
4. Compare `json.JSONDecoder.raw_decode` with a greedy `{.*}` regular expression
   on nested objects and strings containing braces.
5. Add a CLI test for a video longer than one hour.

## Version 0.2 — YouTube search

### Concepts introduced

- Recursive traversal of heterogeneous JSON renderer trees
- Generators that yield matching structures without copying the whole response
- Ordered deduplication with sets plus lists
- Pagination and continuation tokens
- Parsing a constrained JavaScript string representation without evaluating code
- Separating public result models from internal transport state

### Important Python APIs used

- `Iterator` and generator functions for renderer discovery
- `Mapping` checks for defensive JSON traversal
- `json.JSONDecoder.raw_decode` for objects embedded in HTML
- `json.loads` after deterministic JavaScript-string decoding
- `argparse` type validators for `--limit`

### Important networking concepts

The initial search result is a normal HTML page. It contains both initial result data
and the public web-client context used by YouTube itself. When the requested limit is
larger than that page, `myyt` sends the continuation token and client context to the
same first-party search endpoint. Continuation tokens are opaque and temporary: code
must pass them back unchanged and must not infer meaning from their contents.

Requests remain bounded. V0.2 accepts at most 100 results, follows at most ten pages,
stops on repeated tokens, and stops when a page adds no new videos. These guards avoid
infinite pagination loops when upstream responses are inconsistent.

### How this version works internally

`YouTubeSearch.search` validates the query and limit, retrieves `/results`, extracts
`ytInitialData`, and scopes parsing to the primary search list. Recursive traversal
finds `videoRenderer` objects even inside supported shelves. Incomplete or non-video
renderers are skipped. Valid entries become `SearchResult` values.

If more results are needed, the search component decodes `ytcfg` web-client settings,
POSTs the continuation request, normalizes new results, and removes duplicate video
IDs. The CLI serializes the resulting list as one JSON array.

### Functions and classes worth studying

- `YouTubeSearch.search`: bounded pagination and ordered deduplication
- `parse_initial_search_page`: required response-container validation
- `_renderer_values`: recursive generator traversal
- `_normalize_video_renderer`: missing-field policy and model construction
- `extract_web_client_config`: safe decoding without `eval`
- `_render_search`: human versus JSON stdout contracts

### Suggested exercises

1. Add a fixture containing a live result with no `lengthText`.
2. Add a continuation fixture that repeats a video ID and verify stable ordering.
3. Trace which renderer kinds are ignored by the video-only search contract.
4. Add a malformed `ytcfg` assignment and verify that limits satisfied by the first
   page still succeed.
5. Compare a 5-result and 21-result request to see when pagination begins.

## Version 0.3 — Player and format extraction

### Concepts introduced

- Layered fallback strategies for volatile network clients
- MIME types, containers, and codec identifiers
- Muxed versus adaptive audio/video streams
- Expiring signed URLs and Unix timestamps
- Pure ranking functions and lexicographic tuple ordering
- Range-addressable/fragmented media metadata
- Parsing query strings inside cipher payloads

### Important Python APIs used

- `urllib.parse.urlparse`, `parse_qs`, `urlencode`, and `urlunparse`
- Frozen dataclasses for normalized `MediaFormat` and `PlayerInfo`
- Tuples for immutable codec lists and ranking keys
- `max(..., key=...)` for explicit audio selection policy
- `collections.abc.Mapping` for defensive response validation

### Important networking concepts

The normal WEB player response does not always expose individual media URLs. Current
responses may list format metadata plus a server-assisted ABR URL. A different public
first-party player context can return direct signed format URLs. `YouTubePlayer`
isolates this client variation from metadata parsing and selection.

Direct media URLs contain signatures and an `expire` query value. They are temporary,
not stable identifiers. V0.3 validates a selected URL with an HTTP byte-range request
in live tests, but full streaming/download transfer belongs to v0.4.

### How this version works internally

`YouTubeExtractor.extract_player` obtains watch metadata and asks `YouTubePlayer` for
a response with a direct audio URL. `parse_streaming_formats` converts every recognized
muxed/adaptive entry into `MediaFormat`. `select_best_audio` filters unusable URLs and
ranks candidates without making HTTP calls. The CLI renders all formats or the single
selected audio result.

Encrypted `signatureCipher.s` values and untransformed `n` parameters are recorded as
unusable rather than guessed. The verified ANDROID/IOS fallback currently avoids both.

### Functions and classes worth studying

- `YouTubePlayer.resolve`: bounded public client fallback
- `parse_streaming_formats`: raw-list traversal and deduplication
- `parse_mime_type` and `classify_codecs`: media type normalization
- `normalize_format`: expiry, size, adaptive, cipher, and transport fields
- `select_best_audio`: pure multi-factor ranking
- `YouTubeExtractor.extract_player`: orchestration without responsibility leakage

### Suggested exercises

1. Compare itags and codecs across the three live integration video IDs.
2. Change selector bitrates in fixtures and predict the winning tuple before testing.
3. Add a format URL containing `n` and verify it is not selected.
4. Add an unknown codec fixture and inspect the normalized fallback behavior.
5. Convert an `expires_at` epoch to a timezone-aware Python `datetime`.
