from __future__ import annotations

import argparse
import copy
import os
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path


APP_NAME = "Noxlab Downloader"
VIDEO_FORMATS = ("mp4", "mkv", "webm")
AUDIO_FORMATS = ("mp3", "m4a", "wav", "flac", "opus")
RESOLUTIONS = ("best", "2160", "1440", "1080", "720", "480", "360", "240")
COOKIE_BROWSERS = ("none", "chrome", "edge", "firefox", "brave", "opera", "opera-gx", "vivaldi")
JS_RUNTIMES = ("auto", "none", "node", "deno")
ANSI = {
    "reset": "\033[0m",
    "dark_red": "\033[31m",
    "red": "\033[91m",
    "gray": "\033[37m",
    "dark_gray": "\033[90m",
    "green": "\033[92m",
}

NOXLAB_WORDMARK = (
    r" _   _  _____ __   __ _       ___   ______        ____                      _                 _           ",
    r"| \ | |/  _  \\ \ / /| |     / _ \  | ___ \      |  _ \  _____      ___ __ | | ___   __ _  __| | ___ _ __ ",
    r"|  \| || | | | \ V / | |    / /_\ \ | |_/ /      | | | |/ _ \ \ /\ / / '_ \| |/ _ \ / _` |/ _` |/ _ \ '__|",
    r"| . ` || | | | /   \ | |    |  _  | | ___ \      | |_| | (_) \ V  V /| | | | | (_) | (_| | (_| |  __/ |   ",
    r"| |\  |\ \_/ // /^\ \| |____| | | | | |_/ /      |____/ \___/ \_/\_/ |_| |_|_|\___/ \__,_|\__,_|\___|_|   ",
    r"\_| \_/ \___/ \/   \/\_____/\_| |_/ \____/                                                                ",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="noxdl",
        description="Download videos or audio by link from sites supported by yt-dlp.",
    )
    parser.add_argument("url", nargs="?", help="Video, reel, short, post, or playlist URL.")
    parser.add_argument(
        "-r",
        "--resolution",
        choices=RESOLUTIONS,
        default=None,
        help="Maximum video height. Use 'best' for the best available quality.",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=("video", "audio", "mute"),
        default=None,
        help="Download video with sound, audio only, or video without sound.",
    )
    parser.add_argument(
        "-f",
        "--format",
        default=None,
        help="Output format. Video: mp4, mkv, webm. Audio: mp3, m4a, wav, flac, opus.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="downloads",
        help="Output folder. Default: downloads",
    )
    parser.add_argument(
        "--cookies-browser",
        choices=COOKIE_BROWSERS,
        default="none",
        help="Use browser cookies for sites that require login, such as some Instagram links.",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="Proxy URL for region-blocked links, e.g. http://127.0.0.1:8080 or socks5://127.0.0.1:1080.",
    )
    parser.add_argument(
        "--js-runtime",
        choices=JS_RUNTIMES,
        default="auto",
        help="JavaScript runtime for yt-dlp extraction. Default: auto-detect Node or Deno.",
    )
    parser.add_argument(
        "--remote-components",
        default="ejs:github",
        help="Remote yt-dlp helper components to allow. Default: ejs:github.",
    )
    parser.add_argument(
        "--no-remote-components",
        action="store_true",
        help="Do not allow yt-dlp to fetch remote helper components.",
    )
    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="Show all formats yt-dlp sees for the URL, then exit.",
    )
    parser.add_argument(
        "--playlist",
        action="store_true",
        help="Allow playlist downloads. By default only the single given item is downloaded.",
    )
    parser.add_argument(
        "--update-engine",
        action="store_true",
        help="Upgrade yt-dlp before running.",
    )
    return parser


def detect_js_runtime(choice: str) -> str | None:
    if choice == "none":
        return None

    candidates = ("node", "deno") if choice == "auto" else (choice,)
    for runtime in candidates:
        path = shutil.which(runtime)
        if path:
            return f"{runtime}:{path}"
    return None


def detect_ffmpeg() -> str | None:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    try:
        import imageio_ffmpeg
    except ImportError:
        return None

    return imageio_ffmpeg.get_ffmpeg_exe()


def browser_cookie_source(browser: str) -> str:
    if browser == "opera-gx":
        opera_gx_profile = Path(os.environ.get("APPDATA", "")) / "Opera Software" / "Opera GX Stable"
        if opera_gx_profile.exists():
            return f"opera:{opera_gx_profile}"
        return "opera:Opera GX Stable"
    return browser


def yt_dlp_command() -> list[str]:
    return [sys.executable, "-m", "yt_dlp"]


