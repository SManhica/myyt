# YouTube Internals

This document separates observed behavior from design assumptions. YouTube's
undocumented web-client structures can change without notice.

## Version 0.1 observations

### Confirmed by public documentation

- A YouTube video has a video ID. The official IFrame Player API accepts a `videoId`
  when loading a video.
- Official video resources distinguish a stable video ID, snippet-like metadata,
  thumbnails, channel identity, and duration. `myyt` uses similar normalized names
  but does not call the authenticated/quota-controlled YouTube Data API.

References:

- <https://developers.google.com/youtube/iframe_api_reference>
- <https://developers.google.com/youtube/v3/docs/videos>

### Confirmed by watch-page fixtures and live-client observation

- Common public URLs can be reduced to an 11-character video ID and a canonical
  `/watch?v=...` URL.
- A public watch page commonly assigns a JSON object to
  `ytInitialPlayerResponse`.
- The response commonly contains `videoDetails` with `videoId`, `title`, `author`,
  `channelId`, `lengthSeconds`, and thumbnails.
- `microformat.playerMicroformatRenderer` can provide fallback title, channel,
  duration, and thumbnail fields.
- `playabilityStatus` can carry a status and human-readable reason when normal
  video details are absent.

These embedded names are not a documented API contract. Tests record known shapes;
the extractor treats missing and malformed fields as explicit failures rather than
silently fabricating metadata.

## Metadata strategy

Version 0.1 requests the public watch page with a browser-like user agent, English
language preference, and consent/preferences cookies that do not authenticate a
user. It parses the full embedded player response rather than relying solely on
OpenGraph title and thumbnail tags. This gives the project a direct path toward the
`streamingData` work in v0.3 while keeping the normalized model independent.

The HTTP client already supports JSON POST requests. A future version may need a
public YouTube web-client player request using configuration obtained from the page.
That is not implemented in v0.1 because metadata is available in the initial player
response for the supported public-page path.

## Assumptions and volatility

- The exact JavaScript assignment spelling may vary. V0.1 recognizes two observed
  assignment forms and fails clearly when neither exists.
- Consent, bot checks, geography, age gates, and experiments may produce a page with
  no usable player response. V0.1 does not bypass those controls.
- Metadata availability can differ even when a page is publicly reachable.

## Risks carried into v0.3

- `streamingData.formats` and `adaptiveFormats` vary by YouTube client context.
- Direct media URLs expire and cannot be treated as permanent identifiers.
- Some format URLs may use `signatureCipher` instead of an immediately usable URL.
- Player JavaScript may transform signatures and the `n` query parameter. Those
  algorithms are player-version-dependent and require isolated caches and fixtures.
- DASH/HLS manifests and direct HTTP formats require distinct protocol handling.
- Live content, premieres, region restrictions, and client integrity signals can
  change the available player response.

V0.3 should preserve raw response fixtures, model expiration explicitly, and keep
player-JavaScript processing separate from both format ranking and media transfer.

## Version 0.2 search observations

Observed against the public web client on 2026-08-31:

- `/results?search_query=...` embeds its initial response in `ytInitialData`.
- Primary results currently appear below
  `contents.twoColumnSearchResultsRenderer.primaryContents.sectionListRenderer`.
- Normal video entries use `videoRenderer`; channels, playlists, ads, and other
  surfaces use different renderer names.
- Titles and channel names use either `simpleText` or concatenated `runs`.
- Search durations are display strings such as `4:33`, unlike the decimal second
  strings used by the player response.
- The initial page currently provides a `continuationItemRenderer` after its first
  result batch.
- Public web-client configuration is delivered through `ytcfg.set(...)`. Current
  pages may pass that configuration as a quoted JSON string rather than a direct
  object.
- The continuation request uses `/youtubei/v1/search`, the opaque token, and the
  public page's API key and client context. Later responses place result items under
  response-received command/action containers.

These are observed web-client structures, not documented YouTube Data API contracts.
Fixtures preserve representative shapes and the parser validates required containers.

### Search normalization decisions

- Only valid 11-character `videoRenderer.videoId` entries with titles become results.
- Missing channel, thumbnail, or duration fields become JSON `null`; they do not
  invalidate an otherwise usable result.
- Duplicate video IDs are removed while preserving first-seen order.
- A valid page with no video renderers produces an empty result list.
- Continuation tokens, visitor data, API keys, tracking fields, and renderer details
  are transport state and never enter the public `SearchResult` schema.

Search results cannot provide reliable media file size. Size depends on the selected
format and its content length, so it remains a v0.3 concern rather than an invented
search field.
