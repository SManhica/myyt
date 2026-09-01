# How to Run and Test

This guide covers `myyt` 0.4.1 on Windows PowerShell, Linux/macOS shells, Docker,
and Linux VPS hosts. Run commands from the repository root unless stated otherwise.

## 1. Environment setup

Requirements:

- Python 3.11 or newer; Python 3.12 is recommended.
- Internet access to `www.youtube.com`, `youtubei` endpoints, and Google media hosts
  for live commands and integration tests.
- Git is optional for running the source tree but useful for development.
- FFmpeg is required for `myyt download`; metadata, search, and format commands do
  not invoke it.
- Docker Engine or Docker Desktop is required only for the Docker workflow.

The runtime uses only Python's standard library. `pytest` is installed by the
development extra for tests.

### Windows PowerShell

Check the launcher and Python version:

```powershell
py --version
py -3.12 --version
```

If `py` is unavailable, install Python from python.org and enable the installer's
launcher/PATH options. A Microsoft Store `python.exe` alias can otherwise point to a
non-installed placeholder.

Install FFmpeg with a trusted Windows package or archive, add its `bin` directory to
`PATH`, reopen PowerShell, and verify:

```powershell
winget search ffmpeg
ffmpeg -version
```

`winget search` shows currently available package IDs; install the package you trust
with `winget install --id PACKAGE_ID_FROM_SEARCH -e`. Keeping the package ID discovered locally
avoids relying on a stale ID in this guide.

### Linux/macOS shell

```sh
python3 --version
```

On Debian/Ubuntu, the virtual-environment package may be separate:

```sh
sudo apt-get update
sudo apt-get install -y python3 python3-venv
```

On macOS, a current Python can be installed with python.org packages or Homebrew.

Install and verify FFmpeg on Debian/Ubuntu:

```sh
sudo apt-get update
sudo apt-get install -y ffmpeg
ffmpeg -version
```

On macOS with Homebrew:

```sh
brew install ffmpeg
ffmpeg -version
```

### Docker

```sh
docker --version
docker build -t myyt:0.4 .
```

The supplied `Dockerfile` creates `/opt/myyt-venv`, adds it to `PATH`, installs the
project plus test dependencies and FFmpeg, and runs as a non-root user. No host
Python, virtual environment, or FFmpeg install is required.

## 2. Virtual environment creation and activation

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

If PowerShell blocks activation, allow locally created scripts for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Alternatively, do not activate and invoke `.\.venv\Scripts\python.exe` and
`.\.venv\Scripts\myyt.exe` explicitly.

Deactivate with:

```powershell
deactivate
```

### Linux/macOS shell

```sh
python3 -m venv .venv
source .venv/bin/activate
python --version
```

Deactivate with:

```sh
deactivate
```

### Docker

Docker provides process isolation and the image contains a dedicated virtual
environment. It is activated automatically through `PATH`. For an interactive shell:

```sh
docker run --rm -it --entrypoint /bin/sh myyt:0.4
which python
which myyt
which ffmpeg
```

Inside that shell, explicit activation is also possible:

```sh
. /opt/myyt-venv/bin/activate
```

## 3. Project installation

With the PowerShell or POSIX virtual environment active:

```sh
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
myyt --version
```

Expected version:

```text
myyt 0.4.1
```

For runtime-only installation, omit the development extra:

```sh
python -m pip install -e .
```

Docker installation happens during `docker build -t myyt:0.4 .`.

## 4. Running commands through v0.4

All examples target normal public YouTube content. Shell quoting prevents `&` and
other URL characters from being interpreted by the shell.

### `myyt info URL`

Human-readable examples:

```sh
myyt info "https://www.youtube.com/watch?v=M7lc1UVf-VE"
myyt info "https://youtu.be/dQw4w9WgXcQ"
myyt info "https://www.youtube.com/watch?v=jNQXAC9IVRw"
```

JSON examples:

```sh
myyt info "https://youtu.be/M7lc1UVf-VE" --json
myyt info "https://www.youtube.com/watch?v=yKNxeF4KMsY" --json
```

