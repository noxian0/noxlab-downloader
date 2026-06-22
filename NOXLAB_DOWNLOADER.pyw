"""Windowed launcher for NoxLab Downloader."""

from __future__ import annotations

import copy
import os
from pathlib import Path
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import downloader


APP_TITLE = "NoxLab Downloader"
ASCII_TITLE = r"""
 _   _  _____ __   __ _       ___   ______        ____                      _                 _
| \ | |/  _  \\ \ / /| |     / _ \  | ___ \      |  _ \  _____      ___ __ | | ___   __ _  __| | ___ _ __
|  \| || | | | \ V / | |    / /_\ \ | |_/ /      | | | |/ _ \ \ /\ / / '_ \| |/ _ \ / _` |/ _` |/ _ \ '__|
| . ` || | | | /   \ | |    |  _  | | ___ \      | |_| | (_) \ V  V /| | | | | (_) | (_| | (_| |  __/ |
| |\  |\ \_/ // /^\ \| |____| | | | | |_/ /      |____/ \___/ \_/\_/ |_| |_|_|\___/ \__,_|\__,_|\___|_|
\_| \_/ \___/ \/   \/\_____/\_| |_/ \____/
""".strip("\n")


class DownloaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(980, 660)
        self.configure(bg="#121212")
        self.process: subprocess.Popen[str] | None = None

        icon_path = Path(__file__).with_name("assets") / "noxlab_downloader.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except tk.TclError:
                pass

        self._build_style()
        self._build_ui()
        self._update_format_choices()
        self._node_warning()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Root.TFrame", background="#121212")
        style.configure("Panel.TFrame", background="#1d1d1d", borderwidth=1, relief="solid")
        style.configure("TLabel", background="#121212", foreground="#e7e7e7")
        style.configure("Panel.TLabel", background="#1d1d1d", foreground="#e7e7e7")
        style.configure("Muted.TLabel", background="#121212", foreground="#9b9b9b")
        style.configure("Accent.TLabel", background="#121212", foreground="#ff4b4b")
        style.configure("TButton", padding=(12, 7), background="#2b2b2b", foreground="#f2f2f2")
        style.map("TButton", background=[("active", "#3a3a3a")])
        style.configure("Danger.TButton", padding=(12, 7), background="#772727", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#9b3030")])
        style.configure("TCheckbutton", background="#1d1d1d", foreground="#e7e7e7")
        style.configure("TCombobox", fieldbackground="#252525", background="#252525", foreground="#f2f2f2")
        style.configure("TEntry", fieldbackground="#252525", foreground="#f2f2f2")

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="Root.TFrame", padding=16)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="Root.TFrame")
        header.pack(fill="x")
        title = tk.Label(
            header,
            text=ASCII_TITLE,
            bg="#121212",
            fg="#ff3535",
            justify="left",
            font=("Consolas", 10, "bold"),
        )
        title.pack(anchor="w")
        ttk.Label(header, text="[ NoxLab ]  Discord: noxian_  |  GitHub: noxian0", style="Muted.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(header, text="Download video or audio from supported links.", style="Muted.TLabel").pack(anchor="w", pady=(0, 12))

        form = ttk.Frame(root, style="Panel.TFrame", padding=14)
        form.pack(fill="x", pady=(0, 12))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        self.url_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="video")
        self.resolution_var = tk.StringVar(value="1080")
        self.format_var = tk.StringVar(value="mp4")
        self.cookies_var = tk.StringVar(value="none")
        self.proxy_var = tk.StringVar()
        self.playlist_var = tk.BooleanVar(value=False)

        ttk.Label(form, text="Link", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(form, textvariable=self.url_var).grid(row=0, column=1, columnspan=3, sticky="ew", pady=6)

        ttk.Label(form, text="Mode", style="Panel.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
        self.mode_box = ttk.Combobox(form, textvariable=self.mode_var, values=("video", "audio", "mute"), state="readonly", width=14)
        self.mode_box.grid(row=1, column=1, sticky="w", pady=6)
        self.mode_box.bind("<<ComboboxSelected>>", lambda _event: self._update_format_choices())

        ttk.Label(form, text="Resolution", style="Panel.TLabel").grid(row=1, column=2, sticky="w", padx=(20, 8), pady=6)
        ttk.Combobox(form, textvariable=self.resolution_var, values=downloader.RESOLUTIONS, state="readonly", width=14).grid(row=1, column=3, sticky="w", pady=6)

        ttk.Label(form, text="Format", style="Panel.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=6)
        self.format_box = ttk.Combobox(form, textvariable=self.format_var, state="readonly", width=14)
        self.format_box.grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(form, text="Cookies", style="Panel.TLabel").grid(row=2, column=2, sticky="w", padx=(20, 8), pady=6)
        ttk.Combobox(form, textvariable=self.cookies_var, values=downloader.COOKIE_BROWSERS, state="readonly", width=14).grid(row=2, column=3, sticky="w", pady=6)

        ttk.Label(form, text="Proxy", style="Panel.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(form, textvariable=self.proxy_var).grid(row=3, column=1, columnspan=2, sticky="ew", pady=6)
        ttk.Checkbutton(form, text="Download playlist", variable=self.playlist_var).grid(row=3, column=3, sticky="w", pady=6)

        actions = ttk.Frame(root, style="Root.TFrame")
        actions.pack(fill="x", pady=(0, 12))
        self.download_button = ttk.Button(actions, text="Start Download", command=self.start_download)
        self.download_button.pack(side="left")
        self.update_button = ttk.Button(actions, text="Update Engine", command=self.update_engine)
        self.update_button.pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Open Downloads", command=self.open_downloads).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Clear Output", command=self.clear_output).pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(actions, text="Stop", style="Danger.TButton", command=self.stop_download, state="disabled")
        self.stop_button.pack(side="right")

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(root, textvariable=self.status_var, style="Accent.TLabel").pack(anchor="w", pady=(0, 8))

        self.output = tk.Text(
            root,
            bg="#0d0d0d",
            fg="#e8e8e8",
            insertbackground="#ffffff",
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
        )
        self.output.pack(fill="both", expand=True)
        self.output.tag_configure("ok", foreground="#5dff89")
        self.output.tag_configure("error", foreground="#ff5d5d")
        self.output.tag_configure("muted", foreground="#a8a8a8")

    def _update_format_choices(self) -> None:
        if self.mode_var.get() == "audio":
            values = downloader.AUDIO_FORMATS
            default = "mp3"
        else:
            values = downloader.VIDEO_FORMATS
            default = "mp4"
        self.format_box.configure(values=values)
        if self.format_var.get() not in values:
            self.format_var.set(default)

    def _node_warning(self) -> None:
        if not downloader.detect_js_runtime("auto"):
            self.log("Node.js was not found. Some YouTube videos may fail until Node.js LTS is installed.", "muted")

    def log(self, text: str, tag: str | None = None) -> None:
        self.output.insert("end", text + "\n", tag)
        self.output.see("end")

    def clear_output(self) -> None:
        self.output.delete("1.0", "end")

    def open_downloads(self) -> None:
        folder = Path("downloads").resolve()
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def current_args(self) -> object:
        args = copy.copy(downloader.build_parser().parse_args([]))
        args.url = self.url_var.get().strip()
        args.mode = self.mode_var.get()
        args.resolution = "best" if args.mode == "audio" else self.resolution_var.get()
        args.format = self.format_var.get()
        args.cookies_browser = self.cookies_var.get()
        args.proxy = self.proxy_var.get().strip() or None
        args.playlist = self.playlist_var.get()
        return args

    def set_running(self, running: bool) -> None:
        self.download_button.configure(state="disabled" if running else "normal")
        self.update_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")

    def start_download(self) -> None:
        if self.process is not None:
            return
        args = self.current_args()
        if not args.url:
            messagebox.showwarning(APP_TITLE, "Paste a link first.")
            return
        try:
            downloader.validate_args(args)
        except SystemExit:
            messagebox.showerror(APP_TITLE, "Invalid download options.")
            return

        thread = threading.Thread(target=self._run_download, args=(args,), daemon=True)
        thread.start()

    def update_engine(self) -> None:
        if self.process is not None:
            return
        thread = threading.Thread(target=self._run_update_engine, daemon=True)
        thread.start()

    def stop_download(self) -> None:
        if self.process is not None:
            self.process.terminate()

    def _run_update_engine(self) -> None:
        command = [downloader.yt_dlp_command()[0], "-m", "pip", "install", "--upgrade", "yt-dlp"]
        self.after(0, lambda: self._start_process_ui("Updating yt-dlp..."))
        result = self._run_process(command)
        self.after(0, lambda: self._finish_process_ui("Update complete." if result == 0 else f"Update failed. Exit code: {result}", result == 0))

    def _run_download(self, args: object) -> None:
        output_dir = Path(args.output)
        before = downloader.snapshot_output_files(output_dir)
        command = downloader.build_download_command(args)
        self.after(0, lambda: self._start_process_ui("Downloading..."))
        self.after(0, lambda: self.log("Running: " + " ".join(f'"{part}"' if " " in part else part for part in command), "muted"))
        result = self._run_process(command)
        files = downloader.changed_output_files(output_dir, before)

        def done() -> None:
            if result == 0:
                self.log("Done.", "ok")
                if files:
                    self.log("Saved to:", "ok")
                    for path in files:
                        self.log(f"  {path}", "ok")
                else:
                    self.log(f"Output folder: {output_dir.resolve()}", "ok")
                self.status_var.set("Done.")
            else:
                self.log(f"Download failed. Exit code: {result}", "error")
                self.log("Try updating the engine, browser cookies, Node.js LTS, or a system-wide VPN/proxy.", "error")
                self.status_var.set("Download failed.")
            self.set_running(False)
            self.process = None

        self.after(0, done)

    def _run_process(self, command: list[str]) -> int:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.after(0, lambda text=line.rstrip(): self.log(text))
        return self.process.wait()

    def _start_process_ui(self, message: str) -> None:
        self.set_running(True)
        self.status_var.set(message)
        self.log("")
        self.log(message, "muted")

    def _finish_process_ui(self, message: str, ok: bool) -> None:
        self.log(message, "ok" if ok else "error")
        self.status_var.set(message)
        self.set_running(False)
        self.process = None


def main() -> int:
    app = DownloaderApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
