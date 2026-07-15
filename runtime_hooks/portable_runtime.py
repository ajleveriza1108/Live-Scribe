from __future__ import annotations

import ctypes.util
import os
import sys
from pathlib import Path


def _mac_bundle_parent(executable: Path) -> Path | None:
    for parent in executable.parents:
        if parent.suffix.lower() == ".app":
            return parent.parent
    return None


def _portable_home() -> Path:
    override = os.environ.get("LIVE_SCRIBE_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    executable = Path(sys.executable).resolve()
    bundle_parent = _mac_bundle_parent(executable)
    if bundle_parent is not None:
        return bundle_parent
    return executable.parent


def _configure_portable_runtime() -> None:
    root = _portable_home()
    cache = root / ".cache"
    temp = cache / "temp"
    hf_home = cache / "huggingface"
    xdg = cache / "xdg"

    directories = (
        temp,
        hf_home / "hub",
        hf_home / "xet",
        hf_home / "assets",
        xdg / "cache",
        xdg / "config",
        xdg / "data",
        cache / "pycache",
    )
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    values = {
        "LIVE_SCRIBE_HOME": root,
        "HF_HOME": hf_home,
        "HF_HUB_CACHE": hf_home / "hub",
        "HF_XET_CACHE": hf_home / "xet",
        "HF_ASSETS_CACHE": hf_home / "assets",
        "XDG_CACHE_HOME": xdg / "cache",
        "XDG_CONFIG_HOME": xdg / "config",
        "XDG_DATA_HOME": xdg / "data",
        "TMP": temp,
        "TEMP": temp,
        "TMPDIR": temp,
    }
    for name, value in values.items():
        os.environ[name] = str(value)

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ["HF_HUB_DISABLE_XET"] = "1"


_configure_portable_runtime()


# python-sounddevice normally asks the operating system to locate PortAudio.
# Linux portable builds bundle libportaudio.so.2, so make that bundled copy
# discoverable before sounddevice is imported.
if sys.platform.startswith("linux") and getattr(sys, "frozen", False):
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    candidates = (
        bundle_root / "libportaudio.so.2",
        Path(sys.executable).resolve().parent / "_internal" / "libportaudio.so.2",
        Path(sys.executable).resolve().parent / "libportaudio.so.2",
    )
    bundled_portaudio = next((path for path in candidates if path.is_file()), None)
    if bundled_portaudio is not None:
        original_find_library = ctypes.util.find_library

        def portable_find_library(name: str):
            if name == "portaudio":
                return str(bundled_portaudio)
            return original_find_library(name)

        ctypes.util.find_library = portable_find_library
