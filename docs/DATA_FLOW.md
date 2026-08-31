# Data Flow

## Version 0.1

```text
CLI arguments
    |
    v
YouTubeExtractor.extract
    |
    +--> parse_video_url --> ParsedVideoURL
    |
    +--> YouTubeClient.get_text --> public YouTube watch page
    |
    +--> extract_initial_player_response --> player-response mapping
    |
    +--> normalize_video_info --> VideoInfo
    |
    v
CLI human renderer or JSON serializer
    |
    +--> stdout: requested result only
    +--> stderr: errors/diagnostics only
```

The extractor asks what YouTube says about a video. It does not transfer media.
The client handles HTTP but does not understand video metadata.

## Version 0.2 search

```text
CLI query + limit
    |
    v
YouTubeSearch.search
    |
    +--> YouTubeClient.get_text --> /results HTML
    |
    +--> ytInitialData parser --> SearchPage
    |                                |
    |                                +--> SearchResult values
    |                                +--> opaque continuation token
    |
    +--> if more results are needed:
           ytcfg parser --> WebClientConfig
                              |
                              v
           YouTubeClient.post_json --> /youtubei/v1/search
                              |
                              v
                    continuation SearchPage
    |
    +--> ordered deduplication + limit
    |
    v
CLI human renderer or JSON array
```

Client configuration and continuation tokens never leave the search component. The
CLI receives only normalized `SearchResult` instances.

## Version 0.3 formats and audio selection

```text
CLI formats/bestaudio URL
    |
    v
YouTubeExtractor.extract_player
    |
    +--> URL parser
    +--> watch-page HTTP + initial player response
    +--> normalize VideoInfo
    |
    v
YouTubePlayer.resolve
    |
    +--> usable direct WEB audio? --> keep WEB response
    |
    +--> otherwise: public ytcfg --> ANDROID player request
    |                                  |
    |                                  +--> fallback IOS if needed
    v
response with directly usable audio URL
    |
    v
parse_streaming_formats --> tuple[MediaFormat, ...]
    |
    +--> formats command --> human table / PlayerInfo JSON
    |
    +--> select_best_audio (pure, no HTTP)
              |
              v
         bestaudio command --> human details / selected-format JSON
```

Future downloaders will receive the selected `MediaFormat`; they will not parse
YouTube metadata or duplicate selection rules.

## Planned later flow

```text
CLI / application process
    |
    v
YouTube extraction --> normalized formats --> audio selector
    |
    v
media downloader --> binary stdout
    |
    v
Node.js child process --> FFmpeg stdin --> MP3 --> Express response
```

Search is a sibling entry path into normalized `SearchResult` objects. Format
selection is now a pure decision over normalized formats. Downloaders will receive
media URLs/protocol information without parsing YouTube metadata.
