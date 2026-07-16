# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

import ctypes.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, copy_metadata

ROOT = Path(SPECPATH)
APP_NAME = "LiveScribe"

datas = []
binaries = []
hiddenimports = []

for package in (
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "av",
    "onnxruntime",
    "sounddevice",
    "soundcard",
    "customtkinter",
    "_sounddevice_data",
    "docx",
    "lxml",
):
    try:
        package_datas, package_binaries, package_hidden = collect_all(package)
        datas += package_datas
        binaries += package_binaries
        hiddenimports += package_hidden
    except Exception:
        pass

for distribution in (
    "faster-whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface-hub",
    "av",
    "onnxruntime",
    "sounddevice",
    "SoundCard",
    "customtkinter",
    "python-docx",
    "lxml",
):
    try:
        datas += copy_metadata(distribution)
    except Exception:
        pass


def linux_portaudio_path() -> str | None:
    if not sys.platform.startswith("linux"):
        return None
    try:
        output = subprocess.check_output(["ldconfig", "-p"], text=True, errors="ignore")
        for line in output.splitlines():
            if "libportaudio.so.2" in line and "=>" in line:
                candidate = line.split("=>", 1)[1].strip()
                if os.path.isfile(candidate):
                    return candidate
    except Exception:
        pass
    for candidate in (
        "/usr/lib/x86_64-linux-gnu/libportaudio.so.2",
        "/usr/lib/aarch64-linux-gnu/libportaudio.so.2",
        "/usr/lib64/libportaudio.so.2",
        "/usr/lib/libportaudio.so.2",
    ):
        if os.path.isfile(candidate):
            return candidate
    return None


portaudio = linux_portaudio_path()
if portaudio:
    binaries.append((portaudio, "."))

analysis = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "runtime_hooks" / "portable_runtime.py")],
    excludes=["matplotlib", "pandas", "scipy", "torch", "tensorflow"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(
        collection,
        name="Live Scribe.app",
        icon=None,
        bundle_identifier="com.ajleveriza.livescribe",
        info_plist={
            "NSMicrophoneUsageDescription": (
                "Live Scribe needs audio-input access to transcribe microphones and routed livestream audio."
            ),
            "CFBundleShortVersionString": "0.8.1",
            "CFBundleVersion": "0.8.1",
        },
    )
