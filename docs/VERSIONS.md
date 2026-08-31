# Versions

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
- No formats, media download, FFmpeg, or streaming.

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

### Next milestone: 0.3

- Obtain and normalize `streamingData.formats` and `adaptiveFormats`.
- Add typed audio/video format models and MIME/codec parsing.
- Model direct URLs, ciphered URLs, expiry, and protocol.
- Investigate current player JavaScript signature and `n` transformations.
- Add `myyt formats URL` and `myyt bestaudio URL`.
- Implement explicit, fixture-tested best-audio ranking without HTTP in the selector.

## 0.3 — Player and format extraction

Status: not started.

## 0.4 — Downloader and FFmpeg

Status: not started.

## 1.0 — Robust streaming and application integration

Status: not started.
