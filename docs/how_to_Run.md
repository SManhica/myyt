# How to Run and Test

This guide covers `myyt` 1.0 on Windows PowerShell, Linux/macOS shells, Docker, and
Linux VPS hosts. Run commands from the repository root unless stated otherwise.

## 1. Environment setup

Requirements:

- Python 3.11 or newer; Python 3.12 is recommended.
- Internet access to public YouTube pages, player endpoints, and media hosts for live
  commands and integration tests.
- FFmpeg only for `myyt download`; `stream` emits the selected source bytes directly
  and does not invoke FFmpeg.
- Docker Engine or Docker Desktop only for the container workflow.

The Python runtime has no third-party dependencies. The development extra installs
`pytest`.

### Windows PowerShell

```powershell
py --version
$PSVersionTable.PSVersion
ffmpeg -version
```

Install Python from python.org if the `py` launcher is missing. Install FFmpeg only
when using `download`, add its `bin` directory to `PATH`, and reopen PowerShell.

For direct binary redirection with `>`, use PowerShell 7.4 or newer. This repository's
binary probe was verified on PowerShell 7.6.5. Windows PowerShell 5.1 can transform
native output through its text pipeline; use the `Start-Process` recipe in the stream
section instead.

### Linux/macOS shell

```sh
python3 --version
ffmpeg -version
```

On Debian/Ubuntu:

```sh
sudo apt-get update
sudo apt-get install -y python3 python3-venv
sudo apt-get install -y ffmpeg  # only needed for download
```

On macOS, use a current python.org package or Homebrew. FFmpeg is optional unless
running `download`:

```sh
brew install ffmpeg
```

### Docker

```sh
docker --version
docker build -t myyt:1.0 .
```

The image contains Python, a dedicated virtual environment, the project, tests, and
FFmpeg. It runs as a non-root user.

## 2. Virtual environment creation and activation

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Alternatively, do not activate; use `.\.venv\Scripts\python.exe` and
`.\.venv\Scripts\myyt.exe` explicitly. Run `deactivate` to leave the environment.

### Linux/macOS shell

```sh
python3 -m venv .venv
source .venv/bin/activate
python --version
```

Run `deactivate` to leave the environment.

### Docker

The image creates `/opt/myyt-venv` and places it on `PATH`. No host virtual
environment is needed. To inspect it:

```sh
docker run --rm -it --entrypoint /bin/sh myyt:1.0
which python
which myyt
. /opt/myyt-venv/bin/activate
```

## 3. Project installation

With the local virtual environment active:

```sh
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
myyt --version
```

Expected:

```text
myyt 1.0.0
```

For runtime-only installation:

```sh
python -m pip install -e .
```

If a generated launcher is blocked, every command also works through the module
entry point:

```sh
python -m myyt --version
python -m myyt info "https://youtu.be/M7lc1UVf-VE"
```

## 4. Commands

Quote URLs and queries on every platform.

### `myyt info URL`

```sh
myyt info "https://www.youtube.com/watch?v=M7lc1UVf-VE"
myyt info "https://youtu.be/dQw4w9WgXcQ" --json
myyt info "https://www.youtube.com/shorts/jNQXAC9IVRw" --json
```

Human mode prints labeled metadata. JSON mode prints one normalized object.

### `myyt search QUERY`

```sh
myyt search "Coldplay Yellow"
myyt search "Python networking tutorial" --limit 5
myyt search "Mozambique music" --limit 25 --json
```

`--limit` accepts 1 through 100. JSON mode prints one array of normalized videos.

### `myyt formats URL`

```sh
myyt formats "https://youtu.be/M7lc1UVf-VE"
myyt formats "https://youtu.be/yKNxeF4KMsY" --json
myyt formats "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --json
```

Human mode prints a format table. JSON mode includes video data, player client,
manifests, formats, codecs, lengths, and temporary media URLs.

### `myyt bestaudio URL`

```sh
myyt bestaudio "https://youtu.be/M7lc1UVf-VE"
myyt bestaudio "https://youtu.be/yKNxeF4KMsY" --json
myyt bestaudio "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --json
```

The pure selector prefers usable audio-only representations, supported codecs,
quality/bitrate, direct transport, sample rate, and known length.

### `myyt download URL`

