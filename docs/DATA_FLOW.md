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

## Current formats and audio selection (v0.4.1)

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
    +--> public ytcfg --> VISIONOS player request
    |                       |
    |                       +--> direct audio without GVS proof-token requirement
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

The v0.4 downloader receives the selected `MediaFormat`; it does not parse YouTube
metadata or duplicate selection rules.

## Version 0.4 download

```text
CLI download URL + output directory
    |
    v
DownloadService
    |
    +--> YouTubeExtractor.extract_player --> PlayerInfo
    |                                           |
    |                                           v
    |                                  select_best_audio
    |                                           |
    |                         expires soon? ----+----> re-extract once
    |                                           |
    v                                           v
temporary source file <-- HTTPDownloader <-- signed media URL
    |
    +--> chunked writes + Range resume
    +--> TransferProgress --> stderr renderer
    +--> HTTP 403/410 --> re-extract once --> same itag or safe restart
    |
    v
FFmpegProcessor --> temporary MP3
    |
    v
collision-free final path --> stdout
```

Search is a sibling entry path into normalized `SearchResult` objects. Format
selection remains a pure decision over normalized formats. The generic downloader
knows only a URL, expected length, destination, and progress callback. Temporary
source and failed FFmpeg output are removed when the service scope exits.

## Planned v1.0 streaming flow

```text
YouTube extraction --> normalized formats --> audio selector
    |
    v
media downloader --> binary stdout only
    |
    v
Node.js child process --> FFmpeg stdin --> MP3 --> Express response
```

The v0.4 `download` command does not claim this contract. It writes a final path to
stdout; `stream` will introduce the binary-stdout interface in v1.0.
