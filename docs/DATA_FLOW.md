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

Search will be a sibling entry path into normalized `SearchResult` objects. Format
selection will remain a pure decision over normalized formats. Downloaders will
receive media URLs/protocol information without parsing YouTube metadata.