FFmpeg must be on `PATH`. The output option is a directory and is created when
needed. Existing files are not overwritten.

```sh
myyt download "https://youtu.be/jNQXAC9IVRw"
myyt download "https://youtu.be/M7lc1UVf-VE" -o ./downloads
myyt download "https://youtu.be/yKNxeF4KMsY" -o ./music --audio-format mp3 --no-progress
```

Progress and FFmpeg diagnostics go to stderr. Success writes only the final absolute
MP3 path to stdout.

### `myyt stream URL`

`stream` writes source media bytes only to stdout. It does not produce MP3, print a
title, append a newline, invoke FFmpeg, or create a complete-media temporary file.
The selected source is commonly MP4/M4A or WebM; inspect `bestaudio --json` when the
container matters.

Linux/macOS examples:

```sh
myyt stream "https://youtu.be/jNQXAC9IVRw" --no-progress > source-audio.bin
myyt stream "https://youtu.be/M7lc1UVf-VE" 2>stream.log | wc -c
myyt stream "https://youtu.be/yKNxeF4KMsY" --no-progress | sha256sum
```

Use `set -o pipefail` in scripts so a producer failure is not hidden by the final
consumer's status.

PowerShell 7.4 or newer preserves native bytes through native redirection:

```powershell
myyt stream "https://youtu.be/jNQXAC9IVRw" --no-progress > .\source-audio.bin
$stream = Start-Process -FilePath "myyt" -ArgumentList @("stream", "https://youtu.be/M7lc1UVf-VE") -RedirectStandardOutput ".\source-audio.bin" -RedirectStandardError ".\stream.log" -Wait -PassThru
$stream.ExitCode
myyt stream "https://youtu.be/yKNxeF4KMsY" --no-progress > .\another-source.bin; $LASTEXITCODE
```

For Windows PowerShell 5.1, do not use its `>` or pipeline for binary media. Use
native process redirection:

```powershell
$stream = Start-Process -FilePath ".\.venv\Scripts\myyt.exe" -ArgumentList @("stream", "https://youtu.be/jNQXAC9IVRw", "--no-progress") -RedirectStandardOutput ".\source-audio.bin" -RedirectStandardError ".\stream.log" -Wait -PassThru
if ($stream.ExitCode -ne 0) { throw "myyt failed with exit code $($stream.ExitCode)" }
```

Always check the producer exit code. A non-empty output after a non-zero exit may be
partial and must be discarded.

### Docker command equivalents

The image entry point is `myyt`:

```sh
docker run --rm myyt:1.0 info "https://youtu.be/M7lc1UVf-VE" --json
docker run --rm myyt:1.0 search "Coldplay Yellow" --limit 5 --json
docker run --rm myyt:1.0 formats "https://youtu.be/M7lc1UVf-VE" --json
docker run --rm myyt:1.0 bestaudio "https://youtu.be/M7lc1UVf-VE" --json
docker run --rm myyt:1.0 stream "https://youtu.be/jNQXAC9IVRw" --no-progress > source-audio.bin
```

Mount an output directory for complete downloads. Linux/macOS:

```sh
mkdir -p downloads
docker run --rm -v "$PWD/downloads:/downloads" myyt:1.0 download "https://youtu.be/jNQXAC9IVRw" -o /downloads
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force downloads | Out-Null
docker run --rm -v "${PWD}/downloads:/downloads" myyt:1.0 download "https://youtu.be/jNQXAC9IVRw" -o /downloads
```

On PowerShell older than 7.4, apply the same native-redirection warning to `docker
run ... stream`.

## 5. Expected output shapes and exit behavior

### `info --json`

```json
{
  "video_id": "M7lc1UVf-VE",
  "title": "...",
  "channel": "...",
  "channel_id": "...",
  "duration": 221,
  "thumbnail": "https://...",
  "webpage_url": "https://www.youtube.com/watch?v=M7lc1UVf-VE"
}
```

### `search --json`

```json
[
  {
    "video_id": "yKNxeF4KMsY",
    "title": "...",
    "channel": "...",
    "thumbnail": "https://...",
    "duration": 273,
    "webpage_url": "https://www.youtube.com/watch?v=yKNxeF4KMsY"
  }
]
```

