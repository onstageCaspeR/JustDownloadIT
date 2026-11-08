"""
============================================================================
 JustDownloadIT - Simple YouTube Downloader
 Single-file app. Backend: yt-dlp. Full videos, clips, queue, recent list.
============================================================================

QUICK START (for developers / anyone with Python):
    pip install yt-dlp
    python JustDownloadIT.py
    (On Windows, ffmpeg is auto-downloaded on first run if missing.
     On Mac/Linux, install it yourself: brew install ffmpeg / apt install ffmpeg)

WANT A DOUBLE-CLICK .exe FOR WINDOWS (no Python/pip needed by end users)?
    This one file can generate its own one-time build script. Run:
        python JustDownloadIT.py --make-build-script
    That writes "build_windows.bat" next to this file. Copy both files to
    a Windows PC and double-click build_windows.bat once. It will:
      1) Install Python build tools (if Python itself is already present)
      2) Install yt-dlp + pyinstaller
      3) Package everything into dist\\JustDownloadIT.exe

    The resulting JustDownloadIT.exe is fully self-contained - copy/share just
    that one file and it needs nothing else installed, not even Python.
    (Only the one-time build needs Python; the finished .exe does not.)
============================================================================
"""

import os
import re
import sys
import json
import time
import hashlib
import zipfile
import shutil
import threading
import platform
import tempfile
import uuid
import urllib.request
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR

FFMPEG_DIR = os.path.join(APP_DIR, "ffmpeg_bin")
BUNDLED_FFMPEG_DIR = os.path.join(BUNDLE_DIR, "ffmpeg_bin")
RECENT_FILE = os.path.join(APP_DIR, "justdownloadit_recent.json")

APP_VERSION = "1.2.1"
GITHUB_REPOSITORY = "onstageCaspeR/JustDownloadIT"
GITHUB_LATEST_RELEASE_API = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
RELEASES_PAGE_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases/latest"
UPDATE_CHECK_STATE_FILE = os.path.join(APP_DIR, "justdownloadit_update.json")
UPDATE_CHECK_INTERVAL = 24 * 60 * 60
UPDATE_INSTALL_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JustDownloadIT"
)
UPDATE_INSTALLER_NAME = "JustDownloadIT-Setup.exe"

FFMPEG_WIN_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

BLACK = "#000000"
BG_BLACK = "#eaf4ff"
BG_DARK = "#0b0b0d"
PANEL = "#eaf4ff"
PANEL_2 = "#ffffff"
ICE_WHITE = "#f2f6fb"
ICE_BLUE = "#bfe3ff"
ACCENT = "#3aa0ff"
ACCENT_HOVER = "#5cb3ff"
ACCENT_PRESSED = "#2b88e0"
SUBTLE = "#000000"
SUBTLE_DARK = "#000000"
TEXT_DARK = "#000000"
BORDER = "#060608"
BORDER_LIGHT = "#c7dbf5"
BORDER_THICK = 2
SUCCESS = "#4ade80"
SUCCESS_DARK = "#22c55e"
ERROR = "#f87171"
ERROR_DARK = "#ef4444"
WARN = "#fbbf24"
SHADOW_1 = "#d0d4da"
SHADOW_2 = "#e4e8ee"
SHADOW_OFFSET = 2
GRAY_SUBTITLE = "#4a4a4a"

FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_SUBTITLE = ("Segoe UI", 11)
FONT_LABEL = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 9)
FONT_BUTTON = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 8)
FONT_ICON = ("Segoe UI Symbol", 14, "bold")
FONT_ICON_LG = ("Segoe UI Symbol", 22, "bold")


def parse_release_version(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value).strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def is_newer_version(candidate, current=APP_VERSION):
    candidate_version = parse_release_version(candidate)
    current_version = parse_release_version(current)
    return bool(candidate_version and current_version and candidate_version > current_version)


def find_ffmpeg():
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    ext = ".exe" if os.name == "nt" else ""
    bundled = os.path.join(BUNDLED_FFMPEG_DIR, f"ffmpeg{ext}")
    if os.path.isfile(bundled):
        return bundled
    local = os.path.join(FFMPEG_DIR, f"ffmpeg{ext}")
    if os.path.isfile(local):
        return local
    return None


def download_ffmpeg_windows(progress_cb=None):
    os.makedirs(FFMPEG_DIR, exist_ok=True)
    zip_path = os.path.join(FFMPEG_DIR, "ffmpeg.zip")

    def _hook(block_num, block_size, total_size):
        if progress_cb and total_size > 0:
            pct = min(100, block_num * block_size * 100 / total_size)
            progress_cb(pct)

    urllib.request.urlretrieve(FFMPEG_WIN_URL, zip_path, _hook)

    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():
            if member.endswith("bin/ffmpeg.exe"):
                z.extract(member, FFMPEG_DIR)
                extracted = os.path.join(FFMPEG_DIR, member)
                target = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
                shutil.move(extracted, target)
                break

    os.remove(zip_path)
    for entry in os.listdir(FFMPEG_DIR):
        full = os.path.join(FFMPEG_DIR, entry)
        if os.path.isdir(full):
            shutil.rmtree(full, ignore_errors=True)

    final_path = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
    if not os.path.isfile(final_path):
        raise RuntimeError("ffmpeg download completed but ffmpeg.exe was not found in the archive.")
    return final_path


def parse_timestamp(ts):
    ts = ts.strip()
    if not ts:
        return None
    parts = ts.split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def format_speed(bps):
    if bps is None or bps <= 0:
        return "—"
    if bps >= 1024 * 1024:
        return f"{bps / (1024 * 1024):.2f} MiB/s"
    if bps >= 1024:
        return f"{bps / 1024:.2f} KiB/s"
    return f"{bps:.0f} B/s"


def format_eta(secs):
    if secs is None or secs < 0:
        return "—"
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def load_recent():
    if os.path.isfile(RECENT_FILE):
        try:
            with open(RECENT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_recent(recent):
    try:
        with open(RECENT_FILE, "w") as f:
            json.dump(recent[-5:], f, indent=2)
    except Exception:
        pass


def open_folder(path):
    folder = os.path.dirname(path) if os.path.isfile(path) else path
    if not os.path.isdir(folder):
        return
    try:
        if os.name == "nt":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except Exception:
        pass


def quality_to_format(quality, audio_only=False):
    if audio_only:
        return "bestaudio/best"
    if quality == "Best":
        return "bestvideo+bestaudio/best"
    h_map = {"2160p": "2160", "1440p": "1440", "1080p": "1080", "720p": "720", "480p": "480", "360p": "360"}
    h = h_map.get(quality, "720")
    return (
        f"bestvideo[height<={h}]+bestaudio/"
        f"best[height<={h}]/bestvideo[height<={h}]+bestaudio/best[height<={h}]"
    )


def fetch_video_duration(url, ffmpeg_path=None):
    if yt_dlp is None:
        return None
    try:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
        }
        if ffmpeg_path:
            opts["ffmpeg_location"] = ffmpeg_path
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration")
            if duration is not None:
                return float(duration)
    except Exception:
        return None
    return None


class IceButton(tk.Frame):
    def __init__(self, master, variant="primary", width=None, **kwargs):
        self.variant = variant
        variants = {
            "primary": (ACCENT, ACCENT_HOVER, ACCENT_PRESSED, BLACK),
            "secondary": (PANEL_2, "#2a2a30", "#35353b", BLACK),
            "ghost": (BG_BLACK, PANEL, PANEL_2, BLACK),
            "success": (SUCCESS_DARK, "#4ade80", "#16a34a", BLACK),
            "danger": (ERROR_DARK, "#f87171", "#dc2626", BLACK),
        }
        bg, hover, press, fg = variants.get(variant, variants["primary"])
        self._bg = bg
        self._hover = hover
        self._press = press
        self._fg = fg
        super().__init__(master, bg=SHADOW_1, highlightthickness=0)
        self._btn = tk.Button(
            self,
            bg=bg,
            fg=fg,
            activebackground=press,
            activeforeground=fg,
            font=FONT_BUTTON,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14 if width is None else 0,
            pady=8,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
            width=width,
            **kwargs,
        )
        self._btn.pack(fill="both", expand=True, padx=(0, SHADOW_OFFSET), pady=(0, SHADOW_OFFSET))
        self._btn.bind("<Enter>", self._on_enter)
        self._btn.bind("<Leave>", self._on_leave)
        self._btn.bind("<ButtonPress-1>", self._on_press, add="+")
        self._btn.bind("<ButtonRelease-1>", self._on_release, add="+")

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._btn, name)

    def config(self, **kw):
        self._btn.config(**kw)

    def configure(self, **kw):
        self._btn.configure(**kw)

    def bind(self, *a, **kw):
        self._btn.bind(*a, **kw)

    def _on_enter(self, e):
        if self._btn["state"] != "disabled":
            self._btn.config(bg=self._hover)

    def _on_leave(self, e):
        if self._btn["state"] != "disabled":
            self._btn.config(bg=self._bg)

    def _on_press(self, e):
        if self._btn["state"] != "disabled":
            self._btn.config(bg=self._press)

    def _on_release(self, e):
        if self._btn["state"] != "disabled":
            self._btn.config(bg=self._hover)


