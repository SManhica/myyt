# Data Flow

## Metadata

```text
CLI info URL
    |
    v
YouTubeExtractor.extract
    +--> URL parser
    +--> YouTubeClient --> public watch page
    +--> player-response parser
    v
VideoInfo
    +--> human renderer --> stdout text
    +--> JSON renderer  --> stdout JSON
```

## Search

```text
CLI search QUERY
    |
    v
YouTubeSearch.search
    +--> YouTubeClient --> initial public results page
    +--> ytInitialData parser --> SearchResult values
    +--> bounded continuation requests when needed
    v
ordered, deduplicated SearchResult list --> stdout text or JSON
```

## Player formats and selection

```text
CLI formats/bestaudio URL
    |
    v
YouTubeExtractor.extract_player
    +--> watch metadata
    +--> public player-client resolution
    +--> streamingData normalization
    v
PlayerInfo + tuple[MediaFormat, ...]
    +--> formats renderer
    +--> select_best_audio --> bestaudio renderer
```

## Complete-file download

```text
CLI download URL
    |
    v
DownloadService
    +--> extractor --> PlayerInfo
    +--> selector --> MediaFormat
    +--> expiry check / bounded refresh
    v
HTTPDownloader --> FileSink --> temporary source file
    |
    +--> TransferProgress --> stderr
    v
FFmpegProcessor --> temporary MP3 --> final collision-free path
    |
    v
stdout: completed absolute path
```

The source and processed temporary files are owned by `DownloadService`. They are
removed on completion, error, or cancellation.

## Binary stream

```text
CLI stream URL
    |
    v
StreamService
    +--> extractor --> PlayerInfo
    +--> selector --> MediaFormat
    +--> pre-output expiry refresh when needed
    v
HTTPDownloader --> BinaryStreamSink --> stdout: source media bytes only
    |
    +--> TransferProgress --> stderr
    +--> diagnostics/errors --> stderr
```

No complete media file or FFmpeg process exists on this path. Network reads are
bounded and each chunk is written to stdout before the next is read.

## Retry state transition

```text
request fails
    |
    +--> emitted bytes == 0
    |       +--> normal bounded retry
    |       +--> HTTP 403/410: refresh URL; reselection allowed
    |
    +--> emitted bytes == N > 0
            +--> transient failure: request exact Range starting at N
            |       +--> HTTP 206 + matching Content-Range: continue
            |       +--> HTTP 200 or wrong range: fail
            |
            +--> HTTP 403/410: refresh URL
                    +--> exact same representation: exact-range resume
                    +--> changed/unverifiable representation: fail
```

Stdout cannot be rewound, so a non-zero failure after partial output is an explicit
part of the contract. Consumers must trust exit status, not merely the presence of
bytes.

## Downstream closure

```text
stdout write/flush --> BrokenPipe / EPIPE
    |
    +--> stop the active transfer
    +--> close the active HTTP response scope
    +--> do not retry
    +--> concise stderr diagnostic
    +--> exit 130
```

This treats a consumer that stops reading as cancellation rather than as an upstream
network failure.