### `formats --json` and `bestaudio --json`

```json
{
  "video": {"video_id": "M7lc1UVf-VE", "title": "..."},
  "player_client": "VISIONOS",
  "formats": [
    {
      "format_id": "140",
      "itag": 140,
      "mime_type": "audio/mp4",
      "audio_codec": "mp4a.40.2",
      "content_length": 3560000,
      "media_url": "https://...",
      "expires_at": 2000000000
    }
  ]
}
```

`bestaudio --json` uses the same video/client envelope with a single `format` object
instead of `formats`. Media URLs are temporary and must not be stored as identities.

### `download`

```text
stderr: Downloaded: 100.0% 2.4 MiB/2.4 MiB ...
stderr: Processing audio with FFmpeg...
stdout: /absolute/path/Example title.mp3
```

### `stream`

```text
stdout: raw binary source-media bytes, with no text framing
stderr: progress and diagnostics, or empty with --no-progress on success
```

Do not open stream output as text and do not parse it as JSON. Exit 0 is emitted only
after validated completion and output flush. Extraction/selection failures keep
stdout empty. A failure after partial transfer is non-zero and the partial bytes are
not a valid success artifact. A stream with no verifiable format or HTTP byte length
is refused. Downstream closure returns 130.

Important exit codes:

- 0: success
- 2: invalid URL/query/argument
- 3: YouTube network failure
- 4: video unavailable
- 5: extraction/format-response failure
- 6: no suitable format
- 7: media transfer or unsafe-resume failure
- 8: FFmpeg failure for `download`
- 130: keyboard cancellation or downstream stream closure

## 6. Unit tests

PowerShell, Linux, or macOS with the environment active:

```sh
pytest tests/unit
pytest -m "not integration"
```

Docker:

```sh
docker run --rm --entrypoint pytest myyt:1.0 tests/unit
docker run --rm --entrypoint pytest myyt:1.0 -m "not integration"
```

Unit tests use local fixtures and fake HTTP responses. The stream suite covers exact
binary output, channel isolation, bounded reads, retry/resume rules, URL refresh,
format changes, truncation, pipe closure, and response cleanup. Existing download
tests run in the same suite.

## 7. Live/integration tests

Live tests are opt-in because they contact public YouTube and media hosts.

Windows PowerShell:

```powershell
$env:MYYT_RUN_INTEGRATION = "1"
pytest -m integration
Remove-Item Env:MYYT_RUN_INTEGRATION
```

Linux/macOS:

```sh
MYYT_RUN_INTEGRATION=1 pytest -m integration
```

Docker:

```sh
docker run --rm -e MYYT_RUN_INTEGRATION=1 --entrypoint pytest myyt:1.0 -m integration
```

The live suite covers metadata, search continuation, format selection, range access,
complete source transfer, optional MP3 processing, complete short-content streaming,
and process-level binary redirection. Failures can reflect regional availability,
network policy, rate limits, or upstream changes.

## 8. Shell-level stream validation

Linux/macOS:

```sh
set -o pipefail
myyt stream "https://youtu.be/jNQXAC9IVRw" --no-progress > source-audio.bin
test -s source-audio.bin
echo $?
```

PowerShell 7.4+:

```powershell
myyt stream "https://youtu.be/jNQXAC9IVRw" --no-progress > .\source-audio.bin
if ($LASTEXITCODE -ne 0) { Remove-Item .\source-audio.bin; throw "stream failed" }
(Get-Item .\source-audio.bin).Length
```

For older Windows PowerShell, use the `Start-Process` binary-redirection recipe from
section 4 and inspect `$stream.ExitCode`.

## 9. Validating JSON output

PowerShell:

```powershell
$info = myyt info "https://youtu.be/M7lc1UVf-VE" --json | ConvertFrom-Json
$info.video_id
$results = myyt search "Coldplay Yellow" --limit 3 --json | ConvertFrom-Json
$results.Count
$audio = myyt bestaudio "https://youtu.be/M7lc1UVf-VE" --json | ConvertFrom-Json
$audio.format.itag
```

Linux/macOS with Python:

```sh
myyt info "https://youtu.be/M7lc1UVf-VE" --json | python -m json.tool
myyt formats "https://youtu.be/M7lc1UVf-VE" --json | python -m json.tool >/dev/null
myyt search "Coldplay Yellow" --limit 3 --json | python -m json.tool
```

