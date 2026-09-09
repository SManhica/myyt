# Architecture

## Version 1.0 boundaries

The project creates modules only when they own a concrete responsibility. Raw
YouTube dictionaries are normalized at extraction boundaries; transfer and CLI code
operate on typed values.

### `myyt.models`

`VideoInfo`, `SearchResult`, `MediaFormat`, `PlayerInfo`, `DownloadResult`, and
`StreamResult` are immutable public results. `StreamResult` is returned internally by
the stream use case for completion accounting; it is deliberately not written to
stdout by the CLI.

### `myyt.exceptions`

Expected failures use domain types and stable exit codes. `UnsafeResumeError`
identifies a transfer that cannot continue without corrupting already-emitted bytes.
`StreamCancelledError` represents downstream pipe closure and uses exit code 130.

### `myyt.config`

Owns shared HTTP timeout, retry, user-agent, chunk, range, and URL-refresh defaults.
It has no network behavior or mutable global state.

### `myyt.youtube`

- `url_parser` validates supported URLs and produces canonical video identities.
- `client` centralizes YouTube HTTP headers, timeout, retry, GET, and JSON POST work.
- `client_context` parses public player/search client configuration.
- `parsing` contains defensive primitives for heterogeneous response trees.
- `extractor` normalizes watch/player data and never transfers media bytes.
- `search` owns search-page and continuation parsing.
- `player` isolates public player-client policy.
- `formats` maps raw streaming data into `MediaFormat` values.
- `selector` is a pure best-audio ranking function with no HTTP behavior.

### `myyt.download.selection`

Shares extraction/selection, expiry, same-itag lookup, and exact-representation
compatibility rules between file download and streaming orchestration. Exact resume
compatibility requires matching representation identity and media properties,
including a known, unchanged content length.

### `myyt.download.http`

`HTTPDownloader` is the single direct-media transfer engine. It reads bounded chunks,
uses bounded byte ranges when length is known, reports progress, validates response
lengths, and retries transient failures.

The engine writes through a small `TransferSink` contract:

- `FileSink` can safely truncate and restart when an origin ignores a resume range.
- `BinaryStreamSink` writes incrementally to a caller-owned binary stream and cannot
  retract bytes. After output begins, it accepts continuation only when the origin
  returns HTTP 206 with `Content-Range` starting at the exact current offset.

This is one transfer implementation with two destinations, not parallel download
and stream implementations. The sink owns destination semantics; the transport owns
HTTP correctness.

### `myyt.download.service`

`DownloadService` owns the complete-file use case: extract, select, refresh, transfer
to an isolated temporary directory, invoke FFmpeg, publish a collision-free MP3, and
return `DownloadResult`. Different-format reselection is safe here because a partial
temporary file can be discarded.

### `myyt.download.stream`

`StreamService` owns the irreversible stdout use case: extract, select, refresh near
expiry, and pass a `BinaryStreamSink` to the shared transfer engine. Before the first
byte, refresh may reselect normally. After the first byte, refresh may continue only
with an exact match for the original representation; otherwise it fails visibly.

The service creates no media file and has no dependency on the FFmpeg component.

### `myyt.download.progress`

`TransferProgress` is transport-neutral progress data. `ProgressReporter` renders it
only to stderr, rate-limiting interactive updates and emitting a final summary when
stderr is redirected.

### `myyt.download.filenames`

Owns portable filename sanitization and collision-free final-path selection for the
complete-file command. Streaming does not use it.

### `myyt.media.ffmpeg`

Discovers and manages FFmpeg for complete-file MP3 post-processing. It has no
YouTube, selection, or HTTP knowledge and is not invoked by `stream`.

### `myyt.cli`

Parses commands, maps domain failures to exit statuses, and maintains output-channel
contracts. It switches process stdout to binary mode on Windows before streaming.
On downstream closure it suppresses interpreter-shutdown pipe noise and exits 130
without retrying the write.

## Dependency direction

```text
cli -> youtube extractor/search/selector -> youtube client/parsers
cli -> DownloadService -> selection + HTTPDownloader + FFmpegProcessor
cli -> StreamService   -> selection + HTTPDownloader
HTTPDownloader -> TransferSink + TransferProgress
extractor/search/formats/services/cli -> immutable models
all public layers -> domain exceptions
```

The media transfer engine knows URLs and byte counts, not YouTube response schemas.
The selector knows formats, not networks. FFmpeg knows local input/output, not
extraction. These directions keep changes in volatile player behavior from spreading
into binary I/O code.

## Streaming correctness boundary

Before output begins, a failed request can be retried or refreshed because no
consumer-visible state exists. After output begins, stdout is irreversible. The only
safe recovery is the same representation at the current byte offset:

1. request `Range: bytes=N-...`, where `N` is exactly the emitted byte count;
2. require HTTP 206;
3. require `Content-Range` to start at `N`;
4. on URL refresh, require the same representation properties and total length;
5. fail on HTTP 200, mismatched ranges, changed formats, or unverifiable length.

This rule prevents silent duplication and mixed-format corruption. It intentionally
prefers a non-zero exit over output that merely appears complete.

## Deferred responsibilities

- DASH/HLS manifest expansion and segment scheduling for manifest-only content.
- Player-JavaScript signature and `n` transformation when a verified public response
  no longer supplies directly usable URLs.
- User-supplied cookie/configuration surfaces and richer structured logging controls.
- Additional output codecs for complete-file post-processing.

Private access, DRM, paywalls, CAPTCHA solving, and attestation bypasses remain out of
scope.
