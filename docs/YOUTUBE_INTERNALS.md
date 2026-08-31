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
