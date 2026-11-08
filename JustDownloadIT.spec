# -*- mode: python ; coding: utf-8 -*-
#
# Packaging config only - the application code is not modified by this file.
#
# This is an onedir build (EXE with exclude_binaries=True + COLLECT) instead of
# onefile, and UPX compression is disabled everywhere. Both are standard
# packaging choices that reduce heuristic / machine-learning false positives
# (e.g. Smart App Control, Trapmine "Suspicious.low.ml.score"); a packed single
# file that unpacks itself at runtime is a common trigger for such flags.
# Windowed mode, the embedded app_icon.ico and the bundled ffmpeg are kept.


a = Analysis(
    ['JustDownloadIT.py'],
    pathex=[],
    binaries=[('ffmpeg_bin/ffmpeg.exe', 'ffmpeg_bin')],
    datas=[('app_icon.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JustDownloadIT',
    icon='app_icon.ico',
    version='version_info.txt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='JustDownloadIT',
)
