# NoxLab Downloader

![Main Menu](img/noxlabdl-v1-1.png)

NoxLab Downloader is a Windows app and command prompt tool for downloading
video or audio from links supported by `yt-dlp`, including YouTube, Instagram,
TikTok, X/Twitter, SoundCloud, and many other sites.

Downloads are saved in the `downloads` folder and are marked with `[NOXLAB-DOWNLOADER]`
in the filename.

## Important

Use this tool only for content you own, have permission to download, or are
legally allowed to save. The author is not responsible for piracy, copyright
violations or any other misuse.
You use this tool at your own risk.

This project uses third-party software that is not owned by NoxLab:

- `Python`: runs the app and command-line downloader; setup can install the
  official Windows distribution for you.
- `Node.js`: runs yt-dlp's JavaScript helper for YouTube; the app can download
  and open its official LTS installer.
- `yt-dlp`: the downloader engine. It reads the link, talks to the supported
  website, finds available media formats, and downloads the selected media.
- `curl-cffi`: a networking library used by yt-dlp to make supported
  browser-like requests. TikTok may require this for its anti-bot checks.
- `FFmpeg`: setup downloads a portable full FFmpeg Essentials build containing
  `ffmpeg.exe` and `ffprobe.exe`. They merge video and audio streams, inspect
  media files, convert audio formats, and help create playable MP4 files.

See [LICENSE](LICENSE) for the NoxLab Downloader license and third-party
notices.

## Setup

Extract the ZIP into a folder you can write to, then double-click:

```bat
setup.bat
```

Python is required, but you do not need to download it yourself. If setup
cannot find Python 3.10 or newer with Tkinter, it asks **Install Python from
python.org now? [Y/n]**. Press Enter or type `y` to install Python 3.14.10 for
your Windows account and continue setup automatically. Type `n` to cancel.
The automatic installer supports 64-bit Windows (x64 and ARM64).

An internet connection is required. Setup downloads the official Python
installer, checks its publisher signature, and installs Python, pip and
Tkinter. It adds Python to your user PATH. Existing supported installations
are reused. You do not need Visual Studio Code.