With `jq`:

```sh
myyt search "Coldplay Yellow" --limit 3 --json | jq 'length'
myyt bestaudio "https://youtu.be/M7lc1UVf-VE" --json | jq -r '.format.itag'
```

Docker:

```sh
docker run --rm myyt:1.0 info "https://youtu.be/M7lc1UVf-VE" --json | python3 -m json.tool
```

JSON parsing failure means the command failed or stdout was contaminated. Inspect the
producer exit code and stderr separately.

## 10. Common errors and troubleshooting

### Python or launcher not found

Install Python 3.11+, reopen the shell, activate the intended environment, and
reinstall with `python -m pip install -e ".[dev]"`. If `myyt` is blocked or stale,
use `python -m myyt` and verify `myyt --version` reports 1.0.0.

### PowerShell stream output is corrupted or larger than expected

Check `$PSVersionTable.PSVersion`. Direct `>` and native pipelines are binary-safe for
the documented workflow on PowerShell 7.4+. With Windows PowerShell 5.1, use
`Start-Process -RedirectStandardOutput`; do not pass media bytes through its text
pipeline. Never use `Out-File`, `Set-Content`, or `Tee-Object` for media bytes.

### Stream produced some bytes but exited non-zero

Discard the partial output. This can mean exhausted network retries, unexpected EOF,
an ignored/mismatched resume range, a changed representation after URL refresh, or
another transfer error. Partial stdout is never promoted to success.

### Exit 130 or downstream consumer closed

The reading process closed the pipe, or the user cancelled. `myyt` stops without
retrying the write. This is expected when a consumer intentionally reads only a
prefix. If closure was unexpected, inspect the consumer and stderr logs.

### HTTP 403, 410, 429, timeout, or connection failure

- Confirm DNS and outbound HTTPS access.
- Avoid rapid retry storms; HTTP 429 indicates rate limiting.
- Extract immediately before transfer because signed media URLs expire.
- `stream` and `download` refresh once after 403/410; persistent rejection remains a
  visible failure.
- Check proxy, firewall, geography, and hosting-provider egress policy.

The project does not bypass access controls or attestation requirements.

### No directly usable audio format

Run `myyt formats URL --json` and inspect protocol, cipher, and transform flags. The
content may be manifest-only or current public player behavior may have changed.
Update fixtures and the appropriate extraction layer rather than silently invoking a
different downloader.

### FFmpeg missing or failed

This affects `download`, not `stream`. Install the FFmpeg executable on `PATH` and
run `ffmpeg -version`. Inspect the stderr detail, disk space, source support, and
output-directory permissions.

### Output directory or temporary-file errors

Pass a writable directory to `download -o`. Complete-file downloading needs space
for the source and MP3. `stream` does not use that directory or create a complete
media file.

### Docker cannot reach the network

If `docker build` cannot connect to the Docker API or named pipe, start Docker Desktop
or the Docker daemon first. A working `docker --version` client alone does not prove
that the daemon is running.

Configure daemon/Desktop proxy and DNS settings and ensure container bridge traffic
can reach outbound TCP 443.

## 11. VPS/Linux usage notes

- Run as an unprivileged service user in a dedicated virtual environment or container.
- Permit outbound DNS and TCP 443; no inbound port is required.
- FFmpeg is unnecessary for `stream` and required only for `download`.
- Keep stdout and stderr separate. For example:

  ```sh
  set -o pipefail
  myyt stream "$VIDEO_URL" 2>myyt-stream.log | consumer-command
  producer_status=${PIPESTATUS[0]}
  test "$producer_status" -eq 0
  ```

- Treat any non-zero producer exit as failure even if the consumer received bytes.
- Supervisors should forward SIGINT/SIGTERM and allow HTTP sockets to close.
- Apply an outer process timeout appropriate to media duration and network speed.
- Avoid concurrent retry storms after rate limiting.
- Do not cache signed media URLs; run extraction immediately before consuming bytes.
- Redirect binary stdout directly to a native pipe or file, never through a text
  logger. Capture stderr in a separate log.
- Rebuild the Docker image or reinstall the editable environment after version
  updates.