class RoundedPanel(tk.Frame):
    def __init__(self, master, bg=PANEL, border=BORDER, pad=18, **kwargs):
        super().__init__(master, bg=SHADOW_1, highlightthickness=0, **kwargs)
        self._inner_pad = pad
        self.body = tk.Frame(
            self,
            bg=bg,
            highlightbackground=border,
            highlightthickness=BORDER_THICK,
        )
        self.body.pack(fill="both", expand=True, padx=(0, SHADOW_OFFSET), pady=(0, SHADOW_OFFSET))


class RoundedEntry(tk.Frame):
    def __init__(self, master, width=None, show=None, **kwargs):
        super().__init__(master, bg=SHADOW_1, highlightthickness=0)
        self._frame = tk.Frame(
            self,
            bg=PANEL_2,
            highlightbackground=BORDER,
            highlightthickness=BORDER_THICK,
        )
        self._frame.pack(fill="both", expand=True, padx=(0, SHADOW_OFFSET), pady=(0, SHADOW_OFFSET))
        self._entry = tk.Entry(
            self._frame,
            font=FONT_LABEL,
            bg=PANEL_2,
            fg=BLACK,
            insertbackground=BLACK,
            relief="flat",
            bd=0,
            width=width,
            show=show,
            **kwargs,
        )
        self._entry.pack(fill="both", expand=True, padx=10, pady=6)

    def get(self):
        return self._entry.get()

    def set(self, val):
        self._entry.delete(0, tk.END)
        self._entry.insert(0, val)

    def delete(self, *a):
        self._entry.delete(*a)

    def insert(self, *a):
        self._entry.insert(*a)

    def bind(self, seq, cb):
        self._entry.bind(seq, cb)

    def config(self, **kw):
        if "state" in kw:
            self._entry.config(state=kw["state"])
            state = kw["state"]
            self._entry.config(bg=PANEL_2 if state == "normal" else PANEL,
                               disabledforeground=BLACK if state == "disabled" else BLACK)
            self._frame.config(bg=PANEL_2 if state == "normal" else PANEL)
        if "highlightcolor" in kw:
            self._frame.config(highlightcolor=kw["highlightcolor"])
        self._entry.config(**{k: v for k, v in kw.items() if k != "state" and k != "highlightcolor"})

    def entry(self):
        return self._entry


class IconButton(tk.Frame):
    def __init__(self, master, text="⚙", **kwargs):
        self._bg = BG_BLACK
        self._hover = "#e0edff"
        self._press = "#d3e5ff"
        super().__init__(master, bg=SHADOW_1, highlightthickness=0)
        self._btn = tk.Button(
            self,
            text=text,
            bg=self._bg,
            fg=ACCENT,
            activebackground=self._press,
            activeforeground=ACCENT,
            font=FONT_ICON,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=8,
            pady=4,
            **kwargs,
        )
        self._btn.pack(fill="both", expand=True, padx=(0, SHADOW_OFFSET), pady=(0, SHADOW_OFFSET))
        self._btn.bind("<Enter>", self._on_enter)
        self._btn.bind("<Leave>", self._on_leave)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._btn, name)

    def config(self, **kw):
        self._btn.config(**kw)

    def configure(self, **kw):
        self._btn.configure(**kw)

    def bind(self, *a, **kw):
        self._btn.bind(*a, **kw)

    def _on_enter(self, e):
        if self._btn["state"] != "disabled":
            self._btn.config(bg=self._hover)

    def _on_leave(self, e):
        if self._btn["state"] != "disabled":
            self._btn.config(bg=self._bg)


class QualityCombobox(ttk.Combobox):
    def __init__(self, master, **kwargs):
        super().__init__(master, style="Ice.TCombobox", **kwargs)


class DownloadQueueItem:
    STATUSES = ("queued", "downloading", "done", "failed", "skipped")

    def __init__(self, url, mode="full", start_sec=None, end_sec=None,
                 fmt="Video (MP4)", quality="Best"):
        self.url = url
        self.mode = mode
        self.start_sec = start_sec
        self.end_sec = end_sec
        self.fmt = fmt
        self.quality = quality
        self.status = "queued"
        self.title = url[:60]
        self.error_msg = ""
        self.saved_path = ""
        self.progress = 0.0


class ProgressWithLabel(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=SHADOW_1, highlightthickness=0, **kwargs)
        self.body = tk.Frame(
            self, bg=PANEL, highlightbackground=BORDER, highlightthickness=BORDER_THICK
        )
        self.body.pack(fill="both", expand=True, padx=(0, SHADOW_OFFSET), pady=(0, SHADOW_OFFSET))
        self.progress = ttk.Progressbar(
            self.body, style="BigIce.Horizontal.TProgressbar", mode="determinate", length=400
        )
        self.progress.pack(side="left", fill="both", expand=True, padx=(6, 10), pady=6, ipady=2)
        self.pct_var = tk.StringVar(value="0%")
        self.pct_label = tk.Label(
            self.body, textvariable=self.pct_var, font=FONT_BUTTON, fg=BLACK, bg=PANEL, width=6, anchor="e"
        )
        self.pct_label.pack(side="right", padx=(0, 8))

    def set(self, value):
        v = max(0.0, min(100.0, float(value)))
        self.progress["value"] = v
        self.pct_var.set(f"{v:.0f}%")


class SuccessBanner(tk.Frame):
    def __init__(self, master, on_close=None, **kwargs):
        super().__init__(master, bg=SHADOW_1, highlightthickness=0, **kwargs)
        self._on_close = on_close
        self.body = tk.Frame(
            self, bg=PANEL, highlightbackground=SUCCESS_DARK, highlightthickness=1
        )
        self.body.pack(fill="both", expand=True, padx=(0, SHADOW_OFFSET), pady=(0, SHADOW_OFFSET))
        self._check = tk.Label(
            self.body, text="✓", font=FONT_ICON_LG, fg=BLACK, bg=PANEL
        )
        self._check.pack(side="left", padx=(14, 8), pady=10)
        self._msg = tk.Label(
            self.body, text="Download complete!", font=FONT_LABEL, fg=BLACK, bg=PANEL, anchor="w"
        )
        self._msg.pack(side="left", fill="both", expand=True, pady=10)
        self._close = tk.Button(
            self.body, text="✕", font=("Segoe UI", 10, "bold"), fg=BLACK, bg=PANEL,
            relief="flat", bd=0, cursor="hand2", activebackground=PANEL, activeforeground=BLACK,
            command=self.hide, padx=8, pady=4,
        )
        self._close.pack(side="right", padx=8)
        self._close.bind("<Enter>", lambda e: self._close.config(fg=BLACK))
        self._close.bind("<Leave>", lambda e: self._close.config(fg=BLACK))
        self.hide()

    def show(self, message=None):
        if message:
            self._msg.config(text=message)
        self.pack(fill="x", padx=18, pady=(0, 10), after=self.master.winfo_children()[-1] if self.master.winfo_children() else None)
        self.tkraise()
        try:
            alpha = [0.0]
            def fade():
                alpha[0] = min(1.0, alpha[0] + 0.2)
                self.lift()
                if alpha[0] < 1.0:
                    self.after(30, fade)
            fade()
        except Exception:
            pass

    def hide(self):
        try:
            self.pack_forget()
        except Exception:
            pass
        if self._on_close:
            self._on_close()


