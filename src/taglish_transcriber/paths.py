from __future__ import annotations

import os
import sys
import re
from datetime import datetime
from pathlib import Path

PORTABLE_HOME_ENV = "LIVE_SCRIBE_HOME"
LEGACY_PORTABLE_HOME_ENV = "TAGLISH_LIVE_SCRIBE_HOME"


def _mac_bundle_parent(executable: Path) -> Path | None:
    for parent in executable.parents:
        if parent.suffix.lower() == ".app":
            return parent.parent
    return None


def application_root() -> Path:
    """Return the portable folder used for models, settings, recordings, and exports."""
    override = (
        os.environ.get(PORTABLE_HOME_ENV, "").strip()
        or os.environ.get(LEGACY_PORTABLE_HOME_ENV, "").strip()
    )
    if override:
        return Path(override).expanduser().resolve()

    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        bundle_parent = _mac_bundle_parent(executable)
        if bundle_parent is not None:
            return bundle_parent
        return executable.parent

    return Path(__file__).resolve().parents[2]


APP_ROOT = application_root()
DATA_DIR = APP_ROOT / "data"
MODEL_DIR = APP_ROOT / "models"
EXPORT_DIR = APP_ROOT / "exports"
RECORDING_DIR = APP_ROOT / "recordings"
RECORDING_IN_PROGRESS_DIR = RECORDING_DIR / "In Progress"
RECORDING_FINAL_DIR = RECORDING_DIR / "Final Output"
SKILLS_DIR = APP_ROOT / "Skills"
KNOWLEDGE_DIR = APP_ROOT / "Knowledge"
DICTIONARY_DIR = APP_ROOT / "dictionary"
ENGINES_DIR = APP_ROOT / "engines"
CACHE_DIR = APP_ROOT / ".cache"
TEMP_DIR = CACHE_DIR / "temp"
HF_HOME_DIR = CACHE_DIR / "huggingface"
HF_XET_CACHE_DIR = HF_HOME_DIR / "xet"
HF_ASSETS_CACHE_DIR = HF_HOME_DIR / "assets"
XDG_CACHE_DIR = CACHE_DIR / "xdg" / "cache"
XDG_CONFIG_DIR = CACHE_DIR / "xdg" / "config"
XDG_DATA_DIR = CACHE_DIR / "xdg" / "data"
PYCACHE_DIR = CACHE_DIR / "pycache"
SETTINGS_FILE = DATA_DIR / "settings.json"
TOPIC_PROFILES_FILE = DATA_DIR / "topic_profiles.json"
HARDWARE_PROFILE_FILE = DATA_DIR / "hardware_profile.json"
FIRST_RUN_MARKER_FILE = DATA_DIR / ".first-run-complete"
SESSION_DATABASE_FILE = DATA_DIR / "sessions.sqlite3"
RECOVERY_FILE = DATA_DIR / "unfinished_session.json"

def configure_portable_environment() -> None:
    """Keep writable runtime state beside the portable application."""
    values = {
        "HF_HOME": HF_HOME_DIR,
        "HF_HUB_CACHE": HF_HOME_DIR / "hub",
        "HF_XET_CACHE": HF_XET_CACHE_DIR,
        "HF_ASSETS_CACHE": HF_ASSETS_CACHE_DIR,
        "XDG_CACHE_HOME": XDG_CACHE_DIR,
        "XDG_CONFIG_HOME": XDG_CONFIG_DIR,
        "XDG_DATA_HOME": XDG_DATA_DIR,
        "TMP": TEMP_DIR,
        "TEMP": TEMP_DIR,
        "TMPDIR": TEMP_DIR,
    }
    for name, path in values.items():
        os.environ[name] = str(path)

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    # Use the standard resumable Hub transfer path. Raising a cancellation
    # request from hf-xet progress callbacks can escape from its worker and
    # print a traceback even though Live Scribe handles the stop correctly.
    os.environ["HF_HUB_DISABLE_XET"] = "1"


configure_portable_environment()


def ensure_app_directories() -> None:
    try:
        for directory in (
            DATA_DIR,
            MODEL_DIR,
            EXPORT_DIR,
            RECORDING_DIR,
            RECORDING_IN_PROGRESS_DIR,
            RECORDING_FINAL_DIR,
            SKILLS_DIR,
            KNOWLEDGE_DIR,
            DICTIONARY_DIR,
            ENGINES_DIR,
            HF_HOME_DIR,
            HF_XET_CACHE_DIR,
            HF_ASSETS_CACHE_DIR,
            XDG_CACHE_DIR,
            XDG_CONFIG_DIR,
            XDG_DATA_DIR,
            PYCACHE_DIR,
            TEMP_DIR,
        ):
            directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            "The app folder is not writable. Extract the complete product folder "
            "to Documents, Desktop, or a writable USB drive, then start it again."
        ) from exc


def safe_filename_part(value: str, *, fallback: str = "live-scribe-recording") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip()
    cleaned = re.sub(r"\s+", "-", cleaned).strip("-.")
    return cleaned[:80] or fallback


def new_recording_path(title: str = "") -> Path:
    ensure_app_directories()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = safe_filename_part(title)
    return RECORDING_FINAL_DIR / f"{stamp}_{name}.wav"


def atomic_write_text(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
) -> None:
    """Write a small settings/data file through a same-folder temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding=encoding)
    temporary.replace(path)
