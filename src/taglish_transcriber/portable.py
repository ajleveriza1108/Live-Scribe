from __future__ import annotations

import ctypes
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .paths import APP_ROOT, TEMP_DIR, ensure_app_directories


MIB = 1024**2
PORTABLE_TEST_BYTES = 32 * MIB

STORAGE_GOOD = "good"
STORAGE_USABLE = "usable"
STORAGE_SLOW = "slow"
STORAGE_NOT_TESTED = "not tested"
STORAGE_UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class PortableStorageReport:
    app_root: str
    drive_kind: str
    likely_removable: bool
    likely_external: bool
    write_mbps: float | None
    performance: str
    note: str

    @property
    def is_slow(self) -> bool:
        return self.performance == STORAGE_SLOW

    def summary(self) -> str:
        parts = ["Portable folder", self.drive_kind]
        if self.write_mbps is not None:
            parts.append(f"quick write {self.write_mbps:.1f} MB/s")
        else:
            parts.append("speed not tested")
        return "  •  ".join(parts)


def classify_write_speed(write_mbps: float | None) -> tuple[str, str]:
    if write_mbps is None:
        return (
            STORAGE_NOT_TESTED,
            "Portable storage speed was not tested during this startup. "
            "Open Models and choose Check This PC Again to run the quick test.",
        )
    if write_mbps >= 30.0:
        return (
            STORAGE_GOOD,
            "The quick storage test is suitable for portable use. Model startup can "
            "still be slower than an internal SSD.",
        )
    if write_mbps >= 10.0:
        return (
            STORAGE_USABLE,
            "The portable drive is usable, but model downloads and initial model loading "
            "may take longer than on an internal SSD.",
        )
    return (
        STORAGE_SLOW,
        "Slow portable storage was detected. Live transcription may still work after the "
        "model loads, but downloads, startup, WAV verification, and exports can pause. "
        "Use Compact or move Live Scribe to a faster USB 3.x drive or portable SSD.",
    )


def _windows_drive_kind(path: Path) -> tuple[str, bool, bool]:
    # GetDriveTypeW identifies the Windows volume category. Some USB SSDs are
    # reported as fixed drives, so "fixed" does not prove the drive is internal.
    drive_root = path.anchor or str(path)
    if not drive_root.endswith("\\"):
        drive_root += "\\"
    try:
        get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
        get_drive_type.argtypes = [ctypes.c_wchar_p]
        get_drive_type.restype = ctypes.c_uint
        drive_type = int(get_drive_type(drive_root))
    except Exception:
        return "Drive type unknown", False, False

    labels = {
        0: "Drive type unknown",
        1: "Invalid drive path",
        2: "Removable drive",
        3: "Fixed or external SSD",
        4: "Network drive",
        5: "Optical drive",
        6: "RAM drive",
    }
    return (
        labels.get(drive_type, "Drive type unknown"),
        drive_type == 2,
        drive_type in {2, 4},
    )


def _posix_drive_kind(path: Path) -> tuple[str, bool, bool]:
    resolved = str(path.resolve())
    if sys.platform == "darwin" and resolved.startswith("/Volumes/"):
        return "Mounted external volume", True, True
    external_prefixes = ("/media/", "/run/media/", "/mnt/")
    if resolved.startswith(external_prefixes):
        return "Mounted external or removable volume", True, True
    return "Local or externally mounted drive", False, False


def detect_drive_kind(path: Path = APP_ROOT) -> tuple[str, bool, bool]:
    if sys.platform == "win32":
        return _windows_drive_kind(path)
    return _posix_drive_kind(path)


def quick_write_test(
    directory: Path = TEMP_DIR,
    *,
    total_bytes: int = PORTABLE_TEST_BYTES,
) -> float | None:
    """Perform a small sequential write test and return approximate MB/s.

    This is deliberately a quick advisory test, not a full storage benchmark.
    """
    ensure_app_directories()
    directory.mkdir(parents=True, exist_ok=True)
    test_path = directory / ".portable-storage-speed-test.bin"
    block = bytes(MIB)
    remaining = max(MIB, int(total_bytes))

    try:
        started = time.perf_counter()
        with test_path.open("wb", buffering=0) as handle:
            while remaining > 0:
                chunk = block if remaining >= len(block) else block[:remaining]
                handle.write(chunk)
                remaining -= len(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        elapsed = max(0.001, time.perf_counter() - started)
        return (max(MIB, int(total_bytes)) / MIB) / elapsed
    except OSError:
        return None
    finally:
        try:
            test_path.unlink(missing_ok=True)
        except OSError:
            pass


def assess_portable_storage(
    *,
    run_speed_test: bool = False,
    app_root: Path = APP_ROOT,
) -> PortableStorageReport:
    drive_kind, likely_removable, likely_external = detect_drive_kind(app_root)
    write_mbps = quick_write_test() if run_speed_test else None
    performance, note = classify_write_speed(write_mbps)

    if drive_kind == "Network drive":
        note = (
            "A network drive was detected. Live Scribe is designed for a local folder, "
            "USB flash drive, or portable SSD. Network interruptions can damage recordings "
            "or partial model downloads. "
            + note
        )
    elif likely_removable:
        note = (
            "Portable or removable storage was detected. Keep the entire Live Scribe "
            "folder together and safely eject the drive only after the app has closed. "
            + note
        )
    else:
        note = (
            "Live Scribe is using its own application folder for settings, models, "
            "recordings, exports, caches, and temporary files. "
            + note
        )

    return PortableStorageReport(
        app_root=str(app_root),
        drive_kind=drive_kind,
        likely_removable=likely_removable,
        likely_external=likely_external,
        write_mbps=write_mbps,
        performance=performance,
        note=note,
    )


def cleanup_stale_temp_files(
    directory: Path = TEMP_DIR,
    *,
    older_than_days: int = 7,
) -> int:
    """Remove abandoned portable temp files without touching model downloads."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0

    cutoff = time.time() - max(1, older_than_days) * 86400
    removed = 0
    for child in directory.iterdir():
        try:
            if child.stat().st_mtime >= cutoff:
                continue
            if child.is_dir():
                import shutil

                shutil.rmtree(child)
            else:
                child.unlink()
            removed += 1
        except OSError:
            continue
    return removed
