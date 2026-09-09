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

## Version 0.3 player and format observations

Observed against public YouTube responses on 2026-08-31:

- The WEB watch response can contain `adaptiveFormats` metadata with no `url` or
  `signatureCipher`, plus `serverAbrStreamingUrl`. This was observed for ordinary and
  music videos and means format metadata alone is not a downloadable URL.
- A WEB response for another normal public video exposed one ciphered muxed format
  while adaptive formats still lacked URLs. Response shape varies per video.
- A public ANDROID player request returned `formats` and `adaptiveFormats` with direct
  signed URLs for all three tested videos. IOS also returned direct URLs in probing.
- The ANDROID request worked without `contentCheckOk`, `racyCheckOk`, authentication,
  cookies, or access-control override flags.
- The selected Android audio URL contained `sig` and `expire`, did not contain `n`,
  and returned HTTP 206 with 1,024 audio bytes for `Range: bytes=0-1023`.

These observations justified the v0.3 WEB -> ANDROID -> IOS resolution strategy at
the time. V0.4.1 supersedes it after full transfers demonstrated current GVS
Proof-of-Origin enforcement. Client versions remain isolated in `youtube/player.py`.

### `streamingData`

- `formats` usually contains muxed audio+video representations.
- `adaptiveFormats` contains separate audio-only or video-only representations.
- `mimeType` combines the media type and codec list, for example
  `audio/mp4; codecs="mp4a.40.2"`.
- `itag` identifies a representation but is not sufficient to choose quality by
  itself; fields and availability must be inspected.
- `contentLength` is a decimal byte count when present.
- `audioSampleRate` is commonly a decimal string while channels are numeric.
- `initRange` and `indexRange` indicate range-addressable fragmented container data.
- `dashManifestUrl` and `hlsManifestUrl` are optional alternative transports.

### URL and cipher state

V0.3 distinguishes:

- Direct URL: immediately available under `url`.
- Plain cipher signature: a cipher object whose non-encrypted `sig`/`signature` can be
  appended under its requested `sp` parameter.
- Encrypted signature: `signatureCipher.s`; recorded as ciphered with no usable URL.
- `n` parameter: recorded as requiring a player transform and excluded by the audio
  selector until transformation is implemented.

Player-JavaScript deciphering is not implemented in v0.3 because the verified public
player fallback returns usable signed URLs without it. If that changes, the future
implementation must be isolated, cached by player version, fixture-tested, and must
not silently return an untransformed URL.

### Best-audio policy

The selector ranks, in order:

1. audio-only over muxed audio+video;
2. recognized/supported audio codec;
3. YouTube audio-quality label;
4. effective average bitrate, falling back to bitrate;
5. codec preference as a tie-breaker;
6. direct HTTPS/HTTP transport;
7. sample rate;
8. known content length.

This is a declared application policy, not a fact supplied by YouTube.

### Confirmed limitations

- DASH/HLS manifest URLs are preserved but their manifests are not expanded into
  additional `MediaFormat` entries yet.
- Live-only content that has no direct audio representation can therefore fail
  selection.
- V0.3 exposes expiry but does not refresh URLs; v0.4 adds bounded refresh in the
  download orchestration layer.

## Version 0.4 transfer observations

V0.4 builds on the v0.3 live observation that a selected direct Android audio URL
accepted a byte-range request and reported HTTP 206. The downloader does not assume
that every origin will honor resume: it validates `Content-Range`, restarts safely on
HTTP 200, and fails rather than appending bytes from an incompatible range.

Observed in the live integration environment on 2026-09-01, the same public short
video path successfully transferred an entire selected audio representation and its
reported byte length matched the completed file. A separate end-to-end run converted
the source into a non-empty MP3 and left no `.myyt-*` temporary directory.

The adaptive formats commonly selected by `myyt` may have `initRange` and
`indexRange`, meaning their MP4/WebM container is internally fragmented and
range-addressable. This does not necessarily require issuing one request per media
fragment. When YouTube provides a direct signed URL for the complete representation,
v0.4 transfers that resource as one resumable HTTP file and lets FFmpeg demux it.

### Expiry and refresh policy

The `expire` query value normalized in v0.3 is used before transfer. If it falls
within the configured safety margin, the service obtains a fresh player response
before downloading. A media-origin HTTP 403 or 410 triggers one additional player
extraction. The same itag is preferred so a compatible partial transfer can continue;
if that representation disappears, the selector runs again and the partial file is
discarded before using a different format.

This recovery policy is an implementation decision, not a guarantee that every 403
means expiration. Account gates, regional restrictions, or upstream policy can also
produce rejection, and v0.4 does not bypass any of them. The refresh attempt is
bounded so persistent failures remain visible.

### Post-processing boundary

YouTube supplies the source representation, not the requested MP3. FFmpeg reads the
complete selected audio or muxed source and creates MP3 with `libmp3lame`. It is not
used to discover YouTube URLs or choose formats. Consequently, a transfer can succeed
while post-processing fails; these are reported as separate error classes and exit
codes.

### Still unconfirmed or deferred

- Manifest-only DASH/HLS content needs manifest parsing and segment-specific tests.
- Long transfers may require more than one URL refresh; v0.4 performs only one after
  an explicit rejection.
- Player signature/`n` transforms remain deferred unless public client responses stop
  providing usable signed URLs.

## Version 0.4.1 GVS Proof-of-Origin findings

Observed on 2026-09-01 for `M7lc1UVf-VE`:

- The Android player response still returned itag 140 with a signed URL and known
  content length.
- A 1,024-byte range returned HTTP 206, but an unbounded request returned HTTP 403.
- A first large range could succeed while a later range was rejected. Refreshing the
  Android player URL did not make the complete transfer usable.
- The public visionOS player response returned 25 adaptive formats. Its selected itag
  140 URL returned HTTP 200 for an ordinary request and completed the entire transfer.
- The resulting source converted to MP3 successfully through the normal v0.4 pipeline.

The important correction is that a signed URL and a successful small probe no longer
prove that a format is fully downloadable. Current YouTube clients can require a GVS
Proof-of-Origin token bound to the video or session. V0.4.1 does not generate or bypass
that attestation. It uses a public client whose current policy does not require it and
fails visibly if that assumption changes.

Engineering references consulted for this change:

- <https://github.com/yt-dlp/yt-dlp/wiki/Po-Token-Guide>
- <https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/youtube/_base.py>

The reference implementation was used to identify the protocol concept and current
client policy. `myyt` retains its own small player-profile and transfer implementation.

## Version 1.0 streaming observations

Observed against a public short video on 2026-09-09:

- The current public player profile returned a directly usable audio representation
  with a reported content length.
- The selected representation was transferred through the stdout-oriented service
  to its complete reported byte count.
- The transfer used the same signed direct-media URL and HTTP range machinery as the
  complete-file downloader; no separate YouTube endpoint was required for streaming.

These observations confirm the current direct-representation path, not a permanent
YouTube protocol guarantee. Player profiles, URL proof requirements, range behavior,
and available formats remain subject to change.

### Implementation policy, not upstream fact

Version 1.0 treats stdout as irreversible. After any bytes are emitted, a refreshed
URL is accepted only for a normalized representation matching the original itag,
MIME/container/codec properties, audio parameters, and known total byte length. The
subsequent HTTP response must be 206 and begin at the exact emitted offset.

YouTube does not declare this recovery policy. It is a conservative client rule that
prevents duplicated prefixes or mixed representations when temporary URLs expire.
An unverifiable continuation fails visibly even if a more permissive client might
attempt it.
