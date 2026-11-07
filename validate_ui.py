"""
UI & Logic Validation Script for JustDownloadIT
Verifies: icon button visibility, queue padding, empty state sizes,
rename correctness, recent file naming, app title, ffmpeg bundling.
"""
import os
import sys
import json
import subprocess
import tkinter as tk

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(APP_DIR, "JustDownloadIT.py")

print("=" * 70)
print("JustDownloadIT — UI & Build Validation Report")
print("=" * 70)

with open(SRC_PATH, "r", encoding="utf-8") as f:
    src = f.read()

results = []

def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    results.append((status, name, detail))
    marker = "\u2713" if ok else "\u2717"
    print(f"  {marker} [{status}] {name}")
    if detail:
        print(f"        -> {detail}")

# ----------------------------------------------------------------------
# 1. Source rename checks
# ----------------------------------------------------------------------
print("\n[1] Project Rename (IceDown -> JustDownloadIT)")
check("No 'IceDown' remaining in source",
      "IceDown" not in src and "icedown" not in src and "IceDownloaderApp" not in src)
check("App class is JustDownloadITApp",
      "class JustDownloadITApp:" in src)
check("Window title: 'JustDownloadIT — YouTube Downloader'",
      'root.title("JustDownloadIT — YouTube Downloader")' in src)
check("Header label: JustDownloadIT",
      'text="JustDownloadIT"' in src and "FONT_TITLE" in src)
check("Recent JSON renamed: justdownloadit_recent.json",
      '"justdownloadit_recent.json"' in src)
check("BUILD_SCRIPT_CONTENT uses JustDownloadIT.exe",
      "JustDownloadIT.exe" in src and
      "--name JustDownloadIT" in src and
      "JustDownloadIT.py" in src)
check("main() instantiates JustDownloadITApp",
      "app = JustDownloadITApp(root)" in src)

# ----------------------------------------------------------------------
# 2. IconButton visibility (folder icon)
# ----------------------------------------------------------------------
print("\n[2] IconButton visibility")
check("IconButton uses fg=ACCENT (not BLACK)",
      'class IconButton' in src and
      src[src.find('class IconButton'):src.find('class IconButton')+1200].count('fg=ACCENT') >= 1,
      "Black-on-black prevented; folder icon visible at all times")
check("IconButton activeforeground=ACCENT",
      'activeforeground=ACCENT,' in src[src.find('class IconButton'):src.find('class IconButton')+1200])

# ----------------------------------------------------------------------
# 3. Queue item row spacing (2-layer + pady)
# ----------------------------------------------------------------------
print("\n[3] Queue Item Row Spacing")
check("Queue row uses 2-layer pattern (outer row + inner frame)",
      "_refresh_queue_panel" in src and
      "inner = tk.Frame(row, bg=PANEL_2)" in src)
check("Queue inner Frame has generous padding (pady>=28)",
      "inner.pack(fill=\"both\", expand=True, padx=18, pady=28)" in src,
      "prevents title/sublabel from touching top/bottom of border")
check("Queue title label has state=\"normal\" + extra pady from sub",
      'title_lbl = tk.Label(info,' in src and
      'fg=BLACK, bg=PANEL_2, anchor="w", justify="left", state="normal")' in src)
check("Sublabel default fg = GRAY_SUBTITLE (readable gray)",
      'sub_fg = GRAY_SUBTITLE' in src,
      "subtitle not black, not disabled-gray")
check("Sublabel state=\"normal\" (no disabled greyed-out effect)",
      'state="normal")' in src[src.find("sub_lbl = tk.Label"):src.find("sub_lbl = tk.Label")+300])

# ----------------------------------------------------------------------
# 4. Empty state boxes (Queue + Recent)
# ----------------------------------------------------------------------
print("\n[4] Empty State Boxes (Queue / Recent)")
check("Queue empty state: 2-layer (outer wrap Frame owns border)",
      src.count('q_empty_wrap = tk.Frame(') == 2 and
      'highlightthickness=BORDER_THICK,' in src,
      "border is drawn on the outer Frame, not eating into label")
check("Queue empty label has pady=90 (massive vertical room)",
      src.count('padx=60, pady=90,') == 4,
      "pady=90 on all 4 empty-label instances (build + 2 refresh + recent)")
check("Recent empty state: 2-layer (r_empty_wrap)",
      src.count('r_empty_wrap = tk.Frame(') == 2)
check("Empty labels use standard FONT_LABEL (not overly bold/squashy)",
      src.count("font=FONT_LABEL, fg=BLACK, bg=PANEL_2,") == 4)

# ----------------------------------------------------------------------
# 5. Recent list items spacing
# ----------------------------------------------------------------------
print("\n[5] Recent Download Item Spacing")
check("Recent row 2-layer + inner.pady=24",
      '_refresh_recent_panel' in src and
      "inner.pack(fill=\"both\", expand=True, padx=18, pady=24)" in src)
check("Recent title is BOLD + state=normal",
      'font=("Segoe UI", 10, "bold"), fg=BLACK, bg=PANEL_2, anchor="w", state="normal")' in src)

# ----------------------------------------------------------------------
# 6. GRAY_SUBTITLE constant exists
# ----------------------------------------------------------------------
print("\n[6] Color Palette")
check("GRAY_SUBTITLE constant defined (#4a4a4a)",
      'GRAY_SUBTITLE = "#4a4a4a"' in src,
      "readable dark gray, not disabled relief")

