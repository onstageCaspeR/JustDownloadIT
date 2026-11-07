# JustDownloadIT — YouTube Downloader GUI

A single-file, native Windows desktop app for downloading YouTube videos, audio, and timestamp clips. Built with Python + Tkinter + `yt-dlp` + `ffmpeg`.

## Screenshots

<img width="722" height="792" alt="main-window" src="https://github.com/user-attachments/assets/f64a5503-45fd-41ff-a332-f4f7e85fd67d" />


```
JustDownloadIT/
├── JustDownloadIT.py          # Single-file source (all logic + UI)
├── JustDownloadIT.spec        # PyInstaller spec (pre-configured)
├── installer.iss              # Inno Setup script for building the Windows installer
├── build_icon.py              # Script to generate app_icon.ico
├── app_icon.ico               # Application icon (used by shortcuts + installer)
├── requirements.txt           # Python dependencies (yt-dlp + pyinstaller)
├── validate_ui.py             # Run after edits: 31-check regression suite
├── .gitignore                 # Git exclusions (build artifacts, user state, binaries)
└── README.md                  # This file
```

> **ffmpeg.exe is NOT bundled in this repo** — the app auto-downloads it on first run on Windows, or you can place `ffmpeg.exe` in `ffmpeg_bin/` manually. See [Getting ffmpeg](#getting-ffmpeg) below. Build outputs (`build/`, `dist/`, `release_build/`, `installer_output/`, `release/`) are all excluded by `.gitignore`.

---

## Table of Contents

- [1. Quick Start (Run from Source)](#1-quick-start-run-from-source)
- [2. Getting ffmpeg](#2-getting-ffmpeg)
- [3. Build a Standalone .EXE (no Python needed for end users)](#3-build-a-standalone-exe-no-python-needed-for-end-users)
- [4. Build the Windows Installer (.Setup.exe)](#4-build-the-windows-installer-setupexe)
- [5. Pre-built Releases (GitHub Releases)](#5-pre-built-releases-github-releases)
- [6. App Features (How To Use)](#6-app-features-how-to-use)
- [7. Architecture (Single-File)](#7-architecture-single-file)
- [8. UI System & Theming Conventions (HARD RULES FOR DEVS)](#8-ui-system--theming-conventions-hard-rules-for-devs)
- [9. File Persistence (State / JSON files)](#9-file-persistence-state--json-files)
- [10. Known Issues + Future Risks](#10-known-issues--future-risks)
- [11. Validation / Regression Testing](#11-validation--regression-testing)
- [12. Disclaimer & Responsible Use](#12-disclaimer--responsible-use)

---

## 1. Quick Start (Run from Source)

Requires **Python 3.10+** (developed & tested on 3.13).

```bash
# 1. Clone / download this repo
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python JustDownloadIT.py
```

On first run on Windows, if `ffmpeg.exe` is not found on PATH or in `ffmpeg_bin/`, the app will **download it automatically**. See next section.

---

## 2. Getting ffmpeg

`ffmpeg` is required for merging video/audio DASH streams, MP3 extraction, and timestamp clip-cutting.

**Windows:**
- **Automatic (recommended):** On first launch, if `ffmpeg.exe` is missing, the app downloads `ffmpeg-release-essentials.zip` from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/), extracts only `ffmpeg.exe` into `ffmpeg_bin/`, and deletes the zip. ~80 MB one-time download.
- **Manual:** Download ffmpeg from the URL above and place `ffmpeg.exe` in a `ffmpeg_bin/` folder next to `JustDownloadIT.py` (or add it to your system `PATH`).

**Mac / Linux:**
- Install ffmpeg via your package manager: `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Ubuntu/Debian).

> ⚠️ **ffmpeg.exe is NOT committed to this repository** due to its size and separate licensing (ffmpeg is distributed under LGPL/GPL). The app handles acquisition for you.

---

## 3. Build a Standalone .EXE (no Python needed for end users)

First make sure you have `ffmpeg.exe` in `ffmpeg_bin/` (see [Getting ffmpeg](#2-getting-ffmpeg)).

### Option A — One-liner (recommended for this project):

```bash
pyinstaller --onefile --windowed --name JustDownloadIT --add-binary "ffmpeg_bin/ffmpeg.exe;ffmpeg_bin" JustDownloadIT.py
```

This produces **`dist\JustDownloadIT.exe`** (~53 MB). That one file is the entire app — it:
- Bundles Python runtime
- Bundles yt-dlp + all dependencies
- Bundles ffmpeg.exe (extracted into a per-launch temp dir via `_MEIPASS`)
- Uses `--windowed` (no console window pops up)

### Option B — Use the pre-built `JustDownloadIT.spec`:

```bash
pyinstaller JustDownloadIT.spec
```

Same output, uses the `.spec` file that was hand-tuned to bundle `ffmpeg_bin/ffmpeg.exe`.

### Option C — Self-generated build script (for sharing the build):

Give just `JustDownloadIT.py` to someone. On a Windows PC with Python:

```bash
python JustDownloadIT.py --make-build-script
```

This writes `build_windows.bat` next to the `.py` file. Double-click the `.bat` — it installs
`yt-dlp` + `pyinstaller` and runs the exact command above.

### Post-build manual verification checklist:

1. `dist\JustDownloadIT.exe` exists (size ≈ 50–70 MB)
2. Copy it to an empty folder on a **different machine without Python** (or to `standalone_test/` locally)
3. Double-click — window opens, no missing DLL / missing module errors
4. Paste any YouTube URL, click **Add**, then **Download** — it should find ffmpeg (from the bundle)

---

## 4. Build the Windows Installer (.Setup.exe)

Once you have a working `JustDownloadIT.exe` build, you can wrap it into a proper Windows installer using **Inno Setup**.

### Prerequisites:
- **Inno Setup 6** installed (download from [jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php))
- A working build at `release_build\dist\JustDownloadIT.exe` (copy it from `dist\` if you built it there)
- `app_icon.ico` in the project root (already included)

### Build steps:

```bash
# 1. (Optional) If you built to dist\, copy the EXE to release_build\dist\ first
mkdir -p release_build\dist
copy dist\JustDownloadIT.exe release_build\dist\JustDownloadIT.exe

# 2. Compile the installer using ISCC (Inno Setup Compiler)
#    Typical ISCC paths (use whichever exists):
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
# -- or --
"C:\Program Files\Inno Setup 6\ISCC.exe" installer.iss
```

This produces **`installer_output\JustDownloadIT-Setup.exe`**. The installer:
- Installs per-user to `%LOCALAPPDATA%\JustDownloadIT` (no admin rights required)
- Creates Desktop and Start Menu shortcuts using `app_icon.ico`
- Offers a "Launch JustDownloadIT" checkbox on the Finish page
- Adds an entry to Windows "Add/Remove Programs"

### Final release-ready setup.exe location:
Copy the compiled installer to `release\JustDownloadIT-Setup.exe` for upload to GitHub Releases.

---

## 5. Pre-built Releases (GitHub Releases)

Pre-built `JustDownloadIT-Setup.exe` installers are published on the [GitHub Releases page](https://github.com/onstageCaspeR/JustDownloadIT/releases). Users can download the installer and double-click to install; Python and build tools are not needed.

Installed Windows builds check the latest GitHub release at startup (at most once every 24 hours). If a newer version is found, the app asks before downloading or installing it. The installer download is checked against GitHub's SHA-256 asset digest or the release's `JustDownloadIT-Setup.exe.sha256` file. The update check sends no personal data. JustDownloadIT and all updates are free.

Users on builds older than `1.2.0` must install that first updater-enabled release manually; older builds have no code that can check for updates. Later releases can be offered automatically by `1.2.0` and newer installed builds.

For each release, use a semantic version tag such as `v1.2.0` and upload both:

- `JustDownloadIT-Setup.exe`
- `JustDownloadIT-Setup.exe.sha256` (the SHA-256 checksum of the exact installer)

Create the checksum in PowerShell after compiling the installer:

```powershell
(Get-FileHash .\release\JustDownloadIT-Setup.exe -Algorithm SHA256).Hash.ToLower() |
  Set-Content .\release\JustDownloadIT-Setup.exe.sha256 -NoNewline
```



---

## 6. App Features (How To Use)

| Feature | Location / How |
|---|---|
| Paste URL | URL field at top, or click **📋 Paste** |
| Full video download | Leave mode on **Full Video** (default) |
| Clip a segment (timestamp range) | Toggle **Timestamp Clip** mode, enter Start/End in `HH:MM:SS`, `MM:SS`, or seconds |
| Format choice | **Video (MP4)** or **Audio only (MP3)** (format dropdown) |
| Quality choice | Best, 2160p, 1440p, 1080p, 720p, 480p, 360p |
| Output folder | **Browse** under *Save to:* — defaults to `~/Downloads` |
| Single-download now | **⬇ Download** — adds URL to queue and starts |
| Batch queue | Add multiple via **＋ Add**, then **▶ Process Queue** |
| Remove queue item | Click **✕** on any queued/failed/skipped row |
| Remove all | **🗑 Clear** |
| Open file after download | **📂** icon appears to the right of a completed item row |
| History | *Recent Downloads* panel at bottom (last 5, persists) |
| ffmpeg setup (Windows) | Fully automatic on first run |

### How download processing works

1. `yt_dlp.YoutubeDL` downloads video + audio streams separately (for resolutions above ~720p, YouTube serves them as separate DASH streams).
2. `ffmpeg` merges them into a single `.mp4` file.
3. For MP3 mode, `ffmpeg` extracts audio to `.mp3` (192 kbps) via `FFmpegExtractAudio` post-processor.
4. For clips, `yt-dlp`'s `download_ranges` + `force_keyframes_at_cuts` sends the cut range to ffmpeg during the merge step.
5. Progress (%/speed/ETA) and status icons (⏸ queued / ⏳ downloading / ✓ done / ✕ failed / → skipped) update live in the queue list.

---

## 7. Architecture (Single-File)

Everything lives in **`JustDownloadIT.py`** — no imports of sibling Python modules.

### Top-level module structure

| Lines (approx) | Block | Purpose |
|---|---|---|
| 1–26 | Module docstring | Quick-start & build instructions for devs |
| 28–45 | Imports | `tkinter`, `yt_dlp`, threading, urllib, zipfile, shutil, … |
| 47–92 | Constants | Paths (`APP_DIR`, `FFMPEG_DIR`, `RECENT_FILE`), color palette, font tuples |
| 95–243 | Free functions | `find_ffmpeg`, `download_ffmpeg_windows`, `parse_timestamp`, `format_speed`, `format_eta`, `load_recent`, `save_recent`, `open_folder`, `quality_to_format`, `fetch_video_duration` |
| 245–431 | Custom widgets | `IceButton`, `RoundedPanel`, `RoundedEntry`, `IconButton`, `QualityCombobox`, `ProgressWithLabel`, `SuccessBanner` |
| 437–454 | Data class | `DownloadQueueItem` (dataclass-ish POJO, no decorator) |
| 530–1387 | Main app `JustDownloadITApp` | Constructor → `_setup_styles` → `_build_ui` → download/queue/ffmpeg methods |
| 1390–1418 | `BUILD_SCRIPT_CONTENT` | Inline heredoc for `build_windows.bat` (`--make-build-script`) |
| 1422–1442 | `main()` | CLI dispatch (build-script flag vs. Tk `mainloop()`) |

### Key state inside `JustDownloadITApp`

```python
self.queue               # list[DownloadQueueItem]
self.current_queue_index # int, position during Process Queue
self.is_processing_queue # bool
self.download_thread     # Thread running _process_item_individual worker
self.recent              # list[dict], loaded from justdownloadit_recent.json
self.output_dir          # str, user-chosen save path
self.ffmpeg_path         # str|None, resolved at __init__
self._queue_widgets      # dict idx -> {row, icon, title, sub, prog}
```

---

## 8. UI System & Theming Conventions (HARD RULES FOR DEVS)

**Violating these will produce invisible / squashed text — as the earlier bugs showed.**

### 8.1 Color palette (always use these constants, NEVER hardcode)

All user text color must still be pure black (`#000000`) per project preference.

| Constant | Value | Used for |
|---|---|---|
| `BLACK` | `#000000` | All user-facing text (title, subtitle, label, button caption) |
| `GRAY_SUBTITLE` | `#4a4a4a` | Queue-item metadata subtitle + recent-list file path (readably dark, NOT disabled gray) |
| `BG_BLACK` | `#eaf4ff` | App background (pale sky-blue, "ice" theme). Misleading name — keep for back-compat |
| `PANEL` / `PANEL_2` | `#eaf4ff` / `#ffffff` | Card backgrounds (header + card content layers) |
| `ICE_BLUE` | `#bfe3ff` | Active state for icon button hovers |
| `ACCENT` | `#3aa0ff` | Progress bars, combo arrow, IconButton foreground, status colors |
| `SUCCESS_DARK` / `ERROR_DARK` / `WARN` | — | Queue row status icon colors |
| `SHADOW_1` / `SHADOW_OFFSET=2` | — | Layered shadow in custom widgets |

### 8.2 Custom widgets — 2-layer (shadow/border) + inner

Every themed container in this app uses the same pattern because native Tkinter has zero shadow/border support:

```
Outer Frame  (owns the shadow/drop-shadow layer, bg=SHADOW_1)
   └── Body Frame  (owns the highlight background/border, bg+highlightthickness+highlightbackground)
         └── Your content
```

- `IceButton`, `RoundedPanel`, `RoundedEntry`, `IconButton`, `ProgressWithLabel`, `SuccessBanner` ALL do this.
- **When adding children, put them inside `.body`** (e.g. `form = RoundedPanel(parent)` → `fb = form.body` → children go in `fb`).
- **The inner button in `IceButton` / `IconButton` MUST call `pack(fill="both", expand=True, padx=(0, SHADOW_OFFSET), pady=(0, SHADOW_OFFSET))`** — the offset creates the shadow illusion. If you forget `fill="both"` + `expand=True`, the button won't fill its container (see the Download-Button-narrow-inside-gray-bar bug).

### 8.3 Borders around text rows/labels

**DO NOT put `highlightthickness` directly on a `tk.Label`.** Tk draws the highlight *inside* the widget, stealing space from the text. Use this pattern:

```python
# WRONG: border on label  ->  text touches the border edges
tk.Label(..., pady=10, highlightthickness=2)

# RIGHT: border on outer Frame, label inside padding
wrap = tk.Frame(parent, bg=PANEL_2,
                highlightbackground=BORDER, highlightthickness=BORDER_THICK)
wrap.pack(fill="x")
tk.Label(wrap, text="...", padx=60, pady=90).pack(fill="both", expand=True)
```

This is applied to:
- Empty-state boxes (queue empty, recent empty) — see `q_empty_wrap` / `r_empty_wrap`
- Queue item rows / Recent rows — use `row` outer + `inner` inner (`padx=18, pady=28`/`24`)

### 8.4 IconButton foreground

`IconButton` foreground must be **`ACCENT`** (blue `#3aa0ff`), never `BLACK`. The button's background is `BG_BLACK` (also near-ice) so black-on-blue is **invisible** until hover — that was the original "invisible folder icon" bug. Confirmed via live validation:

```
IconButton fg=#3aa0ff bg=#eaf4ff   ->   100% contrast, visible always
```

### 8.5 Queue row labels: no accidental `state="disabled"`

A `tk.Label` with `state="disabled"` under some Windows themes renders in a grayed, etched style. **Always explicitly set `state="normal"`** on queue item title/subtitle/Recent labels even though it's the default — this is a defense against future copy-paste bugs. Pair it with:
- Title = `font=("Segoe UI", 10, "bold"), fg=BLACK` (solid bold black — maximum legibility)
- Subtitle = `font=FONT_LABEL ("Segoe UI 10 regular"), fg=GRAY_SUBTITLE`

---

## 9. File Persistence (State / JSON files)

### `justdownloadit_recent.json`

Location: same folder as `JustDownloadIT.py` or the `.exe`.

Shape:
```json
[
  {
    "path":  "C:/Users/aarav/Downloads/MyVideo.mp4",
    "title": "My Video Title",
    "url":   "https://www.youtube.com/watch?v=J6UTG09xko4",
    "ts":    1756818042.461
  }
]
```
- Capped at the **last 5 entries**.
- Written on every successful download; loaded at startup.

### No settings file yet

The original `icedown_settings.json` is a leftover from older versions and is **not** used by `JustDownloadIT`. Currently `default_format` / `default_quality` / `output_dir` are constants/one-time `__init__` values — if you add a Settings dialog, use `justdownloadit_settings.json` for symmetry.

---

## 10. Known Issues + Future Risks

### CURRENT (as of this build)

1. **`yt-dlp` site-extractor drift (MEDIUM)**
   - YouTube changes its response formats, cipher signatures, and endpoints regularly.
   - **Mitigation**: publish a new release built against a current `yt-dlp`; the installed app checks GitHub Releases and offers the free app update at startup.

2. **ffmpeg Windows URL hard-coded (LOW)**
   - `FFMPEG_WIN_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"` — if gyan.dev reorganizes their build archive, the first-time auto-download breaks on fresh Windows installs.
   - **Mitigation**: already bundled inside the `.exe` via `--add-binary`, so only end-users running from source (pip install) are affected. Add a fallback mirror or catch the HTTP error and show a download link in a messagebox.

3. **One-file PyInstaller cold-start (INFO)**
   - `--onefile` extracts ~140 MB of runtime to a temp `_MEIxxxxxx` folder on every launch. This is normal but feels slow on old HDDs (2–6 seconds).
   - Alternative is `--onedir` with a WiX/InnoSetup installer, but the project requirement was single-EXE portability.

4. **Windows Defender / SmartScreen false positive (LOW)**
   - Unsigned `.exe` files from PyInstaller trigger reputation-based AV warnings.
   - If distributing broadly: buy a code-signing cert (DigiCert/Sectigo OV, ~$70/yr), sign with `signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 dist\JustDownloadIT.exe`.

5. **Clip end-time fetch uses synchronous `extract_info` on the UI thread**
   - If the user only enters a *Start* time but no *End* time, `_add_to_queue` calls `fetch_video_duration` *synchronously*. For long videos or slow connections, the UI freezes for 1–5s.
   - Fix candidate: move the probe to a daemon thread + disable Add button until probe returns; show "Fetching duration…" in status_var.

6. **No playlist support**
   - `noplaylist=True` is hard-coded in ydl_opts and the URL parser. Users expect pasting a `?list=` URL to either download the whole list or show "use individual video URLs" — right now it silently picks only the first.
   - Future work: parse list URLs, add playlist header + per-video rows; strip the list param when fetching.

7. **Tk emoji rendering inconsistency across Windows versions**
   - 📄 🕒 📂 ✕ etc. use `Segoe UI Symbol` font. Older Windows 10 builds may render tofu boxes for newer codepoints.
   - Fallback: ship small PNG icons instead when this surfaces.

8. **`BORDER_THICK = 2` doubled on adjacent rows**
   - When two 1px-border rows stack, there is a 2px-looking seam between them because each row draws its own border. Use `highlightthickness=(1,1,1,0)` equivalent or only draw top-border except the first row if it ever becomes a visual issue.

### BUILD / CI RISKS

9. **`yt_dlp.__pyinstaller` hook optional deps**
   - The PyInstaller log during build reports `collect_data_files` warnings for `curl_cffi` and `yt_dlp_ejs`. These are warnings today but can become errors if a future yt-dlp hook treats them as required. When bumping yt-dlp, re-run the build and watch for ERROR-level messages.

10. **Python 3.13+ `tkinter` changes**
    - Python 3.13 already showed slight Tk init differences; `root.iconbitmap(default="")` is wrapped in try/except for that reason. When a new Python ships, always re-run the full `validate_ui.py`.

---

## 11. Validation / Regression Testing

Every UI/styling change must pass:

```bash
python validate_ui.py
```

This runs **31 checks** covering:
- No leftover `IceDown` references (rename integrity)
- `IconButton` fg is `ACCENT` & contrasts its `BG_BLACK` bg
- Queue/recent empty boxes use 2-layer pattern with `pady=90`
- Queue/recent item rows use 2-layer pattern with `inner pady=28/24`
- All title/subtitle labels have `state="normal"`, subtitle uses `GRAY_SUBTITLE`
- EXE exists and is the right size order-of-magnitude
- `_MEIPASS` / ffmpeg bundled path resolution is present in source
- **Live Tkinter probe** — actually instantiates the app, creates an IconButton, and inspects actual widget cget() values
- Adds a dummy queue item and inspects the dynamic-refresh padding

Expected output: `RESULT: 31/31 checks passed  ALL CHECKS PASSED ✓`

Additionally a machine-readable `validation_report.json` is written next to the script with individual statuses and detail strings — useful for pasting into PR comments or CI logs.

### Manual spot-check list after any build

1. ✅ App window shows "JustDownloadIT" as title and header
2. ✅ Remove/✕ icon on queue items is visible before hovering (NOT black-on-black)
3. ✅ Folder 📂 icon on completed recent items is visible before hovering
4. ✅ Empty "Queue is empty" box has massive white space **inside** the border above/below text, not text-touching
5. ✅ A real URL added to the queue shows title + metadata with the title in solid **bold black**, subtitle gray, progress bar below, nothing touches the top/bottom black line of the row
6. ✅ Run a download of a short YouTube video to confirm ffmpeg merge + saved path works end-to-end
7. ✅ Close the app, re-open — Recent Downloads panel still shows the item (JSON round-trip OK)

---

## 12. Disclaimer & Responsible Use

JustDownloadIT is a personal utility tool intended for lawful, offline use.

- **Respect copyrights:** Only download content you own, have explicit permission to download, or is in the public domain. Many creators on YouTube earn a living from views — downloading their work without permission deprives them of revenue and may violate their rights.

- **Respect YouTube's Terms of Service:** Downloading content from YouTube may violate YouTube's Terms of Service (ToS). This tool is provided for educational and personal use. Review [YouTube's Terms of Service](https://www.youtube.com/static?template=terms) and applicable laws in your jurisdiction before using this software.

- **No warranty:** This software is provided "as-is" without any warranty of any kind. The authors are not responsible for any copyright infringement claims, account bans, or other consequences arising from misuse.

Use this tool responsibly. When in doubt, don't download — use YouTube's own offline-viewing features or support the creator directly.