Manual installation remains available from [python.org](https://www.python.org/downloads/windows/).
Include **pip**, **Tcl/Tk and IDLE**, and **Add python.exe to PATH**, then run
`setup.bat` again.

`setup.bat` does this on your PC:

1. Offers to install Python if a suitable installation is missing.
2. Creates a local `.venv` Python environment inside the project folder.
3. Installs the required Python packages into that local environment.
4. Downloads a portable FFmpeg Essentials build into `tools\ffmpeg`. This
   includes `ffmpeg.exe` and `ffprobe.exe`, which are needed for sound,
   merging video/audio streams, and audio-only conversions.
5. Creates a `downloads` folder.
6. Creates a `NoxLab Downloader` shortcut on your desktop and in the project folder.

The setup installs these Python packages:

- `yt-dlp`, including its `curl-cffi` browser-impersonation support

It also downloads the FFmpeg Essentials toolset from `gyan.dev` during setup.
This is normally an approximately 80 MB one-time download. It does not install
videos, change your browser, add FFmpeg to your system PATH, or upload your
files anywhere. The Python environment and FFmpeg tools are kept inside the
project folder. Python itself is installed for your Windows account if you
accept the installation option.

## Node.js For YouTube

**Node.js LTS is recommended for YouTube videos**, especially when a YouTube
download fails. It runs the JavaScript helper used by yt-dlp for YouTube.

1. Open NoxLab Downloader and click **Install Node.js LTS**.
2. Wait for the official installer to download from [nodejs.org](https://nodejs.org/).
3. Complete the Node.js setup window. Keep **Add to PATH** enabled and approve
   the Windows administrator prompt if it appears. Extra build tools are not
   needed for this downloader.
4. Return to the app and retry the download once it reports Node.js is ready.

The button chooses the latest LTS installer for your PC and checks its publisher
signature before opening it. It can also be used to update an existing Node.js
installation. Node.js is installed as a normal Windows program, outside the
project folder; it can be removed through Windows Settings > Apps.
Cancel the native installer to stop installation. If it requests a Windows
restart, restart before retrying. If Node.js is still not detected after an
otherwise successful install, close and reopen the app.

**Update Engine** updates yt-dlp and its Python dependencies; use the separate
**Install Node.js LTS** button to install or update Node.js.

## Start The Tool

Recommended start method:

```text
NoxLab Downloader
```

Use the shortcut created on your desktop or inside the project folder.

You can also double-click the windowed launcher:

```bat
NOXLAB_DOWNLOADER.pyw
```

Command prompt mode is still available:

```bat
noxdl.bat
```


## Options

When using the app or command prompt mode, you can choose:

- video with sound
- audio only
- muted video
- resolution
- output format
- whether to use browser cookies for login-only links
- whether to download a full playlist
- an optional proxy for country/region-blocked links

For MP4 video downloads, the tool prefers M4A/AAC audio so the result plays
properly in Windows' built-in video players.

If an older copy of the downloader says that `ffprobe.exe` is missing, run
`setup.bat` again. The new setup installs the full FFmpeg toolset required for
audio downloads and video/audio merging.

For TikTok errors mentioning `impersonation` or an unexpected webpage response,
click **Update Engine** in the app. It updates yt-dlp and installs its supported
browser-request component (`curl-cffi`).

## If A Download Fails

1. Click **Update Engine**, wait for completion, then retry.
2. For YouTube, click **Install Node.js LTS**, complete the installer, and retry.
3. If it still fails with **Access denied** or another file-permission error,
   close the app, right-click the **NoxLab Downloader** shortcut and choose
   **Run as administrator** (on Windows 11, look under **Show more options**).
   Alternatively, move the project into a folder you own and run setup again.

Administrator mode helps with Windows permissions; it does not fix unavailable
videos, website restrictions, or missing login cookies. Read the actual error
in the app output. For login-only videos, use the Cookies selector. Try a lower
resolution or another format if the requested format is unavailable.

## Direct Commands

Download a 1080p MP4 video with sound:

```bat
noxdl.bat "https://www.youtube.com/watch?v=VIDEO_ID" --resolution 1080 --mode video --format mp4
```

Download audio only as MP3:

```bat
noxdl.bat "https://www.youtube.com/watch?v=VIDEO_ID" --mode audio --format mp3
```

Download a muted 720p MP4:

```bat
noxdl.bat "https://www.youtube.com/watch?v=VIDEO_ID" --resolution 720 --mode mute --format mp4
```

Use browser cookies, useful for some private or login-only links:

```bat
noxdl.bat "https://www.instagram.com/reel/SHORTCODE/" --cookies-browser edge
```

Opera GX cookies can be used with:

```bat
noxdl.bat "https://soundcloud.com/example/track" --cookies-browser opera-gx
```

Opera GX VPN only affects traffic inside Opera GX. It does not automatically
route Python, yt-dlp, or FFmpeg through the browser VPN. If a song/video is
country blocked, use a system-wide VPN or a proxy that affects all apps.

If you have a proxy URL, you can pass it directly:

```bat
noxdl.bat "https://soundcloud.com/example/track" --proxy "http://127.0.0.1:8080"
```

## Proxy Box

The proxy box is optional. Leave it empty if you do not have a proxy.

A proxy tells yt-dlp to send the download request through another server. This
can help when a song/video is blocked in your country, but only if the proxy is
in a country where the content is available.

Examples:

```text
http://127.0.0.1:8080
socks5://127.0.0.1:1080
http://username:password@proxy.example.com:8080
```

Use the proxy box when:

- a link is country/region blocked
- your VPN app gives you a local proxy address
- you have a system/proxy service that works outside the browser

Do not put a normal website link in the proxy box. The normal video/song link
goes in the Link box. The proxy box only accepts proxy server addresses.

Opera GX VPN only works inside Opera GX. It does not automatically affect
NoxLab Downloader, Python, yt-dlp, or FFmpeg. For region blocks, use a
system-wide VPN or a proxy URL.

Show every format available for a link:

```bat
noxdl.bat "https://www.youtube.com/watch?v=VIDEO_ID" --list-formats
```

Update the downloader engine:

```bat
noxdl.bat --update-engine
```

## What It Does On Your PC

NoxLab Downloader runs locally on your PC. During normal use it can:

- create a `downloads` folder
- save downloaded video/audio files into that folder
- create a local `.venv` folder during setup
- download and install Python for your Windows account when you accept setup's
  Python installation prompt
- download and launch the official Node.js LTS installer when you click
  **Install Node.js LTS**; the installer may change your system PATH and request
  Windows administrator permission
- download and store `ffmpeg.exe` and `ffprobe.exe` inside `tools\ffmpeg`
  during setup
- create desktop and folder shortcuts during setup
- run `yt-dlp` through Python
- use yt-dlp's `curl-cffi` component for supported browser-like requests when
  a site such as TikTok requires it
- run the bundled portable FFmpeg tools for media inspection, audio conversion,
  and merging video with sound
- contact the website from the link you paste
- optionally read browser cookies if you choose `--cookies-browser` or select
  cookies in the menu
- read Opera GX cookies from your Opera GX profile when `opera-gx` is selected
- use a proxy if you provide one with `--proxy` or enter one in the menu
- allow yt-dlp to fetch its recommended YouTube JavaScript helper from GitHub
  when a JavaScript runtime is available

Browser cookies are only used if you choose that option.

## License

NoxLab Downloader is free to use, but it may not be sold, included in paid
software, included in freemium software, or reuploaded/modified without the
author's permission. See [LICENSE](LICENSE).