### `myyt search QUERY`

```sh
myyt search "Coldplay Yellow"
myyt search "Python networking tutorial" --limit 5
myyt search "Mozambique music" --limit 25 --json
```

The limit must be between 1 and 100. Requests beyond the initial page use bounded
first-party continuation calls.

### `myyt formats URL`

```sh
myyt formats "https://www.youtube.com/watch?v=M7lc1UVf-VE"
myyt formats "https://youtu.be/yKNxeF4KMsY" --json
myyt formats "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --json
```

Human output is a compact table. JSON output includes normalized formats and their
expiring media URLs.

### `myyt bestaudio URL`

```sh
myyt bestaudio "https://www.youtube.com/watch?v=M7lc1UVf-VE"
myyt bestaudio "https://youtu.be/yKNxeF4KMsY" --json
myyt bestaudio "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --json
```

The selector prefers audio-only, supported codecs, reported quality/bitrate, direct
HTTP transport, sample rate, and known length. It does not make network requests.

### `myyt download URL`

FFmpeg must be available on `PATH`. The `-o/--output` value is a directory, created
when necessary. Existing files are not overwritten; a repeated title becomes
`Title (1).mp3`, then `Title (2).mp3`.

```sh
myyt download "https://www.youtube.com/watch?v=jNQXAC9IVRw"
myyt download "https://youtu.be/M7lc1UVf-VE" -o ./downloads
myyt download "https://www.youtube.com/watch?v=yKNxeF4KMsY" -o ./music --audio-format mp3 --no-progress
```

The default command reports transfer and FFmpeg status to stderr. `--no-progress`
suppresses those status lines. On success, stdout contains only the absolute MP3 path.

### Docker command equivalents

The image entry point is `myyt`, so omit the executable name after the image:

```sh
docker run --rm myyt:0.4 info "https://youtu.be/M7lc1UVf-VE"
docker run --rm myyt:0.4 search "Coldplay Yellow" --limit 5 --json
docker run --rm myyt:0.4 formats "https://youtu.be/yKNxeF4KMsY" --json
docker run --rm myyt:0.4 bestaudio "https://youtu.be/yKNxeF4KMsY" --json
```

Downloads need a bind-mounted host directory. Linux/macOS:

```sh
mkdir -p downloads
docker run --rm -v "$PWD/downloads:/downloads" myyt:0.4 download "https://youtu.be/jNQXAC9IVRw" -o /downloads
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force downloads | Out-Null
docker run --rm -v "${PWD}/downloads:/downloads" myyt:0.4 download "https://youtu.be/jNQXAC9IVRw" -o /downloads
```

Without a bind mount, the MP3 remains in the disposable container and is lost when
`--rm` removes it.

## 5. Expected output shapes

Human output is intended for terminals. JSON schemas are intended for Node.js and
other processes. JSON stdout contains no diagnostics; errors go to stderr.

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

The top level is an array. Duration is normalized seconds; optional fields can be
`null`.

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

### `formats --json`

```json
{
  "video": {"video_id": "M7lc1UVf-VE", "title": "..."},
  "player_client": "VISIONOS",
  "dash_manifest_url": null,
  "hls_manifest_url": null,
  "formats": [
    {
      "format_id": "140",
      "itag": 140,
      "mime_type": "audio/mp4",
      "container": "m4a",
      "codecs": ["mp4a.40.2"],
      "audio_codec": "mp4a.40.2",
      "video_codec": null,
      "bitrate": 131585,
      "sample_rate": 44100,
      "channels": 2,
      "content_length": 3560000,
      "has_audio": true,
      "has_video": false,
      "media_url": "https://...expiring URL...",
      "protocol": "https",
      "adaptive": true,
      "fragmented": true,
      "is_ciphered": false,
      "requires_n_transform": false,
      "expires_at": 2000000000
    }
  ]
}
```

The actual format object also contains average bitrate, dimensions, FPS, quality
labels, and audio quality. `content_length` is bytes and `expires_at` is a Unix epoch.

### `bestaudio --json`

