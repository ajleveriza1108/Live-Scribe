from __future__ import annotations

import os
import sys
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
SKILLS_DIR = APP_ROOT / "Skills"
KNOWLEDGE_DIR = APP_ROOT / "Knowledge"
DICTIONARY_DIR = APP_ROOT / "dictionary"
ENGINES_DIR = APP_ROOT / "engines"
CACHE_DIR = APP_ROOT / ".cache"
TEMP_DIR = CACHE_DIR / "temp"
HF_HOME_DIR = CACHE_DIR / "huggingface"
SETTINGS_FILE = DATA_DIR / "settings.json"
TOPIC_PROFILES_FILE = DATA_DIR / "topic_profiles.json"
HARDWARE_PROFILE_FILE = DATA_DIR / "hardware_profile.json"

# Keep model downloads and Hugging Face cache inside the portable folder.
os.environ.setdefault("HF_HOME", str(HF_HOME_DIR))
os.environ.setdefault("HF_HUB_CACHE", str(HF_HOME_DIR / "hub"))


def ensure_app_directories() -> None:
    try:
        for directory in (
            DATA_DIR,
            MODEL_DIR,
            EXPORT_DIR,
            RECORDING_DIR,
            SKILLS_DIR,
            KNOWLEDGE_DIR,
            DICTIONARY_DIR,
            ENGINES_DIR,
            HF_HOME_DIR,
            TEMP_DIR,
        ):
            directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            "The app folder is not writable. Extract the complete product folder "
            "to Documents, Desktop, or a writable USB drive, then start it again."
        ) from exc


def new_recording_path() -> Path:
    ensure_app_directories()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return RECORDING_DIR / f"live-scribe-recording_{stamp}.wav"
