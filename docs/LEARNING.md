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
unusable rather than guessed. The verified Android/iOS fallback avoided both during
v0.3 development; v0.4.1 replaces it because GVS token policy later made those URLs
unsuitable for complete downloads.

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

## Version 0.4 — Downloader and FFmpeg

### Concepts introduced

- Binary streaming in bounded chunks instead of whole-file buffering
- Resumable HTTP transfers and byte ranges
- Separation between extraction, selection, transport, and post-processing
- Temporary-resource ownership and cleanup guarantees
- Cross-platform filename safety and collision handling
- Child-process lifecycle, exit codes, and diagnostic channels
- Progress as data separated from progress rendering
- Refreshing volatile capabilities such as signed media URLs

### Important Python APIs used

- `pathlib.Path` for explicit filesystem operations
- `tempfile.TemporaryDirectory` for scoped intermediate files
- `os.replace` for final same-filesystem publication
- `urllib.request.Request` with the HTTP `Range` header
- `http.client.IncompleteRead` for interrupted-response detection
- `subprocess.Popen`, `communicate`, `terminate`, and `kill` for FFmpeg management
- `shutil.which` for executable discovery
- `time.monotonic` for elapsed transfer time and `time.time` for URL expiry
- `unicodedata.normalize` for stable filename normalization

### Important networking concepts

A response body can end early even after the server accepted a request. The downloader
compares transferred bytes with `Content-Length`, `Content-Range`, or the expected
format length. A retry sends `Range: bytes=N-` for the verified partial length. It
appends only when the server returns HTTP 206 with a matching range start. If the
server returns HTTP 200, the local file is safely restarted instead.

HTTP 403 and 410 have special meaning for a direct YouTube media URL: the signed URL
may have expired or become invalid. The generic downloader reports that state; the
YouTube-aware service re-extracts once and resumes the same itag when possible. Other
retryable statuses and transient socket failures use bounded backoff.

### How this version works internally

`DownloadService` extracts `PlayerInfo`, runs the pure audio selector, and checks the
selected URL's expiry. It creates a temporary directory inside the destination so the
final move remains on one filesystem. `HTTPDownloader` writes the source incrementally.
`FFmpegProcessor` converts that source to MP3. Only after successful conversion does
the service choose a collision-free name and publish the result. Leaving the scope
removes all intermediate files on success, error, or cancellation.

Progress callbacks receive byte counts, elapsed time, throughput, and ETA. The CLI
renders progress and FFmpeg status on stderr. Stdout contains only the completed
absolute path, which remains easy for another process to consume.

### Functions and classes worth studying

- `HTTPDownloader.download`: bounded retry orchestration
- `HTTPDownloader._transfer`: range-aware incremental transfer
- `TransferProgress` and `ProgressReporter`: data/presentation separation
- `sanitize_filename` and `available_output_path`: filesystem boundary hardening
- `DownloadService.download`: use-case orchestration and cleanup ownership
- `DownloadService._download_with_refresh`: expiring-URL recovery
- `FFmpegProcessor.convert_to_mp3`: subprocess lifecycle and error mapping

### Suggested exercises

1. Add a fake response that ends early twice, then succeeds, and trace each range.
2. Compare interactive and redirected stderr progress behavior.
3. Add filename cases for Unicode normalization and Windows device names.
4. Replace the fake FFmpeg process with a tiny controlled helper executable in a test.
5. Design a segment model for HLS without coupling it to YouTube metadata.

## Version 0.4.1 — Validating playback capability

### Concepts introduced

- A URL's presence does not prove end-to-end playback authorization.
- Small health probes can produce false confidence when enforcement applies to real
  transfer behavior.
- Proof-of-Origin tokens are client- and purpose-specific attestation data, distinct
  from URL signatures and expiry timestamps.
- Client fallback policy must account for transport requirements, not only response
  shape.

### How the failure was isolated

The original Android URL passed a 1 KiB range test but rejected a full GET. Bounded
ranges showed that the problem was not ordinary expiry or resume corruption. Testing
another first-party profile separated media transfer behavior from the generic HTTP
downloader: the visionOS response supplied the same audio representation and completed
normally without adding an attestation token.

