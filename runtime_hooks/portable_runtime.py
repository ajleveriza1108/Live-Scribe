from __future__ import annotations

import ctypes.util
import os
import sys
from pathlib import Path


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