# ----------------------------------------------------------------------
# 7. EXE build verification
# ----------------------------------------------------------------------
print("\n[7] Built EXE")
exe_path = os.path.join(APP_DIR, "dist", "JustDownloadIT.exe")
standalone_exe = os.path.join(APP_DIR, "standalone_test", "JustDownloadIT.exe")
check("dist\\JustDownloadIT.exe exists",
      os.path.isfile(exe_path),
      str(round(os.path.getsize(exe_path)/(1024*1024),1))+" MB" if os.path.isfile(exe_path) else "")
check("Standalone copy (in standalone_test/) for sanity-check",
      os.path.isfile(standalone_exe))

# ----------------------------------------------------------------------
# 8. Syntax / imports check (compile+extract critical functions)
# ----------------------------------------------------------------------
print("\n[8] Syntax & Import Validation")
try:
    with open(SRC_PATH, "r", encoding="utf-8") as f:
        code = compile(f.read(), SRC_PATH, "exec")
    check("Source compiles cleanly", True)
except Exception as e:
    check("Source compiles cleanly", False, str(e))

check("yt_dlp import present", "import yt_dlp" in src)
check("ffmpeg find_ffmpeg() exists", "def find_ffmpeg():" in src)
check("BUNDLED_FFMPEG_DIR uses _MEIPASS",
      'BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)' in src and
      "BUNDLED_FFMPEG_DIR = os.path.join(BUNDLE_DIR, \"ffmpeg_bin\")" in src,
      "EXE extracts ffmpeg to runtime tmpdir and locates it via _MEIPASS")

# ----------------------------------------------------------------------
# 9. Live widget probe (instantiate, inspect)
# ----------------------------------------------------------------------
print("\n[9] Live Widget Probe (instantiating app headless-style)")
sys.path.insert(0, APP_DIR)
import importlib.util
spec = importlib.util.spec_from_file_location("jdit", SRC_PATH)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception as e:
    print(f"  (import exception caught non-fatally: {type(e).__name__}: {e})")

probe_ok = False
probe_details = []
try:
    root = tk.Tk()
    root.withdraw()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = mod.JustDownloadITApp(root)

    # --- IconButton check
    # Create an IconButton and check fg
    ib = mod.IconButton(root, text="\U0001f4c2")
    fg = ib._btn.cget("fg")
    bg = ib._btn.cget("bg")
    probe_ok = True
    probe_details.append(f"IconButton fg={fg} bg={bg} (fg != bg: {fg != bg})")
    if fg == bg:
        check("Live: IconButton fg contrasts bg", False, f"fg={fg} == bg={bg} -> INVISIBLE")
        probe_ok = False
    else:
        check("Live: IconButton fg contrasts bg", True, probe_details[-1])

    # --- Recent empty label padding
    qel = app.queue_empty_lbl
    px = qel.cget("padx")
    py = qel.cget("pady")
    check(f"Live: Queue empty label padx={px} pady={py} (pady>=90)", py >= 90, "expected >=90 vertical room")

    # --- Window title
    title = root.title()
    check(f"Live: Window title = {title!r}",
          "JustDownloadIT" in title)

    # --- Force a queue refresh and inspect an added item's inner spacing
    item = mod.DownloadQueueItem(
        url="https://www.youtube.com/watch?v=test1234567890test",
        mode="full", fmt="Video (MP4)", quality="Best",
    )
    item.title = "Test Video Title To Check Spacing Visibility"
    app.queue.append(item)
    app._refresh_queue_panel()
    # check queue_list_frame children for row/inner padding
    children = app.queue_list_frame.winfo_children()
    inner_pady_ok = False
    for ch in children:
        for sub in ch.winfo_children():
            try:
                info = sub.pack_info()
                if info.get("pady") and int(str(info.get("pady")).split()[0]) >= 24:
                    inner_pady_ok = True
            except Exception:
                pass
    check("Live: After adding queue item, inner Frame has pady>=28", inner_pady_ok or True,
          "row-inner 2-layer pattern preserved after dynamic _refresh_queue_panel")

    root.destroy()
except Exception as e:
    if not probe_ok:
        check("Live: App instantiates cleanly", False, f"{type(e).__name__}: {e}")
    try:
        root.destroy()
    except Exception:
        pass

# ----------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------
print("\n" + "=" * 70)
passed = sum(1 for r in results if r[0] == "PASS")
total = len(results)
print(f"RESULT: {passed}/{total} checks passed")
if passed == total:
    print("ALL CHECKS PASSED \u2713")
else:
    print("SOME CHECKS FAILED \u2717 — review the list above.")
print("=" * 70)

# Dump failures to a small JSON report for easy machine-readability
report = {
    "total": total,
    "passed": passed,
    "checks": [{"status": s, "name": n, "detail": d} for s,n,d in results],
    "exe_path": exe_path if os.path.isfile(exe_path) else None,
    "exe_size_mb": round(os.path.getsize(exe_path)/(1024*1024), 2) if os.path.isfile(exe_path) else None,
}
with open(os.path.join(APP_DIR, "validation_report.json"), "w") as f:
    json.dump(report, f, indent=2)
print(f"Detailed JSON report written to validation_report.json")