```json
{
  "video": {"video_id": "M7lc1UVf-VE", "title": "..."},
  "player_client": "VISIONOS",
  "format": {"itag": 251, "audio_codec": "opus", "media_url": "https://..."}
}
```

Media URLs are temporary. Do not store them as permanent application identifiers.

### `download`

When stderr is a terminal, progress updates reuse one line, followed by the FFmpeg
status. Exact sizes, speed, title, and path vary:

```text
stderr: Downloaded: 100.0% 2.4 MiB/2.4 MiB 1.1 MiB/s ETA 00:00
stderr: Processing audio with FFmpeg...
stdout: D:\Projectos\myyt\Example title.mp3
```

On Linux/macOS, the last line is an absolute POSIX path such as
`/home/user/myyt/downloads/Example title.mp3`. There is no `download --json` in v0.4;
the stable machine-readable JSON contracts remain on `info`, `search`, `formats`, and
`bestaudio`. A successful download exits 0. Transfer failures exit 7, FFmpeg failures
exit 8, and keyboard cancellation exits 130.

## 6. Unit tests

PowerShell, Linux, and macOS with the environment active:

```sh
pytest tests/unit
pytest -m "not integration"
```

Docker:

```sh
docker run --rm --entrypoint pytest myyt:0.4 tests/unit
docker run --rm --entrypoint pytest myyt:0.4 -m "not integration"
```

Unit tests use local fixtures and should not access YouTube.

## 7. Live/integration tests

Live tests make public YouTube and media-host requests. They can fail because of
network policy, regional availability, rate limiting, or upstream changes.

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
docker run --rm -e MYYT_RUN_INTEGRATION=1 --entrypoint pytest myyt:0.4 -m integration
```

The v0.4 integration suite checks metadata, search continuation, multiple video
categories, best-audio selection, a 1 KiB range request, a complete selected-source
download, and an end-to-end MP3 conversion. The MP3 test skips when FFmpeg is absent.
Live failures can also reflect regional availability, rate limiting, or a blocked
network rather than deterministic test regressions.

## 8. Validating JSON output

### Windows PowerShell

```powershell
$result = myyt search "Coldplay Yellow" --limit 3 --json | ConvertFrom-Json
$result.Count
$result[0].video_id

$audio = myyt bestaudio "https://youtu.be/M7lc1UVf-VE" --json | ConvertFrom-Json
$audio.format.media_url
```

`ConvertFrom-Json` failing means stdout was not valid JSON or the command failed.
Inspect `$LASTEXITCODE` and rerun without a pipeline to see stderr.

### Linux/macOS

With Python only:

```sh
myyt info "https://youtu.be/M7lc1UVf-VE" --json | python -m json.tool
myyt formats "https://youtu.be/M7lc1UVf-VE" --json | python -m json.tool >/dev/null
echo $?
```

With `jq` installed:

```sh
myyt search "Coldplay Yellow" --limit 3 --json | jq 'length'
myyt bestaudio "https://youtu.be/M7lc1UVf-VE" --json | jq -r '.format.media_url'
```

### Docker

```sh
docker run --rm myyt:0.4 info "https://youtu.be/M7lc1UVf-VE" --json \
  | python3 -m json.tool
```

## 9. Common errors and troubleshooting

### `python`, `python3`, or `py` not found

Install Python 3.11+ and reopen the shell. On Windows, try `py` even when `python`
is not on PATH. On Linux, install both Python and the distribution's `venv` package.

### PowerShell cannot run `Activate.ps1`

Use `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or invoke executables under
`.\.venv\Scripts` directly without activation.

### `myyt` reports an old version

Ensure the intended virtual environment is active, then reinstall:

```sh
python -m pip install -e ".[dev]"
myyt --version
```

If Windows Application Control blocks the generated `myyt.exe` launcher, use the
equivalent module entry point and recreate/install the environment from a normal
non-administrator PowerShell session when policy permits:

```powershell
python -m myyt --version
python -m myyt download "https://youtu.be/M7lc1UVf-VE" -o ./downloads
```