class JustDownloadITApp:
    def __init__(self, root):
        self.root = root
        root.title("JustDownloadIT — YouTube Downloader")
        root.geometry("720x760")
        root.minsize(640, 680)
        root.configure(bg=BG_BLACK)

        self.default_format = "Video (MP4)"
        self.default_quality = "Best"
        self.recent = load_recent()
        self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.ffmpeg_path = find_ffmpeg()
        self.queue = []
        self.current_queue_index = -1
        self.download_thread = None
        self.is_processing_queue = False
        self._queue_widgets = {}
        self._auto_start_queue = False

        self._setup_styles()
        self._build_ui()
        self._refresh_recent_panel()

        if self.ffmpeg_path is None:
            if os.name == "nt":
                self.root.after(400, self._ensure_ffmpeg_windows)
            else:
                self.status_var.set(
                    "ffmpeg not found — please install it (brew install ffmpeg / apt install ffmpeg) "
                    "for best results."
                )

        if self._is_managed_install():
            self.root.after(1200, self._check_for_updates)

    @staticmethod
    def _is_managed_install():
        if os.name != "nt" or not getattr(sys, "frozen", False):
            return False
        installed_dir = os.path.normcase(os.path.abspath(UPDATE_INSTALL_DIR))
        running_dir = os.path.normcase(os.path.abspath(APP_DIR))
        return installed_dir == running_dir

    def _check_for_updates(self):
        try:
            with open(UPDATE_CHECK_STATE_FILE, "r", encoding="utf-8") as f:
                last_check = float(json.load(f).get("last_check", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            last_check = 0
        if time.time() - last_check < UPDATE_CHECK_INTERVAL:
            return
        threading.Thread(target=self._fetch_latest_release, daemon=True).start()

    def _fetch_latest_release(self):
        request = urllib.request.Request(
            GITHUB_LATEST_RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"JustDownloadIT/{APP_VERSION}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                release = json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))
            with open(UPDATE_CHECK_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_check": time.time()}, f)
        except Exception:
            return

        if not isinstance(release, dict):
            return
        tag = release.get("tag_name", "")
        if not is_newer_version(tag):
            return
        assets = release.get("assets") or []
        installer = next(
            (asset for asset in assets if asset.get("name") == UPDATE_INSTALLER_NAME),
            None,
        )
        if not installer:
            return
        asset_url = installer.get("browser_download_url", "")
        if not self._valid_release_asset_url(asset_url):
            return
        release["_installer_asset"] = installer
        release["_checksum_asset"] = next(
            (
                asset for asset in assets
                if asset.get("name") == f"{UPDATE_INSTALLER_NAME}.sha256"
            ),
            None,
        )
        try:
            self.root.after(0, self._offer_update, release)
        except tk.TclError:
            pass

    def _offer_update(self, release):
        version = release["tag_name"].lstrip("v")
        notes = (release.get("body") or "").strip()
        if len(notes) > 500:
            notes = notes[:497] + "..."
        details = f"\n\nRelease notes:\n{notes}" if notes else ""
        accepted = messagebox.askyesno(
            "Free update available",
            f"JustDownloadIT {version} is available. This app and its updates are free.\n\n"
            f"Update now? The app will close, install the update, and reopen.{details}",
            parent=self.root,
        )
        if not accepted:
            self.status_var.set(f"Update {version} available; you can install it later.")
            return
        self.status_var.set(f"Downloading free update {version}…")
        threading.Thread(
            target=self._download_update,
            args=(release,),
            daemon=True,
        ).start()

    @staticmethod
    def _valid_release_asset_url(url):
        expected_prefix = (
            f"https://github.com/{GITHUB_REPOSITORY}/releases/download/"
        )
        return str(url).lower().startswith(expected_prefix.lower())

    @staticmethod
    def _is_github_asset_host(url):
        lowered = str(url).lower()
        return lowered.startswith((
            "https://github.com/",
            "https://release-assets.githubusercontent.com/",
            "https://objects.githubusercontent.com/",
        ))

    def _download_update(self, release):
        asset = release["_installer_asset"]
        checksum_asset = release.get("_checksum_asset")
        url = asset["browser_download_url"]
        expected_digest = asset.get("digest") or ""
        if expected_digest.startswith("sha256:"):
            expected_digest = expected_digest.split(":", 1)[1].lower()
        else:
            expected_digest = ""

        installer_path = os.path.join(
            tempfile.gettempdir(),
            f"JustDownloadIT-Setup-{uuid.uuid4().hex}.exe",
        )
        try:
            if not self._valid_release_asset_url(url):
                raise RuntimeError("The release installer URL is not trusted.")
            request = urllib.request.Request(
                url,
                headers={"User-Agent": f"JustDownloadIT/{APP_VERSION}"},
            )
            digest = hashlib.sha256()
            written = 0
            total = int(asset.get("size") or 0)
            with urllib.request.urlopen(request, timeout=30) as response:
                if not self._is_github_asset_host(response.geturl()):
                    raise RuntimeError("The installer download redirected to an untrusted host.")
                with open(installer_path, "wb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > 200 * 1024 * 1024:
                            raise RuntimeError("The installer is unexpectedly large.")
                        output.write(chunk)
                        digest.update(chunk)
                        if total:
                            pct = min(100, written * 100 / total)
                            try:
                                self.root.after(
                                    0, self._set_update_progress, pct, release["tag_name"]
                                )
                            except tk.TclError:
                                pass

            if total and written != total:
                raise RuntimeError("The downloaded installer size does not match GitHub's release metadata.")

            if not expected_digest and checksum_asset:
                checksum_url = checksum_asset.get("browser_download_url", "")
                if not self._valid_release_asset_url(checksum_url):
                    raise RuntimeError("The release checksum URL is not trusted.")
                checksum_request = urllib.request.Request(
                    checksum_url,
                    headers={"User-Agent": f"JustDownloadIT/{APP_VERSION}"},
                )
                with urllib.request.urlopen(checksum_request, timeout=15) as response:
                    if not self._is_github_asset_host(response.geturl()):
                        raise RuntimeError("The checksum download redirected to an untrusted host.")
                    checksum_text = response.read(4096).decode("ascii", errors="strict")
                match = re.search(r"\b([0-9a-fA-F]{64})\b", checksum_text)
                if match:
                    expected_digest = match.group(1).lower()

            if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
                raise RuntimeError("The release has no valid SHA-256 checksum.")
            if digest.hexdigest() != expected_digest:
                raise RuntimeError("The installer failed its SHA-256 integrity check.")

            try:
                self.root.after(
                    0, self._launch_update_installer, installer_path, release["tag_name"]
                )
            except tk.TclError:
                pass
        except Exception as e:
            try:
                if os.path.isfile(installer_path):
                    os.remove(installer_path)
            except OSError:
                pass
            try:
                self.root.after(0, self._update_failed, str(e))
            except tk.TclError:
                pass

    def _set_update_progress(self, pct, version):
        self.status_var.set(f"Downloading update {version}… {pct:.0f}%")

    @staticmethod
    def _powershell_quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    def _launch_update_installer(self, installer_path, version):
        powershell = os.path.join(
            os.environ.get("WINDIR", r"C:\Windows"),
            "System32",
            "WindowsPowerShell",
            "v1.0",
            "powershell.exe",
        )
        script_path = os.path.join(
            tempfile.gettempdir(), f"jdit_update_{uuid.uuid4().hex}.ps1"
        )
        app_path = os.path.join(UPDATE_INSTALL_DIR, "JustDownloadIT.exe")
        script = (
            f"$parentId = {os.getpid()}\n"
            "while (Get-Process -Id $parentId -ErrorAction SilentlyContinue) "
            "{ Start-Sleep -Milliseconds 250 }\n"
            f"$setup = {self._powershell_quote(installer_path)}\n"
            f"$app = {self._powershell_quote(app_path)}\n"
            "$p = Start-Process -FilePath $setup "
            "-ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-' "
            "-Wait -PassThru\n"
            "if ($p.ExitCode -eq 0 -and (Test-Path -LiteralPath $app)) "
            "{ Start-Process -FilePath $app }\n"
            "Remove-Item -LiteralPath $setup -Force -ErrorAction SilentlyContinue\n"
            "Remove-Item -LiteralPath $MyInvocation.MyCommand.Path "
            "-Force -ErrorAction SilentlyContinue\n"
        )
        try:
            with open(script_path, "w", encoding="utf-8-sig") as f:
                f.write(script)
            subprocess.Popen(
                [
                    powershell,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-WindowStyle",
                    "Hidden",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    script_path,
                ],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                close_fds=True,
            )
        except Exception as e:
            try:
                os.remove(script_path)
            except OSError:
                pass
            self._update_failed(str(e))
            return
        self.status_var.set(f"Installing update {version}…")
        self.root.destroy()

    def _update_failed(self, error):
        self.status_var.set("The update could not be installed.")
        messagebox.showwarning(
            "Update failed",
            f"The update could not be installed:\n{error}\n\n"
            f"You can download it manually from:\n{RELEASES_PAGE_URL}",
            parent=self.root,
        )

    # ---------- STYLE SETUP (RUNS ONCE) ----------
    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("default")
        except Exception:
            pass
        style.configure(
            "Ice.TCombobox",
            fieldbackground=PANEL_2,
            background=PANEL_2,
            foreground=BLACK,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            arrowcolor=ACCENT,
            padding=6,
            font=FONT_LABEL,
            relief="flat",
            borderwidth=BORDER_THICK,
        )
        style.map(
            "Ice.TCombobox",
            fieldbackground=[("readonly", PANEL_2), ("active", PANEL_2)],
            background=[("readonly", PANEL_2), ("active", PANEL_2)],
            foreground=[("readonly", BLACK)],
            selectbackground=[("readonly", ACCENT)],
            selectforeground=[("readonly", BLACK)],
            bordercolor=[("readonly", BORDER), ("active", BORDER)],
        )
        style.configure(
            "BigIce.Horizontal.TProgressbar",
            troughcolor=PANEL_2,
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            thickness=20,
            troughrelief="flat",
            relief="flat",
        )
        style.configure(
            "Q.Horizontal.TProgressbar",
            troughcolor="#f0f5fc",
            background=ACCENT,
            thickness=5,
            bordercolor=BORDER,
            troughrelief="flat",
            relief="flat",
        )

    # ---------- UI BUILD ----------
    def _build_ui(self):
        root = self.root

        # ---------- HEADER ----------
        header = tk.Frame(root, bg=BG_BLACK)
        header.pack(fill="x", padx=28, pady=(22, 8))

        logo_frame = tk.Frame(header, bg=BG_BLACK)
        logo_frame.pack(side="left")
        self._draw_logo(logo_frame)

        title_frame = tk.Frame(header, bg=BG_BLACK)
        title_frame.pack(side="left", padx=(14, 0), pady=(2, 0))
        tk.Label(title_frame, text="JustDownloadIT", font=FONT_TITLE, fg=BLACK, bg=BG_BLACK).pack(anchor="w")
        tk.Label(title_frame, text="YouTube Downloader", font=FONT_SUBTITLE, fg=BLACK, bg=BG_BLACK).pack(anchor="w", pady=(1, 0))

        # ---------- MAIN CONTENT ----------
        container = tk.Frame(root, bg=BG_BLACK)
        container.pack(fill="both", expand=True, padx=28, pady=(4, 20))

        # ---------- SUCCESS BANNER ----------
        self.success_banner = tk.Frame(container, bg=SHADOW_1, highlightthickness=0)
        self.success_banner.pack(fill="x", padx=0, pady=(0, 12))
        self.success_banner.pack_forget()
        sb_body = tk.Frame(
            self.success_banner, bg=PANEL,
            highlightbackground=SUCCESS_DARK, highlightthickness=BORDER_THICK,
        )
        sb_body.pack(fill="both", expand=True, padx=(0, SHADOW_OFFSET), pady=(0, SHADOW_OFFSET))
        tk.Label(sb_body, text="✓", font=FONT_ICON_LG, fg=BLACK, bg=PANEL).pack(side="left", padx=(14, 10), pady=10)
        self.success_msg = tk.Label(sb_body, text="", font=FONT_LABEL, fg=BLACK, bg=PANEL, anchor="w")
        self.success_msg.pack(side="left", fill="both", expand=True, pady=10)
        sb_close = tk.Button(
            sb_body, text="✕", font=("Segoe UI", 10, "bold"), fg=BLACK, bg=PANEL,
            relief="flat", bd=0, cursor="hand2", activebackground=PANEL, activeforeground=BLACK,
            command=self._hide_success_banner, padx=10, pady=4,
        )
        sb_close.pack(side="right", padx=10)
        sb_close.bind("<Enter>", lambda e: sb_close.config(fg=BLACK))
        sb_close.bind("<Leave>", lambda e: sb_close.config(fg=BLACK))

        # ---------- DOWNLOAD FORM PANEL ----------
        form = RoundedPanel(container, bg=PANEL)
        form.pack(fill="x", pady=(0, 14))
        self.form_panel = form
        fb = form.body

        pad = {"padx": 18, "pady": 8}

        # URL row
        url_label_row = tk.Frame(fb, bg=PANEL)
        url_label_row.pack(fill="x", padx=18, pady=(18, 4))
        tk.Label(url_label_row, text="Video URL", font=FONT_LABEL, fg=BLACK, bg=PANEL).pack(side="left")

        url_row = tk.Frame(fb, bg=PANEL)
        url_row.pack(fill="x", padx=18, pady=(0, 4))

        self.url_entry = RoundedEntry(url_row)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.set("https://www.youtube.com/watch?v=...")
        self.url_entry.bind("<FocusIn>", self._clear_placeholder)
        self.url_entry.bind("<Return>", lambda e: self._add_to_queue())

        self.paste_btn = IceButton(url_row, variant="secondary", text="📋  Paste", width=10, command=self._paste_url)
        self.paste_btn.pack(side="left", padx=(0, 8))

        self.add_queue_btn = IceButton(url_row, variant="secondary", text="＋  Add", width=8, command=self._add_to_queue)
        self.add_queue_btn.pack(side="left")

        # Mode selector
        mode_frame = tk.Frame(fb, bg=PANEL)
        mode_frame.pack(fill="x", **pad)
        tk.Label(mode_frame, text="Download mode:", font=FONT_LABEL, fg=BLACK, bg=PANEL).pack(side="left")
        self.mode_var = tk.StringVar(value="full")
        style_rb = {"bg": PANEL, "fg": BLACK, "selectcolor": "#ffffff", "activebackground": "#e0edff", "activeforeground": BLACK, "font": FONT_LABEL, "cursor": "hand2"}
        self.rb_full = tk.Radiobutton(mode_frame, text="Full Video", variable=self.mode_var, value="full", command=self._toggle_timestamp_fields, **style_rb)
        self.rb_full.pack(side="left", padx=(14, 0))
        self.rb_clip = tk.Radiobutton(mode_frame, text="Timestamp Clip", variable=self.mode_var, value="clip", command=self._toggle_timestamp_fields, **style_rb)
        self.rb_clip.pack(side="left", padx=(14, 0))
        for rb in (self.rb_full, self.rb_clip):
            rb.bind("<Enter>", lambda e, w=rb: w.config(fg=BLACK))
            rb.bind("<Leave>", lambda e, w=rb: w.config(fg=BLACK))

        # Timestamp fields (wrapped for blur overlay effect)
        self.ts_wrapper = tk.Frame(fb, bg=PANEL, highlightthickness=0)
        self.ts_wrapper.pack(fill="x", padx=18, pady=(0, 2))
        self.ts_frame = tk.Frame(self.ts_wrapper, bg=PANEL)
        self.ts_frame.pack(fill="x")
        l_pad = {"font": FONT_LABEL, "fg": BLACK, "bg": PANEL}
        e_bg = {"bg": PANEL_2, "fg": BLACK, "insertbackground": BLACK, "relief": "flat", "highlightthickness": BORDER_THICK, "highlightbackground": BORDER, "highlightcolor": ACCENT, "disabledforeground": BLACK}
        self.ts_start_lbl = tk.Label(self.ts_frame, text="Start (HH:MM:SS)", **l_pad)
        self.ts_start_lbl.grid(row=0, column=0, sticky="w")
        self.ts_end_lbl = tk.Label(self.ts_frame, text="End (HH:MM:SS)", **l_pad)
        self.ts_end_lbl.grid(row=0, column=1, sticky="w", padx=(20, 0))
        self.start_entry = tk.Entry(self.ts_frame, width=15, **e_bg)
        self.start_entry.grid(row=1, column=0, ipady=6, pady=(2, 0), sticky="w", padx=(0, 0))
        self.start_entry.insert(0, "00:00:00")
        self.end_entry = tk.Entry(self.ts_frame, width=15, **e_bg)
        self.end_entry.grid(row=1, column=1, ipady=6, pady=(2, 0), sticky="w", padx=(20, 0))
        self.end_entry.insert(0, "00:00:00")
        # Blur overlay — raised when Full Video mode is active to "dim" timestamp fields
        self.ts_blur = tk.Frame(self.ts_wrapper, bg=PANEL, highlightbackground=BORDER, highlightthickness=BORDER_THICK)
        self.ts_blur_lbl = tk.Label(
            self.ts_blur,
            text="⏸  Timestamp clip disabled — choose \"Timestamp Clip\" mode above",
            font=FONT_LABEL,
            fg=BLACK,
            bg="#f5f9ff",
        )
        self.ts_blur_lbl.pack(expand=True, fill="both", padx=12, pady=10)
        self._toggle_timestamp_fields()

        # Format + Quality row
        fmt_q_frame = tk.Frame(fb, bg=PANEL)
        fmt_q_frame.pack(fill="x", **pad)
        fmt_col = tk.Frame(fmt_q_frame, bg=PANEL)
        fmt_col.pack(side="left", fill="x", expand=True)
        tk.Label(fmt_col, text="Format:", font=FONT_LABEL, fg=BLACK, bg=PANEL).pack(anchor="w")
        self.format_var = tk.StringVar(value=self.default_format)
        QualityCombobox(fmt_col, textvariable=self.format_var, values=["Video (MP4)", "Audio only (MP3)"], state="readonly", width=18).pack(anchor="w", pady=(2, 0))

        q_col = tk.Frame(fmt_q_frame, bg=PANEL)
        q_col.pack(side="left", padx=(14, 0), fill="x", expand=True)
        tk.Label(q_col, text="Quality:", font=FONT_LABEL, fg=BLACK, bg=PANEL).pack(anchor="w")
        self.quality_var = tk.StringVar(value=self.default_quality)
        QualityCombobox(q_col, textvariable=self.quality_var, values=["Best", "2160p", "1440p", "1080p", "720p", "480p", "360p"], state="readonly", width=18).pack(anchor="w", pady=(2, 0))

        # Output dir
        out_frame = tk.Frame(fb, bg=PANEL)
        out_frame.pack(fill="x", **pad)
        tk.Label(out_frame, text="Save to:", font=FONT_LABEL, fg=BLACK, bg=PANEL).pack(anchor="w")
        dir_row = tk.Frame(out_frame, bg=PANEL)
        dir_row.pack(fill="x", pady=(2, 0))
        self.out_label = tk.Label(dir_row, text=self.output_dir, font=FONT_MONO, fg=BLACK, bg=PANEL_2, anchor="w", padx=10, pady=7,
                                  highlightbackground=BORDER, highlightthickness=BORDER_THICK)
        self.out_label.pack(side="left", fill="x", expand=True)
        self.browse_btn = IceButton(dir_row, variant="secondary", text="Browse", width=10, command=self._choose_dir)
        self.browse_btn.pack(side="left", padx=(8, 0))

        # Download action row
        action_row = tk.Frame(fb, bg=PANEL)
        action_row.pack(fill="x", padx=18, pady=(14, 8))
        self.download_btn = IceButton(action_row, variant="primary", text="⬇  Download", command=self._on_download_click)
        self.download_btn.pack(side="left", fill="x", expand=True, ipady=2)
        self.process_queue_btn = IceButton(action_row, variant="success", text="▶  Process Queue", width=18, command=self._start_queue)
        self.process_queue_btn.pack(side="left", padx=(10, 0), ipady=2)
        self.clear_queue_btn = IceButton(action_row, variant="danger", text="🗑  Clear", width=9, command=self._clear_queue)
        self.clear_queue_btn.pack(side="left", padx=(8, 0), ipady=2)

        # Progress
        prog_pad = tk.Frame(fb, bg=PANEL)
        prog_pad.pack(fill="x", padx=18, pady=(8, 4))
        self.progress = ProgressWithLabel(prog_pad)
        self.progress.pack(fill="x")

        # Status
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(fb, textvariable=self.status_var, font=FONT_LABEL, fg=BLACK, bg=PANEL, wraplength=640, anchor="w").pack(padx=18, pady=(0, 18), anchor="w", fill="x")

        # ---------- QUEUE PANEL ----------
        queue_panel = RoundedPanel(container, bg=PANEL)
        queue_panel.pack(fill="x", pady=(0, 14))
        qb = queue_panel.body
        q_header = tk.Frame(qb, bg=PANEL)
        q_header.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(q_header, text="⬇  Download Queue", font=("Segoe UI", 12, "bold"), fg=BLACK, bg=PANEL).pack(side="left")
        self.queue_count_var = tk.StringVar(value="0 items")
        tk.Label(q_header, textvariable=self.queue_count_var, font=FONT_LABEL, fg=BLACK, bg=PANEL).pack(side="right", pady=(2, 0))

        self.queue_list_frame = tk.Frame(qb, bg=PANEL)
        self.queue_list_frame.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        q_empty_wrap = tk.Frame(
            self.queue_list_frame,
            bg=PANEL_2,
            highlightbackground=BORDER,
            highlightthickness=BORDER_THICK,
        )
        q_empty_wrap.pack(fill="x")
        self.queue_empty_lbl = tk.Label(
            q_empty_wrap,
            text="Queue is empty. Paste a URL and click Add.",
            font=FONT_LABEL, fg=BLACK, bg=PANEL_2,
            padx=60, pady=90,
        )
        self.queue_empty_lbl.pack(fill="both", expand=True)

        # ---------- RECENT PANEL ----------
        recent_panel = RoundedPanel(container, bg=PANEL)
        recent_panel.pack(fill="x", pady=(0, 14))
        rb = recent_panel.body
        r_header = tk.Frame(rb, bg=PANEL)
        r_header.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(r_header, text="🕒  Recent Downloads", font=("Segoe UI", 12, "bold"), fg=BLACK, bg=PANEL).pack(side="left")
        tk.Label(r_header, text="(last 5)", font=FONT_SMALL, fg=BLACK, bg=PANEL).pack(side="right", pady=(4, 0))

        self.recent_list_frame = tk.Frame(rb, bg=PANEL)
        self.recent_list_frame.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        r_empty_wrap = tk.Frame(
            self.recent_list_frame,
            bg=PANEL_2,
            highlightbackground=BORDER,
            highlightthickness=BORDER_THICK,
        )
        r_empty_wrap.pack(fill="x")
        self.recent_empty_lbl = tk.Label(
            r_empty_wrap,
            text="No recent downloads yet.",
            font=FONT_LABEL, fg=BLACK, bg=PANEL_2,
            padx=60, pady=90,
        )
        self.recent_empty_lbl.pack(fill="both", expand=True)

        # ---------- FOOTER ----------
        tk.Label(
            container,
            text="Powered by yt-dlp  •  For personal use — respect copyright & YouTube's Terms of Service",
            font=FONT_SMALL, fg=BLACK, bg=BG_BLACK,
        ).pack(pady=(4, 8))

    def _draw_logo(self, parent):
        size = 50
        cvs = tk.Canvas(parent, width=size, height=size, bg=BG_BLACK, highlightthickness=0, bd=0)
        cvs.pack()
        r = 22
        cx, cy = size // 2, size // 2
        cvs.create_oval(cx - r, cy - r, cx + r, cy + r, fill=PANEL, outline=BORDER_LIGHT, width=2)
        try:
            cvs.create_oval(cx - r, cy - r, cx + r, cy + r, fill="", outline=ACCENT, width=2)
        except Exception:
            pass
        pts = [cx - 6, cy - 9, cx + 10, cy, cx - 6, cy + 9]
        cvs.create_polygon(pts, fill=ACCENT, outline=ACCENT)
        for i in range(3):
            x1 = cx - 14 - i * 3
            y1 = cy - 12 + i * 3
            x2 = cx - 10 - i * 3
            y2 = cy - 12 + i * 3
            cvs.create_line(x1, y1, x2, y2, fill=ACCENT, width=2, capstyle="round")

    # ---------- UI HELPERS ----------
    def _hide_success_banner(self):
        try:
            self.success_banner.pack_forget()
        except Exception:
            pass

    def _show_success_banner(self, message, auto_hide_ms=4000):
        self.success_msg.config(text=message)
        try:
            self.success_banner.pack(fill="x", padx=0, pady=(0, 12), before=self.form_panel)
        except Exception:
            self.success_banner.pack(fill="x", padx=0, pady=(0, 12))
        self.success_banner.tkraise()
        if auto_hide_ms:
            self.root.after(auto_hide_ms, self._hide_success_banner)

    def _clear_placeholder(self, event):
        if self.url_entry.get().startswith("https://www.youtube.com/watch?v=..."):
            self.url_entry.delete(0, tk.END)

    def _toggle_timestamp_fields(self):
        is_clip = self.mode_var.get() == "clip"
        if is_clip:
            try:
                self.ts_blur.place_forget()
            except Exception:
                pass
            state = "normal"
            lbl_fg = BLACK
            entry_fg = BLACK
            entry_bg = PANEL_2
            entry_highlight = ACCENT
            for w in (self.start_entry, self.end_entry):
                cur = w.get().strip()
                if not cur or parse_timestamp(cur) is None:
                    was_disabled = str(w["state"]) == "disabled"
                    try:
                        w.config(state="normal")
                    except Exception:
                        pass
                    w.delete(0, tk.END)
                    w.insert(0, "00:00:00")
                    if was_disabled:
                        w.config(state=state)
        else:
            self.ts_wrapper.update_idletasks()
            try:
                self.ts_blur.place(in_=self.ts_wrapper, relx=0, rely=0, relwidth=1, relheight=1)
                self.ts_blur.tkraise()
            except Exception:
                self.ts_blur.pack(fill="both", expand=True, in_=self.ts_wrapper)
                self.ts_blur.tkraise()
            state = "disabled"
            lbl_fg = BLACK
            entry_fg = BLACK
            entry_bg = PANEL
            entry_highlight = BORDER
        for w in (self.start_entry, self.end_entry):
            w.config(state=state, disabledbackground=entry_bg, disabledforeground=entry_fg,
                     bg=entry_bg, fg=entry_fg, highlightbackground=BORDER, highlightcolor=entry_highlight)
        for lbl in (self.ts_start_lbl, self.ts_end_lbl):
            lbl.config(fg=lbl_fg)

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.output_dir)
        if d:
            self.output_dir = d
            self.out_label.config(text=d)

    def _paste_url(self):
        try:
            clip = self.root.clipboard_get()
            if clip:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, clip.strip())
                self.status_var.set("Pasted from clipboard.")
        except tk.TclError:
            self.status_var.set("Clipboard is empty.")

    # ---------- QUEUE MANAGEMENT ----------
    def _add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url or url.startswith("https://www.youtube.com/watch?v=..."):
            messagebox.showwarning("Missing URL", "Please paste a video URL first.")
            return

        start_sec = end_sec = None
        if self.mode_var.get() == "clip":
            raw_start = self.start_entry.get()
            raw_end = self.end_entry.get()
            both_empty = (not raw_start.strip()) and (not raw_end.strip())
            if both_empty:
                messagebox.showwarning("Invalid timestamps", "Enter at least a start or end time for the clip, e.g. 00:01:30")
                return
            start_sec = parse_timestamp(raw_start) if raw_start.strip() else None
            end_sec = parse_timestamp(raw_end) if raw_end.strip() else None
            bad_parse = (raw_start.strip() and start_sec is None) or (raw_end.strip() and end_sec is None)
            if bad_parse:
                messagebox.showwarning("Invalid timestamps", "Could not parse timestamps. Use HH:MM:SS, MM:SS, or seconds, e.g. 00:01:30")
                return
            if start_sec is None and end_sec is not None:
                start_sec = 0.0
            elif start_sec is not None and end_sec is None:
                self.status_var.set("Fetching video length to clip until end…")
                self.root.update_idletasks()
                duration = fetch_video_duration(url, self.ffmpeg_path)
                if duration is None or duration <= 0:
                    messagebox.showwarning(
                        "Cannot determine video length",
                        "Could not fetch the video's length automatically. Please fill in the End time manually for this clip."
                    )
                    return
                end_sec = float(duration)
            if end_sec <= start_sec:
                messagebox.showwarning("Invalid range", "End time must be after start time.")
                return

        item = DownloadQueueItem(
            url=url,
            mode=self.mode_var.get(),
            start_sec=start_sec,
            end_sec=end_sec,
            fmt=self.format_var.get(),
            quality=self.quality_var.get(),
        )
        self.queue.append(item)
        self._refresh_queue_panel()
        self.url_entry.delete(0, tk.END)
        self.url_entry.set("https://www.youtube.com/watch?v=...")
        self.status_var.set(f"Added to queue ({len(self.queue)} items).")

    def _clear_queue(self):
        if self.is_processing_queue and self.download_thread and self.download_thread.is_alive():
            messagebox.showinfo("Busy", "Download in progress — wait for it to finish, or restart the app.")
            return
        self.queue = []
        self.current_queue_index = -1
        self._refresh_queue_panel()
        self.progress.set(0)
        self.status_var.set("Queue cleared.")

    def _refresh_queue_panel(self):
        for w in self.queue_list_frame.winfo_children():
            w.destroy()
        self._queue_widgets = {}

        if not self.queue:
            q_empty_wrap = tk.Frame(
                self.queue_list_frame,
                bg=PANEL_2,
                highlightbackground=BORDER,
                highlightthickness=BORDER_THICK,
            )
            q_empty_wrap.pack(fill="x")
            self.queue_empty_lbl = tk.Label(
                q_empty_wrap,
                text="Queue is empty. Paste a URL and click Add.",
                font=FONT_LABEL, fg=BLACK, bg=PANEL_2,
                padx=60, pady=90,
            )
            self.queue_empty_lbl.pack(fill="both", expand=True)
            self.queue_count_var.set("0 items")
            return

        self.queue_count_var.set(f"{len(self.queue)} item{'s' if len(self.queue) != 1 else ''}")

        status_icon_map = {"queued": "⏸", "downloading": "⏳", "done": "✓", "failed": "✕", "skipped": "→"}
        status_fg_map = {
            "queued": BLACK,
            "downloading": ACCENT,
            "done": SUCCESS_DARK,
            "failed": ERROR_DARK,
            "skipped": WARN,
        }
        title_font = ("Segoe UI", 10, "bold")

        for idx, item in enumerate(self.queue):
            row = tk.Frame(self.queue_list_frame, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill="x", pady=2)

            inner = tk.Frame(row, bg=PANEL_2)
            inner.pack(fill="both", expand=True, padx=18, pady=28)

            icon_fg = status_fg_map.get(item.status, BLACK)
            icon = tk.Label(inner, text=status_icon_map.get(item.status, "?"), font=FONT_ICON, fg=icon_fg, bg=PANEL_2, width=2)
            icon.pack(side="left", padx=(0, 6))

            info = tk.Frame(inner, bg=PANEL_2)
            info.pack(side="left", fill="x", expand=True, padx=(2, 6))
            title_lbl = tk.Label(info, text=item.title[:80], font=title_font, fg=BLACK, bg=PANEL_2, anchor="w", justify="left", state="normal")
            title_lbl.pack(anchor="w", pady=(0, 4))
            meta_parts = []
            if item.mode == "clip":
                def _fmt(s):
                    if s is None:
                        return "?"
                    h, rem = divmod(int(s), 3600)
                    m, sec = divmod(rem, 60)
                    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"
                meta_parts.append(f"Clip {_fmt(item.start_sec)}-{_fmt(item.end_sec)}")
            meta_parts.append(f"{item.fmt} • {item.quality}")
            sub_txt = "  ·  ".join(meta_parts)
            sub_fg = GRAY_SUBTITLE
            if item.status == "failed" and item.error_msg:
                sub_txt += f"   ❌ {item.error_msg[:60]}"
                sub_fg = ERROR_DARK
            elif item.status == "done" and item.saved_path:
                sub_txt += f"   ✓ {os.path.basename(item.saved_path)[:50]}"
                sub_fg = SUCCESS_DARK
            elif item.status == "downloading":
                sub_txt += f"   ↓ {item.progress:.0f}%"
                sub_fg = ACCENT
            sub_lbl = tk.Label(info, text=sub_txt, font=FONT_LABEL, fg=sub_fg, bg=PANEL_2, anchor="w", justify="left", state="normal")
            sub_lbl.pack(anchor="w")

            prog_wrap = tk.Frame(info, bg=PANEL_2)
            prog_wrap.pack(fill="x", pady=(10, 0))
            item_prog = ttk.Progressbar(prog_wrap, style="Q.Horizontal.TProgressbar", mode="determinate", value=item.progress)
            item_prog.pack(fill="x")

            actions = tk.Frame(inner, bg=PANEL_2)
            actions.pack(side="right", padx=8)

            if item.status == "done" and item.saved_path:
                open_wrap = tk.Frame(actions, bg=PANEL_2)
                open_wrap.pack(side="left", padx=2)
                open_btn = tk.Button(
                    open_wrap,
                    text="📂",
                    font=("Segoe UI Symbol", 16, "bold"),
                    fg=ACCENT,
                    bg=PANEL_2,
                    activebackground=ICE_BLUE,
                    activeforeground=BLACK,
                    relief="flat",
                    bd=0,
                    cursor="hand2",
                    padx=6,
                    pady=2,
                    highlightthickness=1,
                    highlightbackground=ACCENT,
                    highlightcolor=ACCENT,
                    command=lambda p=item.saved_path: open_folder(p),
                )
                open_btn.pack(fill="both", expand=True)
            if item.status in ("queued", "failed", "skipped"):
                remove_btn = IconButton(actions, text="✕", command=lambda i=idx: self._remove_queue_item(i))
                remove_btn.pack(side="left", padx=2)
                remove_btn.config(fg=ERROR_DARK)

            self._queue_widgets[idx] = {"row": row, "icon": icon, "title": title_lbl, "sub": sub_lbl, "prog": item_prog}

    def _remove_queue_item(self, idx):
        if idx == self.current_queue_index and self.download_thread and self.download_thread.is_alive():
            self.queue[idx].status = "skipped"
            self._refresh_queue_panel()
            return
        if 0 <= idx < len(self.queue):
            del self.queue[idx]
            if self.current_queue_index > idx:
                self.current_queue_index -= 1
            self._refresh_queue_panel()

    def _update_queue_item_ui(self, idx):
        if idx not in self._queue_widgets:
            return
        item = self.queue[idx]
        w = self._queue_widgets[idx]
        status_icon_map = {"queued": "⏸", "downloading": "⏳", "done": "✓", "failed": "✕", "skipped": "→"}
        status_fg_map = {
            "queued": BLACK,
            "downloading": ACCENT,
            "done": SUCCESS_DARK,
            "failed": ERROR_DARK,
            "skipped": WARN,
        }
        try:
            w["icon"].config(text=status_icon_map.get(item.status, "?"), fg=status_fg_map.get(item.status, BLACK))
            w["prog"].config(value=item.progress)
            meta_parts = []
            if item.mode == "clip":
                def _fmt(s):
                    if s is None:
                        return "?"
                    h, rem = divmod(int(s), 3600)
                    m, sec = divmod(rem, 60)
                    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"
                meta_parts.append(f"Clip {_fmt(item.start_sec)}-{_fmt(item.end_sec)}")
            meta_parts.append(f"{item.fmt} • {item.quality}")
            sub_txt = "  ·  ".join(meta_parts)
            sub_fg = GRAY_SUBTITLE
            if item.status == "failed" and item.error_msg:
                sub_txt += f"   ❌ {item.error_msg[:60]}"
                sub_fg = ERROR_DARK
            elif item.status == "done" and item.saved_path:
                sub_txt += f"   ✓ {os.path.basename(item.saved_path)[:50]}"
                sub_fg = SUCCESS_DARK
            elif item.status == "downloading":
                sub_txt += f"   ↓ {item.progress:.0f}%"
                sub_fg = ACCENT
            w["sub"].config(text=sub_txt, fg=sub_fg, font=FONT_LABEL, state="normal")
            w["title"].config(font=("Segoe UI", 10, "bold"), fg=BLACK, state="normal")
        except Exception:
            pass

    # ---------- RECENT MANAGEMENT ----------
    def _add_recent(self, saved_path, title, url):
        entry = {"path": saved_path, "title": title, "url": url, "ts": time.time()}
        self.recent.insert(0, entry)
        self.recent = self.recent[:5]
        save_recent(self.recent)
        self._refresh_recent_panel()

    def _refresh_recent_panel(self):
        for w in self.recent_list_frame.winfo_children():
            w.destroy()
        if not self.recent:
            r_empty_wrap = tk.Frame(
                self.recent_list_frame,
                bg=PANEL_2,
                highlightbackground=BORDER,
                highlightthickness=BORDER_THICK,
            )
            r_empty_wrap.pack(fill="x")
            self.recent_empty_lbl = tk.Label(
                r_empty_wrap,
                text="No recent downloads yet.",
                font=FONT_LABEL, fg=BLACK, bg=PANEL_2,
                padx=60, pady=90,
            )
            self.recent_empty_lbl.pack(fill="both", expand=True)
            return
        for r in self.recent:
            row = tk.Frame(self.recent_list_frame, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill="x", pady=2)
            inner = tk.Frame(row, bg=PANEL_2)
            inner.pack(fill="both", expand=True, padx=18, pady=24)
            tk.Label(inner, text="📄", font=FONT_ICON, fg=ACCENT, bg=PANEL_2, width=2).pack(side="left", padx=(0, 6))
            info = tk.Frame(inner, bg=PANEL_2)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=(r.get("title") or os.path.basename(r.get("path", "")))[:70], font=("Segoe UI", 10, "bold"), fg=BLACK, bg=PANEL_2, anchor="w", state="normal").pack(anchor="w", pady=(0, 4))
            path_display = r.get("path", "")[:90]
            tk.Label(info, text=path_display, font=FONT_MONO, fg=GRAY_SUBTITLE, bg=PANEL_2, anchor="w", state="normal").pack(anchor="w")
            btns = tk.Frame(inner, bg=PANEL_2)
            btns.pack(side="right", padx=6)
            exists = os.path.isfile(r.get("path", ""))
            open_txt = "📂" if exists else "🗙"
            open_cmd = lambda p=r.get("path", ""): open_folder(p) if exists else messagebox.showinfo("Missing", "File no longer exists.")
            b = IconButton(btns, text=open_txt, command=open_cmd)
            if not exists:
                b.config(fg=GRAY_SUBTITLE)
            b.pack(side="left", padx=2)

    # ---------- DOWNLOAD LOGIC ----------
    def _on_download_click(self):
        if self.is_processing_queue and self.download_thread and self.download_thread.is_alive():
            messagebox.showinfo("Busy", "A queue download is in progress.")
            return
        url = self.url_entry.get().strip()
        if url and not url.startswith("https://www.youtube.com/watch?v=..."):
            self._add_to_queue()
            self.current_queue_index = len(self.queue) - 1
            self.is_processing_queue = False
            item = self.queue[-1]
            self._process_item_individual(item, self.current_queue_index)
        else:
            if self.queue:
                self._start_queue()
            else:
                messagebox.showwarning("Missing URL", "Please paste a video URL first.")

    def _start_queue(self):
        if self.is_processing_queue and self.download_thread and self.download_thread.is_alive():
            messagebox.showinfo("Already processing", "Queue is already being processed.")
            return
        if not self.queue:
            messagebox.showinfo("Empty queue", "Add some URLs to the queue first.")
            return
        self.is_processing_queue = True
        # find next queued/failed item
        start = -1
        for i, it in enumerate(self.queue):
            if it.status in ("queued", "failed", "skipped"):
                start = i
                break
        if start < 0:
            self.status_var.set("All queue items already processed.")
            self.is_processing_queue = False
            return
        self.current_queue_index = start - 1
        self._advance_queue()

    def _advance_queue(self):
        self.current_queue_index += 1
        while self.current_queue_index < len(self.queue):
            it = self.queue[self.current_queue_index]
            if it.status in ("queued", "failed", "skipped"):
                it.status = "queued"
                it.progress = 0
                self._refresh_queue_panel()
                self._process_item_individual(it, self.current_queue_index, from_queue=True)
                return
            self.current_queue_index += 1
        self.is_processing_queue = False
        self._on_queue_finished()

    def _on_queue_finished(self):
        done = sum(1 for it in self.queue if it.status == "done")
        failed = sum(1 for it in self.queue if it.status == "failed")
        self.progress.set(100 if self.queue else 0)
        msg = f"Queue done: {done} succeeded, {failed} failed."
        self.status_var.set(msg)
        if done > 0:
            self._show_success_banner(msg)

    def _process_item_individual(self, item, idx, from_queue=False):
        if yt_dlp is None:
            messagebox.showerror("Missing dependency", "yt-dlp is not installed.\nInstall it with: pip install yt-dlp")
            return
        item.status = "downloading"
        item.progress = 0.0
        self._refresh_queue_panel()
        self.download_btn.config(state="disabled", text="Downloading…")
        self.process_queue_btn.config(state="disabled")
        self.progress.set(0)
        self.status_var.set(f"Downloading: {item.title[:60]}…")

        def worker():
            try:
                saved_path, title = self._run_ydl(item)
                item.status = "done"
                item.saved_path = saved_path or ""
                item.title = title or item.title
                item.progress = 100.0
                self.root.after(0, self._add_recent, saved_path, title, item.url)
                self.root.after(0, self._on_item_success, idx, item, from_queue)
            except Exception as e:
                item.status = "failed"
                item.error_msg = str(e)[:200]
                self.root.after(0, self._on_item_error, idx, item, from_queue, str(e))

        self.download_thread = threading.Thread(target=worker, daemon=True)
        self.download_thread.start()

    def _run_ydl(self, item):
        audio_only = item.fmt.startswith("Audio")
        fmt_str = quality_to_format(item.quality, audio_only)

        def hook(d):
            if d["status"] == "downloading":
                downloaded = d.get("downloaded_bytes", 0) or 0
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total and total > 0:
                    pct = max(0.0, min(100.0, (downloaded / total) * 100.0))
                else:
                    pct = 0.0
                speed = d.get("speed")
                eta = d.get("eta")
                self.root.after(0, self._update_download_progress, pct, speed, eta, item)
            elif d["status"] == "finished":
                self.root.after(0, self.status_var.set, "Processing (merging/converting)…")

        ydl_opts = {
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [hook],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        if self.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path

        if audio_only:
            ydl_opts.update({
                "format": fmt_str,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        else:
            ydl_opts["format"] = fmt_str
            ydl_opts["merge_output_format"] = "mp4"

        if item.mode == "clip" and item.start_sec is not None and item.end_sec is not None:
            ydl_opts["download_ranges"] = lambda info, ydl, s=item.start_sec, e=item.end_sec: [{"start_time": s, "end_time": e}]
            ydl_opts["force_keyframes_at_cuts"] = True

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(item.url, download=True)
            title = info.get("title", item.url)
            requested = info.get("requested_downloads", [])
            if requested and requested[0].get("filepath"):
                final_path = requested[0]["filepath"]
            else:
                final_path = ydl.prepare_filename(info)
                if audio_only:
                    final_path = os.path.splitext(final_path)[0] + ".mp3"
            return final_path, title

    def _update_download_progress(self, pct, speed, eta, item):
        self.progress.set(pct)
        item.progress = pct
        if 0 <= self.current_queue_index < len(self.queue):
            self._update_queue_item_ui(self.current_queue_index)
        speed_txt = format_speed(speed)
        eta_txt = format_eta(eta)
        self.status_var.set(f"Downloading… {pct:.1f}%  {speed_txt}  ETA {eta_txt}")

    def _on_item_success(self, idx, item, from_queue):
        self.progress.set(100)
        item.progress = 100.0
        self._refresh_queue_panel()
        self.download_btn.config(state="normal", text="⬇  Download")
        self.process_queue_btn.config(state="normal")
        if from_queue:
            self.status_var.set(f"Done: {os.path.basename(item.saved_path)[:60]}")
            self.root.after(600, self._advance_queue)
        else:
            msg = f"✓ Downloaded: {os.path.basename(item.saved_path)[:60]}"
            self.status_var.set(msg)
            self._show_success_banner(msg)
            messagebox.showinfo("Success", "Download complete!")

    def _on_item_error(self, idx, item, from_queue, err_msg):
        self.progress.set(0)
        self._refresh_queue_panel()
        self.download_btn.config(state="normal", text="⬇  Download")
        self.process_queue_btn.config(state="normal")
        if from_queue:
            self.status_var.set(f"Failed: {err_msg[:80]}")
            self.root.after(500, self._advance_queue)
        else:
            self.status_var.set("Error occurred. See details.")
            messagebox.showerror("Download failed", err_msg[:800])

    # ---------- FFMPEG ----------
    def _ensure_ffmpeg_windows(self):
        self.status_var.set("Setting up ffmpeg (one-time, ~80MB)…")
        self.download_btn.config(state="disabled")
        self.process_queue_btn.config(state="disabled")

        def worker():
            try:
                def cb(pct):
                    self.root.after(0, lambda: self.progress.set(pct))
                path = download_ffmpeg_windows(progress_cb=cb)
                self.ffmpeg_path = path
                self.root.after(0, self._ffmpeg_ready)
            except Exception as e:
                self.root.after(0, self._ffmpeg_failed, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _ffmpeg_ready(self):
        self.progress.set(0)
        self.status_var.set("Ready.")
        self.download_btn.config(state="normal")
        self.process_queue_btn.config(state="normal")

    def _ffmpeg_failed(self, err):
        self.progress.set(0)
        self.status_var.set("Couldn't auto-install ffmpeg. Video/audio merging or clipping may fail.")
        self.download_btn.config(state="normal")
        self.process_queue_btn.config(state="normal")


BUILD_SCRIPT_CONTENT = r"""@echo off
REM ============================================================
REM  JustDownloadIT - One-time build script (run on Windows)
REM  This produces JustDownloadIT.exe which needs NO Python or yt-dlp
REM  installed on the end user's machine - just double-click it.
REM ============================================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python was not found. Install it from https://www.python.org/downloads/
    echo IMPORTANT: check "Add Python to PATH" during install, then re-run this script.
    pause
    exit /b 1
)

echo Installing build tools and dependencies...
python -m pip install --upgrade pip >nul
python -m pip install yt-dlp pyinstaller pillow

REM Bundle the app icon if it is next to this script (otherwise the .exe
REM falls back to PyInstaller's default icon).
set EXTRA=
if exist app_icon.ico set EXTRA=%EXTRA% --icon app_icon.ico
if exist ffmpeg_bin\ffmpeg.exe set EXTRA=%EXTRA% --add-binary "ffmpeg_bin\ffmpeg.exe;ffmpeg_bin"

if not exist app_icon.ico echo NOTE: app_icon.ico not found here - built .exe will use the default icon.
if not exist ffmpeg_bin\ffmpeg.exe echo NOTE: ffmpeg_bin\ffmpeg.exe not found - the built .exe will auto-download ffmpeg on first run.

echo Building JustDownloadIT.exe ...
pyinstaller --onefile --windowed --name JustDownloadIT %EXTRA% JustDownloadIT.py

echo.
echo ============================================================
echo Done! Your standalone app is at:  dist\JustDownloadIT.exe
echo You can copy just that one file anywhere and run it -
echo no Python, no pip, no yt-dlp install needed for end users.
echo ============================================================
pause
"""


def main():
    if "--make-build-script" in sys.argv:
        out_path = os.path.join(APP_DIR, "build_windows.bat")
        with open(out_path, "w", newline="\r\n") as f:
            f.write(BUILD_SCRIPT_CONTENT)
        print(f"Wrote {out_path}")
        print("Copy this .bat file next to JustDownloadIT.py on a Windows PC,")
        print("then double-click it to build a standalone JustDownloadIT.exe.")
        return

    root = tk.Tk()
    for base in (APP_DIR, BUNDLE_DIR):
        icon_path = os.path.join(base, "app_icon.ico")
        if os.path.isfile(icon_path):
            try:
                root.iconbitmap(icon_path)
            except Exception:
                pass
            break
    app = JustDownloadITApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
