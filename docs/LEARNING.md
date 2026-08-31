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