### HTTP 403, 429, timeouts, or connection failures

- Confirm outbound HTTPS and DNS access.
- Avoid rapid repeated live runs; 429 indicates rate limiting.
- Check corporate/VPS proxy and firewall policy.
- Retry later for transient failures.
- Do not attempt CAPTCHA or access-control bypasses.

### `player client configuration required for formats`

YouTube returned a page variant without the public client configuration expected by
v0.4. Run the unit suite, capture only non-sensitive debug structure, and update the
fixture/parser rather than falling back to another downloader.

### `no player client returned a directly usable audio URL`

The public WEB/VISIONOS response behavior may have changed, or the content may not
be normally public in the current region. Check `docs/YOUTUBE_INTERNALS.md` and update
client profiles/fixtures after confirming the response shape.

### `no directly usable audio format is available`

Available URLs may be encrypted, require an unimplemented `n` transform, or use only
an unsupported manifest transport. `formats --json` exposes these states explicitly.

### A saved media URL returns 403

Media URLs expire. `download` automatically re-extracts once after media HTTP 403 or
410. For a URL obtained from `bestaudio` or `formats`, extract it again immediately
before your own transfer. Persistent rejection can indicate rate limiting, geography,
or access controls and is not bypassed.

If `myyt --version` reports 0.4.0, upgrade to 0.4.1. YouTube now applies GVS
Proof-of-Origin token requirements to direct media from some public player clients.
V0.4.1 avoids treating those Android/iOS URLs as downloadable and uses a current
non-token-required public client profile. Persistent 403 responses can mean YouTube
changed that policy again; run the live format/download tests and update the player
profiles rather than reducing the request to tiny byte probes.

### `FFmpeg was not found on PATH`

Install FFmpeg using the platform steps in section 1, reopen the shell, and run
`ffmpeg -version`. If that succeeds but `myyt` still fails, confirm both commands run
from the same shell, service account, or container. A Python package named `ffmpeg`
does not install the required executable.

### `FFmpeg failed with exit code ...`

The stderr detail printed by `myyt` comes from FFmpeg. Check free disk space, source
format support, and write permission on the output directory. The temporary source
and incomplete MP3 are removed automatically; rerun with `formats --json` to inspect
the selected formats if the problem is reproducible.

### Output directory or temporary-file errors

Pass a writable directory to `-o`. V0.4 places temporary files inside that directory,
so the filesystem needs space for both the downloaded source and encoded MP3. It does
not overwrite an existing MP3 and cleans the per-operation `.myyt-*` directory after
normal completion, error, or cancellation.

### Pytest cache warning

A read-only workspace can prevent `.pytest_cache` updates without failing tests. Use:

```sh
pytest -p no:cacheprovider
```

### Docker build or live commands cannot reach the network

Configure Docker Desktop/daemon proxy and DNS settings. On restrictive VPS hosts,
ensure container bridge traffic can reach HTTPS destinations.

## 10. VPS/Linux notes

- Run `myyt` as an unprivileged service user inside a dedicated virtual environment.
- Install FFmpeg for that service user and verify `sudo -u <user> ffmpeg -version`, or
  use the Docker image where FFmpeg is included.
- Keep the checkout and virtual environment separate from web-server writable paths.
- Permit outbound TCP 443 and working DNS; no inbound port is required by `myyt`.
- Media URLs are short-lived. Extract immediately before the consuming process starts.
- JSON is stdout-only and diagnostics are stderr-only, so capture them separately:

  ```sh
  myyt bestaudio "$VIDEO_URL" --json >result.json 2>myyt-error.log
  ```

- Use process timeouts and inspect non-zero exit codes from Node.js or systemd.
- Do not run concurrent retry storms after 429 responses.
- Budget destination space for the source representation plus MP3. Temporary files
  live inside `-o`, which avoids cross-filesystem final moves.
- V0.4 downloads and converts complete files but does not provide the v1.0 binary
  `stream` contract. Do not pipe `myyt download` stdout into FFmpeg; stdout is a path.
- Rebuild Docker images or reinstall editable environments after each version update.
