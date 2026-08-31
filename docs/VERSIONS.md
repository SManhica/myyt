# Versions

Release rule: every version must update `docs/how_to_Run.md` with current Windows
PowerShell, Linux/macOS, Docker, command, output, test, JSON-validation,
troubleshooting, and VPS instructions.

## 0.1.0 — URL and metadata extraction

Status: implemented.

### Implements

- Common YouTube URL parsing and canonical watch URLs
- Typed `VideoInfo`
- Centralized HTTP client with timeout, user agent, retries, GET, and JSON POST
- Embedded initial-player-response parsing
- `videoDetails` normalization with microformat fallbacks
- Human and JSON `info` output
- Domain error types and non-zero exit codes
- Fixture-based unit tests and opt-in live integration test

### Current limitations

- Only public, directly reachable watch pages are supported.
- No login cookies, private access, age-gate handling, or CAPTCHA handling.
- Only two known initial-player-response assignment forms are recognized.
- Watch-page experiments, consent interstitials, or bot checks may prevent extraction.
- Description and live-status normalization are deferred until their consumers and
  response variants are defined.
- No media download, FFmpeg, or streaming.

### Known failures

- A response without a usable embedded player response raises `ExtractionError`.
- An unavailable response without video metadata raises `VideoUnavailableError`.
- Region- or account-restricted content is not bypassed.

## 0.2.0 — Search

Status: implemented.

### Implements

- `myyt search QUERY`, `--limit N`, and `--json`
- Typed, immutable `SearchResult`
- Public search-page acquisition and `ytInitialData` extraction
- Defensive video-renderer parsing, including nested shelf results
- Missing optional fields represented as `null`
- Valid empty result lists
- First-party continuation requests using public `ytcfg` client context
- Ordered video-ID deduplication and bounded pagination
- Fixture coverage for standard, malformed, nested, empty, and continuation responses
- Live continuation integration test
- Stable JSON search schema: an array of normalized result objects

### Current limitations

- Search returns videos only; channel and playlist renderer output is intentionally
  excluded.
- Results are capped at 100 and continuation traversal at ten pages per invocation.
- YouTube search ranking, regionalization, and experiments control the returned order.
- Public client configuration or renderer schema changes can require fixture and
  parser updates.
- Search cannot report media size before v0.3 format extraction.

### Known failures

- Missing primary result containers raise `SearchError` instead of being mistaken for
  a legitimate empty search.
- A continuation failure fails the command; partial result arrays are not emitted.
- CAPTCHA, authentication, and access-control challenges are not bypassed.

## 0.3.0 — Player and format extraction

Status: implemented.

### Implements

- `myyt formats URL` and `myyt bestaudio URL`, both with JSON-only mode
- Immutable `MediaFormat` and `PlayerInfo` models
- Shared, safe public `ytcfg` client-context parser
- WEB response use when direct audio is already available
- Bounded ANDROID then IOS public player fallback for direct format URLs
- `formats` and `adaptiveFormats` normalization
- MIME type, container, audio/video codec, bitrate, sample rate, channels, dimensions,
  FPS, quality, byte length, protocol, adaptive, fragmented, and expiry fields
- Explicit direct, plain-signature, encrypted-cipher, and `n`-transform state
- DASH/HLS manifest URL discovery
- Pure, explicitly ranked best-audio selector
- Fixtures for SABR-without-URLs, direct formats, muxed/adaptive formats, manifests,
  plain cipher signatures, and unresolved encrypted signatures
- Live tests across three public video categories and an HTTP range validation
- Cross-platform Windows/Linux/macOS/Docker/VPS runbook in `docs/how_to_Run.md`

### Current limitations

- Player client versions are volatile and may require updates when YouTube changes.
- Encrypted `signatureCipher.s` and `n` transformations are recognized but not
  deciphered. Current verified Android/IOS responses avoid them.
- DASH/HLS URLs are exposed but manifests are not expanded into formats.
- No automatic media-URL refresh exists before v0.4/v1.0 transfer layers.
- No full download, fragment transfer, FFmpeg processing, or binary stdout streaming.

### Known failures

- SABR-only WEB data with unavailable Android/IOS URLs raises `FormatExtractionError`.
- Manifest-only live content may have no selectable direct audio format.
- Expired URLs return upstream HTTP errors and must be re-extracted manually.
- Private, account-gated, CAPTCHA, and access-controlled content is not bypassed.

### Next milestone: 0.4

- Add chunked HTTP media transfer without loading full files into RAM.
- Add retry, timeout, progress, cancellation, and partial-file cleanup behavior.
- Add filename sanitization and safe output paths.
- Add FFmpeg discovery, subprocess management, and MP3 post-processing.
- Re-extract formats when a selected media URL expires before/during transfer.
- Add fragment transfer architecture where direct range download is insufficient.

## 0.4 — Downloader and FFmpeg

Status: not started.

## 1.0 — Robust streaming and application integration

Status: not started.