def ensure_engine() -> None:
    result = subprocess.run(
        yt_dlp_command() + ["--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        print("yt-dlp is not installed yet.")
        print("Run setup.bat first, or run: python -m pip install -r requirements.txt")
        raise SystemExit(1)


def update_engine() -> None:
    print("Updating yt-dlp...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
        check=True,
    )


def color_text(text: str, color: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{ANSI[color]}{text}{ANSI['reset']}"


def enable_windows_virtual_terminal() -> None:
    if os.name != "nt" or not sys.stdout.isatty():
        return

    try:
        import ctypes
    except ImportError:
        return

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    mode = ctypes.c_uint32()
    if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        return
    kernel32.SetConsoleMode(handle, mode.value | 0x0004)


def configure_interactive_console() -> None:
    if os.name != "nt" or not sys.stdout.isatty():
        return

    enable_windows_virtual_terminal()
    try:
        subprocess.run(
            ["cmd", "/c", "mode con: cols=132 lines=42"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        pass


def clear_screen() -> None:
    if sys.stdout.isatty():
        print("\033[3J\033[2J\033[H", end="", flush=True)


def write_banner() -> None:
    clear_screen()
    rule = "  " + "=" * 116
    print()
    print(color_text(rule, "dark_red"))
    for line in NOXLAB_WORDMARK:
        print(color_text("  " + line, "red"))
    print(color_text(rule, "dark_red"))
    print(color_text("  [ NoxLab ]  Discord: noxian_  |  GitHub: noxian0", "gray"))
    print(color_text("  Paste a link to download from YouTube, Instagram, TikTok, X/Twitter, and more.", "gray"))
    if not detect_js_runtime("auto"):
        print(color_text("  Node.js was not found. Some YouTube videos may fail until Node.js LTS is installed.", "dark_gray"))
    print()


def read_input(prompt: str) -> str:
    try:
        return sanitize_text(input(prompt))
    except EOFError:
        return ""


def sanitize_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\xef\xbb\xbf", "")
    return "".join(char for char in text if unicodedata.category(char) != "Cf")


def choose(prompt: str, choices: tuple[str, ...], default: str) -> str:
    while True:
        print()
        for index, choice in enumerate(choices, start=1):
            suffix = " (default)" if choice == default else ""
            print(f"{index}. {choice}{suffix}")

        answer = read_input(f"{prompt}: ").strip().lower()
        if not answer:
            return default
        if answer in choices:
            return answer
        if answer.isdigit():
            selected = int(answer)
            if 1 <= selected <= len(choices):
                return choices[selected - 1]
        print("Please pick one of the listed options.")


def ask_yes_no(prompt: str, default: bool) -> bool:
    label = "Y/n" if default else "y/N"
    while True:
        answer = read_input(f"{prompt} [{label}]: ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def interactive_args(args: argparse.Namespace, allow_empty_exit: bool = False) -> argparse.Namespace | None:
    write_banner()

    if not args.url:
        prompt = "Paste the video/reel/post link"
        if allow_empty_exit:
            prompt += " (or press Enter to exit)"
        args.url = read_input(prompt + ": ").strip()
    if not args.url:
        if allow_empty_exit:
            return None
        print("No URL entered.")
        raise SystemExit(1)

    if args.mode is None:
        args.mode = choose(
            "What do you want to download",
            ("video", "audio", "mute"),
            "video",
        )

    if args.mode == "audio":
        if args.format is None:
            args.format = choose("Audio format", AUDIO_FORMATS, "mp3")
        args.resolution = "best"
    else:
        if args.resolution is None:
            args.resolution = choose("Maximum resolution", RESOLUTIONS, "1080")
        if args.format is None:
            args.format = choose("Video format", VIDEO_FORMATS, "mp4")

    if args.cookies_browser == "none":
        use_cookies = ask_yes_no("Use browser cookies for login-only/private links", False)
        if use_cookies:
            args.cookies_browser = choose("Browser", COOKIE_BROWSERS[1:], "edge")

    if args.proxy is None:
        proxy = read_input("Proxy URL for country/region blocks (optional, press Enter to skip): ").strip()
        args.proxy = proxy or None

    args.playlist = ask_yes_no("Download full playlist if the link is a playlist", args.playlist)
    return args


def interactive_session(base_args: argparse.Namespace) -> int:
    configure_interactive_console()
    last_result = 0

    while True:
        current_args = copy.copy(base_args)
        current_args.url = None

        current_args = interactive_args(current_args, allow_empty_exit=True)
        if current_args is None:
            return last_result

        validate_args(current_args)
        last_result = run_download(current_args, wait_for_enter=True)


def validate_args(args: argparse.Namespace) -> None:
    if args.url:
        args.url = sanitize_text(args.url).strip()

    if not args.url:
        print("Missing URL.")
        raise SystemExit(2)

    if args.mode is None:
        args.mode = "video"
    if args.resolution is None:
        args.resolution = "best" if args.mode == "audio" else "1080"
    if args.format is None:
        args.format = "mp3" if args.mode == "audio" else "mp4"

    valid_formats = AUDIO_FORMATS if args.mode == "audio" else VIDEO_FORMATS
    if args.format not in valid_formats:
        allowed = ", ".join(valid_formats)
        print(f"Invalid format '{args.format}' for {args.mode} mode. Allowed: {allowed}")
        raise SystemExit(2)


def video_selector(resolution: str, muted: bool, output_format: str) -> str:
    ext_filter = f"[ext={output_format}]" if output_format in {"mp4", "webm"} else ""

    if resolution == "best":
        height_filter = ""
    else:
        height_filter = f"[height<={resolution}]"

    if muted:
        return (
            f"bestvideo{height_filter}{ext_filter}/"
            f"bestvideo{height_filter}/"
            f"best{height_filter}"
        )

    if output_format == "mp4":
        return (
            f"bestvideo{height_filter}[ext=mp4]+bestaudio[ext=m4a]/"
            f"best{height_filter}[ext=mp4]/"
            "best[ext=mp4]"
        )

    return (
        f"bestvideo{height_filter}{ext_filter}+bestaudio/"
        f"bestvideo{height_filter}+bestaudio/"
        f"best{height_filter}/best"
    )


def build_download_command(args: argparse.Namespace) -> list[str]:
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title).180B [NOXLAB].%(ext)s")

    command = yt_dlp_command()

    ffmpeg_path = detect_ffmpeg()
    if ffmpeg_path:
        command += ["--ffmpeg-location", ffmpeg_path]

    js_runtime = detect_js_runtime(args.js_runtime)
    if js_runtime:
        command += ["--js-runtimes", js_runtime]
        if not args.no_remote_components and args.remote_components:
            command += ["--remote-components", args.remote_components]

    if args.cookies_browser != "none":
        command += ["--cookies-from-browser", browser_cookie_source(args.cookies_browser)]

    if args.proxy:
        command += ["--proxy", args.proxy]

    if args.list_formats:
        return command + ["--list-formats", args.url]

    if not args.playlist:
        command.append("--no-playlist")

    command += [
        "--progress",
        "--newline",
        "--windows-filenames",
        "-o",
        output_template,
    ]

    if args.mode == "audio":
        command += [
            "--extract-audio",
            "--audio-format",
            args.format,
            "--audio-quality",
            "0",
            "-f",
            "bestaudio/best",
        ]
    else:
        muted = args.mode == "mute"
        command += [
            "-f",
            video_selector(args.resolution, muted, args.format),
            "--merge-output-format",
            args.format,
        ]

    command.append(args.url)
    return command


def run_command(command: list[str]) -> int:
    print("\nRunning:")
    print(" ".join(f'"{part}"' if " " in part else part for part in command))
    print(flush=True)

    completed = subprocess.run(command)
    return completed.returncode


def snapshot_output_files(output_dir: Path) -> dict[Path, tuple[int, int]]:
    if not output_dir.exists():
        return {}
    return {
        path.resolve(): (path.stat().st_mtime_ns, path.stat().st_size)
        for path in output_dir.glob("*")
        if path.is_file()
    }


def changed_output_files(output_dir: Path, before: dict[Path, tuple[int, int]]) -> list[Path]:
    if not output_dir.exists():
        return []

    changed = []
    for path in output_dir.glob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        current_state = (path.stat().st_mtime_ns, path.stat().st_size)
        if before.get(resolved) != current_state:
            changed.append(resolved)
    return sorted(changed, key=lambda path: path.stat().st_mtime_ns, reverse=True)


def print_download_summary(result: int, output_dir: Path, files: list[Path]) -> None:
    print()
    if result == 0:
        print(color_text("Done.", "green"))
    else:
        print(color_text(f"Download failed. Exit code: {result}", "red"))
        print("Try updating the engine with: noxdl.bat --update-engine")
        print("If YouTube still fails, install Node.js LTS from https://nodejs.org/")
        print("For restricted/login-only links, retry with browser cookies enabled.")
        print("For country/region blocks, use a system-wide VPN or a proxy with --proxy.")
        print("If one resolution or format fails, try a lower resolution or MKV/WebM.")

    if files:
        print("Saved to:")
        for path in files:
            print(f"  {path}")
    else:
        print(f"Output folder: {output_dir.resolve()}")


def run_download(args: argparse.Namespace, wait_for_enter: bool = False) -> int:
    output_dir = Path(args.output)
    before = snapshot_output_files(output_dir) if not args.list_formats else {}
    command = build_download_command(args)
    result = run_command(command)

    if not args.list_formats:
        files = changed_output_files(output_dir, before)
        print_download_summary(result, output_dir, files)
        if wait_for_enter:
            read_input("\nPress Enter to download another one...")

    return result


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.update_engine:
        update_engine()
        if args.url is None and not args.list_formats:
            return 0

    ensure_engine()

    if args.url is None and not args.list_formats:
        return interactive_session(args)

    needs_menu = (
        args.url is None
        or args.mode is None
        or (args.mode != "audio" and args.resolution is None)
        or args.format is None
    )
    if needs_menu and not args.list_formats:
        configure_interactive_console()
        args = interactive_args(args)
        if args is None:
            return 0

    validate_args(args)
    return run_download(args)


if __name__ == "__main__":
    raise SystemExit(main())
