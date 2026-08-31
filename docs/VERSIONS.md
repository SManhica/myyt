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
- No search, formats, media download, FFmpeg, or streaming.

### Known failures

- A response without a usable embedded player response raises `ExtractionError`.
- An unavailable response without video metadata raises `VideoUnavailableError`.
- Region- or account-restricted content is not bypassed.

### Next milestone: 0.2

- Add `myyt search QUERY`, `--limit`, and `--json`.
- Add typed `SearchResult` and defensive renderer traversal.
- Centralize public YouTube client context needed by search requests.
- Add fixtures for no-results, missing fields, shelves, and continuation tokens.
- Design continuation handling without forcing pagination into the initial CLI.

## 0.2 — Search

Status: not started.

## 0.3 — Player and format extraction

Status: not started.

## 0.4 — Downloader and FFmpeg

Status: not started.

## 1.0 — Robust streaming and application integration

Status: not started.
