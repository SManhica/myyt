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

Search is now a sibling entry path into normalized `SearchResult` objects. Format
selection will remain a pure decision over normalized formats. Downloaders will
receive media URLs/protocol information without parsing YouTube metadata.
