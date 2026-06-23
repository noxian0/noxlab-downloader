"""Windowed launcher for NoxLab Downloader."""

from __future__ import annotations

import copy
import ctypes
import os
from pathlib import Path
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import downloader


APP_TITLE = "NoxLab Downloader"
APP_USER_MODEL_ID = "NoxLab.Downloader.App"
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

        self.asset_dir = Path(__file__).resolve().parent / "assets"
        self.icon_png = self.asset_dir / "noxlab_downloader_icon.png"
        self.icon_ico = self.asset_dir / "noxlab_downloader_window.ico"
        self._window_icon: tk.PhotoImage | None = None
        self._native_icon_handles: list[int] = []
        self._apply_window_icon()
        self._apply_dark_title_bar()

        self._build_style()
        self._build_ui()
        self._update_format_choices()
        self._node_warning()
        self.after(250, self._refresh_window_chrome)

    def _refresh_window_chrome(self) -> None:
        self._apply_window_icon()
        self._apply_dark_title_bar()

    def _apply_window_icon(self) -> None:
        if self.icon_png.exists():
            try:
                if self._window_icon is None:
                    self._window_icon = tk.PhotoImage(file=str(self.icon_png))
                self.iconphoto(True, self._window_icon)
            except tk.TclError:
                self._window_icon = None
        if self.icon_ico.exists():
            try:
                self.iconbitmap(default=str(self.icon_ico))
                self.wm_iconbitmap(default=str(self.icon_ico))
            except tk.TclError:
                pass
        self._apply_native_windows_icon()

    def _apply_native_windows_icon(self) -> None:
        if os.name != "nt" or not self.icon_ico.exists():
            return
        try:
            hwnd = int(self.winfo_id())
            user32 = ctypes.windll.user32
            user32.LoadImageW.restype = ctypes.c_void_p
            user32.SendMessageW.restype = ctypes.c_void_p
            user32.GetParent.restype = ctypes.c_void_p
            image_icon = 1
            load_from_file = 0x00000010
            wm_seticon = 0x0080
            icon_small = 0
            icon_big = 1
            small = user32.LoadImageW(None, str(self.icon_ico), image_icon, 16, 16, load_from_file)
            big = user32.LoadImageW(None, str(self.icon_ico), image_icon, 32, 32, load_from_file)
            if small:
                user32.SendMessageW(hwnd, wm_seticon, icon_small, small)
                self._native_icon_handles.append(small)
            if big:
                user32.SendMessageW(hwnd, wm_seticon, icon_big, big)
                self._native_icon_handles.append(big)
            parent = user32.GetParent(hwnd)
            if parent:
                if small:
                    user32.SendMessageW(parent, wm_seticon, icon_small, small)
                if big:
                    user32.SendMessageW(parent, wm_seticon, icon_big, big)
        except Exception:
            pass

    def _apply_dark_title_bar(self) -> None:
        if os.name != "nt":
            return
        try:
            hwnd = int(self.winfo_id())
            user32 = ctypes.windll.user32
            dwmapi = ctypes.windll.dwmapi
            user32.GetParent.restype = ctypes.c_void_p
            handles = [hwnd]
            parent = user32.GetParent(hwnd)
            if parent:
                handles.append(parent)

            dark_enabled = ctypes.c_int(1)
            caption_color = ctypes.c_int(0x202020)
            text_color = ctypes.c_int(0xD0D0D0)
            border_color = ctypes.c_int(0x3A3A3A)

            for handle in dict.fromkeys(handles):
                for attribute in (20, 19):
                    dwmapi.DwmSetWindowAttribute(
                        handle,
                        attribute,
                        ctypes.byref(dark_enabled),
                        ctypes.sizeof(dark_enabled),
                    )
                for attribute, value in ((35, caption_color), (36, text_color), (34, border_color)):
                    dwmapi.DwmSetWindowAttribute(handle, attribute, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.option_add("*TCombobox*Listbox.background", "#101010")
        self.option_add("*TCombobox*Listbox.foreground", "#ffffff")
        self.option_add("*TCombobox*Listbox.selectBackground", "#353535")
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        style.configure("Root.TFrame", background="#121212")
        style.configure("Panel.TFrame", background="#1d1d1d", borderwidth=1, relief="solid")
        style.configure("TLabel", background="#121212", foreground="#e7e7e7")
        style.configure("Panel.TLabel", background="#1d1d1d", foreground="#e7e7e7")
        style.configure("PanelMuted.TLabel", background="#1d1d1d", foreground="#9b9b9b")
        style.configure("Muted.TLabel", background="#121212", foreground="#9b9b9b")
        style.configure("Accent.TLabel", background="#121212", foreground="#ff4b4b")
        style.configure("TButton", padding=(12, 7), background="#2b2b2b", foreground="#f2f2f2")
        style.map("TButton", background=[("active", "#3a3a3a")])
        style.configure("Danger.TButton", padding=(12, 7), background="#772727", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#9b3030")])
        style.configure("TCheckbutton", background="#1d1d1d", foreground="#e7e7e7")
        style.map(
            "TCheckbutton",
            background=[("active", "#1d1d1d"), ("focus", "#1d1d1d")],
            foreground=[("active", "#e7e7e7"), ("focus", "#e7e7e7")],
        )
        style.configure(
            "Dark.TCombobox",
            fieldbackground="#101010",
            background="#2b2b2b",
            foreground="#ffffff",
            arrowcolor="#ffffff",
            bordercolor="#4a4a4a",
            lightcolor="#4a4a4a",
            darkcolor="#4a4a4a",
            selectbackground="#353535",
            selectforeground="#ffffff",
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", "#101010"), ("active", "#101010"), ("focus", "#101010")],
            foreground=[("readonly", "#ffffff"), ("active", "#ffffff"), ("focus", "#ffffff")],
            background=[("readonly", "#2b2b2b"), ("active", "#3a3a3a")],
            selectbackground=[("readonly", "#353535")],
            selectforeground=[("readonly", "#ffffff")],
        )
        style.configure(
            "Dark.TEntry",
            fieldbackground="#101010",
            foreground="#ffffff",
            insertcolor="#ffffff",
            bordercolor="#4a4a4a",
            lightcolor="#4a4a4a",
            darkcolor="#4a4a4a",
        )
        style.map("Dark.TEntry", fieldbackground=[("focus", "#101010")], foreground=[("focus", "#ffffff")])

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
        ttk.Entry(form, textvariable=self.url_var, style="Dark.TEntry").grid(row=0, column=1, columnspan=3, sticky="ew", pady=6)

        ttk.Label(form, text="Mode", style="Panel.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
        self.mode_box = ttk.Combobox(form, textvariable=self.mode_var, values=("video", "audio", "mute"), state="readonly", width=14, style="Dark.TCombobox")
        self.mode_box.grid(row=1, column=1, sticky="w", pady=6)
        self.mode_box.bind("<<ComboboxSelected>>", lambda _event: self._update_format_choices())

        ttk.Label(form, text="Resolution", style="Panel.TLabel").grid(row=1, column=2, sticky="w", padx=(20, 8), pady=6)
        ttk.Combobox(form, textvariable=self.resolution_var, values=downloader.RESOLUTIONS, state="readonly", width=14, style="Dark.TCombobox").grid(row=1, column=3, sticky="w", pady=6)

        ttk.Label(form, text="Format", style="Panel.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=6)
        self.format_box = ttk.Combobox(form, textvariable=self.format_var, state="readonly", width=14, style="Dark.TCombobox")
        self.format_box.grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(form, text="Cookies", style="Panel.TLabel").grid(row=2, column=2, sticky="w", padx=(20, 8), pady=6)
        ttk.Combobox(form, textvariable=self.cookies_var, values=downloader.COOKIE_BROWSERS, state="readonly", width=14, style="Dark.TCombobox").grid(row=2, column=3, sticky="w", pady=6)

        ttk.Label(form, text="Proxy", style="Panel.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(form, textvariable=self.proxy_var, style="Dark.TEntry").grid(row=3, column=1, columnspan=2, sticky="ew", pady=6)
        ttk.Checkbutton(form, text="Download playlist", variable=self.playlist_var).grid(row=3, column=3, sticky="w", pady=6)
        proxy_help = ttk.Label(
            form,
            text="Optional. Use only if you have a proxy URL for region blocks, e.g. http://127.0.0.1:8080 or socks5://127.0.0.1:1080.",
            style="PanelMuted.TLabel",
        )
        proxy_help.grid(row=4, column=1, columnspan=3, sticky="w", pady=(0, 6))

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
    set_windows_app_user_model_id()
    app = DownloaderApp()
    app.mainloop()
    return 0


def set_windows_app_user_model_id() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