### Functions and classes worth studying

- `YouTubePlayer.resolve`: capability-aware client selection
- `PlayerClientProfile`: volatile first-party client identity kept behind one boundary
- `HTTPDownloader._transfer`: sequential range validation and resume

### Suggested exercises

1. Add a fake client whose first response has a URL but whose safe fallback succeeds.
2. Record full-transfer success separately from a small range probe in a live test.
3. Design a future PO-token provider interface without implementing attestation inside
   the format parser or downloader.

## Version 1.0 — Binary stdout and irreversible streams

### Concepts introduced

- Binary-safe standard output as a process protocol
- Sink abstractions for sharing transport logic across destinations
- Irreversible output and stronger recovery invariants
- Partial writes, broken pipes, and downstream cancellation
- Exact byte-range continuation after partial output
- Structural compatibility checks for refreshed media representations
- Completion validation and trustworthy process exit status

### Important Python APIs used

- `sys.stdout.buffer` for bytes rather than text
- `msvcrt.setmode` with `os.O_BINARY` for Windows binary output
- `typing.BinaryIO` and `Protocol` for narrow sink interfaces
- `memoryview` for completing partial output writes without copying a chunk
- `errno.EPIPE` and `BrokenPipeError` for closed-consumer detection
- `os.dup2` and `os.devnull` to prevent interpreter-shutdown pipe noise
- Context managers around HTTP responses for prompt cleanup

### Important networking concepts

HTTP retry behavior depends on whether output is reversible. A file can be truncated
and restarted if a server ignores `Range`. Stdout cannot: bytes may already have been
consumed elsewhere. After `N` bytes are emitted, a safe retry requests a range
starting at `N` and accepts only HTTP 206 with a matching `Content-Range` start.

HTTP 200 is valid for an initial response, but unsafe for a resume because it begins
at byte zero. Appending it would duplicate the prefix. A mismatched 206 is similarly
unsafe. Both cases fail explicitly.

A signed media URL can be refreshed after HTTP 403 or 410. Before output, normal
selection can run again. After output, the refreshed format must match the original
itag, MIME type, container, codecs, audio properties, and known content length. This
is an implementation safety policy: matching only the itag is not enough evidence to
mix two byte sequences.

### How this version works internally

`StreamService` extracts a `PlayerInfo`, selects audio, and creates a
`BinaryStreamSink` around the caller-owned output. `HTTPDownloader.transfer` performs
the same requests, bounded reads, retries, range validation, length accounting, and
progress callbacks used by file downloads. Only sink behavior differs.

Each received chunk is written before the next network read, so normal streaming
memory use is bounded by the configured chunk size plus library buffers. Successful
completion flushes the output and returns `StreamResult`; the CLI deliberately emits
no rendering of that result. A broken write becomes `StreamCancelledError`, is never
retried, and maps to exit 130 without a traceback.

### Functions and classes worth studying

- `HTTPDownloader.transfer`: destination-independent retry orchestration
- `HTTPDownloader._transfer`: exact range and completion validation
- `FileSink` and `BinaryStreamSink`: reversible versus irreversible output policy
- `StreamService.stream`: extraction, selection, refresh, and transfer orchestration
- `is_exact_resume_match`: refreshed-representation safety boundary
- `_process_binary_stdout`: platform-specific binary stdout setup
- `_replace_process_stdout_with_devnull`: clean broken-pipe shutdown

### Suggested exercises

1. Make a fake output object accept only two bytes per `write` and verify the sink
   completes the full chunk in order.
2. Add a retry fixture whose `Content-Range` starts one byte too late and confirm that
   no bytes from that response reach output.
3. Compare HTTP 200 and 206 behavior before and after the first emitted byte.
4. Pipe a short live stream into a consumer that exits after 100 bytes and inspect the
   producer's exit status and stderr.
5. Design a segmented sink contract without allowing already-emitted stdout bytes to
   be reordered or repeated.
