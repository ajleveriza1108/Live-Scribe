from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .paths import (
    FIRST_RUN_MARKER_FILE,
    HARDWARE_PROFILE_FILE,
    SETTINGS_FILE,
    atomic_write_text,
    ensure_app_directories,
)


MODEL_PLACEHOLDER = "Choose speech quality…"

MODEL_CATALOG: dict[str, dict[str, str | int]] = {
    "small": {
        "name": "Compact",
        "size": "about 486 MB",
        "short": "Fastest download and lowest computer load",
        "description": (
            "Best for first tests, shorter recordings, and older computers. "
            "It is the quickest option but may miss more names and uncommon words."
        ),
        "bytes": 486_000_000,
    },
    "medium": {
        "name": "Balanced",
        "size": "about 1.53 GB",
        "short": "Good accuracy, especially when using CPU",
        "description": (
            "A stronger accuracy option for computers without a powerful graphics card. "
            "It uses more memory and processes speech more slowly than Compact."
        ),
        "bytes": 1_530_000_000,
    },
    "large-v3-turbo": {
        "name": "Best Overall",
        "size": "about 1.62 GB",
        "short": "Recommended balance of speed and accuracy",
        "description": (
            "Recommended for most buyers with a capable modern computer. "
            "It is designed to be much faster than Maximum Accuracy with only a small quality trade-off."
        ),
        "bytes": 1_620_000_000,
    },
    "large-v3": {
        "name": "Maximum Accuracy",
        "size": "about 3.09 GB",
        "short": "Highest quality, largest download, slowest processing",
        "description": (
            "Use when transcription quality matters more than speed. "
            "A stronger computer or compatible NVIDIA graphics card is recommended."
        ),
        "bytes": 3_090_000_000,
    },
}

MODEL_OPTIONS = tuple(MODEL_CATALOG)


def model_display_label(model_name: str) -> str:
    details = MODEL_CATALOG.get(model_name)
    if not details:
        return MODEL_PLACEHOLDER
    return f"{details['name']}  •  {details['size']}"


def model_friendly_name(model_name: str) -> str:
    details = MODEL_CATALOG.get(model_name)
    return str(details["name"]) if details else "Speech model"


def model_size_label(model_name: str) -> str:
    details = MODEL_CATALOG.get(model_name)
    return str(details["size"]) if details else "Unknown size"


def model_short_description(model_name: str) -> str:
    details = MODEL_CATALOG.get(model_name)
    return str(details["short"]) if details else "Choose a speech quality option."


def model_long_description(model_name: str) -> str:
    details = MODEL_CATALOG.get(model_name)
    return str(details["description"]) if details else "Choose a speech quality option."


MODEL_DISPLAY_TO_ID = {
    model_display_label(model_name): model_name for model_name in MODEL_OPTIONS
}
MODEL_SELECTION_OPTIONS = (MODEL_PLACEHOLDER, *MODEL_DISPLAY_TO_ID)


def model_id_from_display(value: str) -> str:
    clean = value.strip()
    if clean in MODEL_OPTIONS:
        return clean
    return MODEL_DISPLAY_TO_ID.get(clean, "")


AUDIO_SOURCE_MICROPHONE = "Microphone"
AUDIO_SOURCE_SYSTEM = "Computer audio / livestream"
AUDIO_SOURCE_OPTIONS = (AUDIO_SOURCE_MICROPHONE, AUDIO_SOURCE_SYSTEM)

LANGUAGE_AUTO = "Auto Detect"
LANGUAGE_ENGLISH = "English"
LANGUAGE_FILIPINO = "Filipino / Tagalog"
LANGUAGE_TAGLISH = "English + Filipino / Taglish"
LANGUAGE_SPANISH = "Spanish"
LANGUAGE_FRENCH = "French"
LANGUAGE_GERMAN = "German"
LANGUAGE_ITALIAN = "Italian"
LANGUAGE_PORTUGUESE = "Portuguese"
LANGUAGE_DUTCH = "Dutch"

LANGUAGE_LABEL_TO_CODE = {
    LANGUAGE_AUTO: None,
    LANGUAGE_ENGLISH: "en",
    LANGUAGE_FILIPINO: "tl",
    LANGUAGE_TAGLISH: None,
    LANGUAGE_SPANISH: "es",
    LANGUAGE_FRENCH: "fr",
    LANGUAGE_GERMAN: "de",
    LANGUAGE_ITALIAN: "it",
    LANGUAGE_PORTUGUESE: "pt",
    LANGUAGE_DUTCH: "nl",
}

LANGUAGE_PROMPTS = {
    LANGUAGE_AUTO: (
        "Faithful verbatim multilingual transcript. Preserve the language actually spoken. "
        "Keep names, numbers, places, technical terms, and normal punctuation. "
        "Do not translate and do not rewrite grammar."
    ),
    LANGUAGE_TAGLISH: (
        "Faithful verbatim transcript of a speaker who may naturally switch between "
        "English and Filipino or Tagalog. Preserve Taglish code-switching and Filipino affixes. "
        "Keep names, numbers, places, technical terms, and normal punctuation. "
        "Do not translate and do not rewrite grammar."
    ),
}

LANGUAGE_DISPLAY_NAMES = {
    LANGUAGE_ENGLISH: "English",
    LANGUAGE_FILIPINO: "Filipino or Tagalog",
    LANGUAGE_SPANISH: "Spanish",
    LANGUAGE_FRENCH: "French",
    LANGUAGE_GERMAN: "German",
    LANGUAGE_ITALIAN: "Italian",
    LANGUAGE_PORTUGUESE: "Portuguese",
    LANGUAGE_DUTCH: "Dutch",
}

GRAMMAR_REVIEW_LANGUAGE_LABELS = {
    LANGUAGE_ENGLISH,
    LANGUAGE_FILIPINO,
    LANGUAGE_TAGLISH,
}


def language_prompt(language_label: str | None) -> str:
    label = language_label or LANGUAGE_AUTO
    if label in LANGUAGE_PROMPTS:
        return LANGUAGE_PROMPTS[label]
    language_name = LANGUAGE_DISPLAY_NAMES.get(label, label)
    return (
        f"Faithful verbatim transcript in {language_name}. Preserve the language actually spoken. "
        "Keep names, numbers, places, technical terms, and normal punctuation. "
        "Do not translate and do not rewrite grammar."
    )


SENSITIVITY_THRESHOLDS = {
    "High — quiet speaker": 0.006,
    "Normal": 0.012,
    "Low — noisy room": 0.022,
}

THEME_OLED = "OLED Black"
THEME_LIGHT = "Dirty White"
THEME_OPTIONS = (THEME_OLED, THEME_LIGHT)

DEFAULT_TOPIC_PROFILE_ID = "general-conversation"


def first_run_has_completed() -> bool:
    """Return True when this portable copy has already shown its first-run report."""
    return FIRST_RUN_MARKER_FILE.is_file() or HARDWARE_PROFILE_FILE.is_file()


def mark_first_run_completed() -> None:
    """Persist first-run completion independently from editable settings."""
    ensure_app_directories()
    atomic_write_text(
        FIRST_RUN_MARKER_FILE,
        "Live Scribe first-run PC report completed.\n",
    )


@dataclass(slots=True)
class AppSettings:
    model_name: str = ""
    language_label: str = LANGUAGE_TAGLISH
    audio_source_mode: str = AUDIO_SOURCE_MICROPHONE
    microphone_label: str = "Default input"
    device_mode: str = "Auto"
    sensitivity_label: str = "Normal"
    include_timestamps: bool = True
    final_accuracy_pass: bool = False
    live_noise_reduction: bool = False
    noise_reduction: bool = True
    grammar_diction_comments: bool = True
    include_live_appendix: bool = True
    theme_name: str = THEME_OLED
    topic_profile_id: str = DEFAULT_TOPIC_PROFILE_ID
    hardware_check_completed: bool = False
    hardware_check_version: int = 0

    @classmethod
    def load(cls, path: Path = SETTINGS_FILE) -> "AppSettings":
        ensure_app_directories()
        if not path.exists():
            settings = cls()
            if first_run_has_completed():
                settings.hardware_check_completed = True
            return settings

        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            settings = cls()
            if first_run_has_completed():
                settings.hardware_check_completed = True
            return settings

        allowed = {field_name for field_name in cls.__dataclass_fields__}
        safe = {key: value for key, value in raw.items() if key in allowed}

        # Migrate the original Taglish label from early versions.
        if safe.get("language_label") == "Auto — English + Tagalog":
            safe["language_label"] = LANGUAGE_TAGLISH
        if safe.get("language_label") == "Tagalog / Filipino":
            safe["language_label"] = LANGUAGE_FILIPINO

        try:
            settings = cls(**safe)
        except TypeError:
            settings = cls()
            if first_run_has_completed():
                settings.hardware_check_completed = True
            return settings

        if settings.model_name not in MODEL_OPTIONS:
            settings.model_name = ""
        if settings.audio_source_mode not in AUDIO_SOURCE_OPTIONS:
            settings.audio_source_mode = AUDIO_SOURCE_MICROPHONE
        if settings.language_label not in LANGUAGE_LABEL_TO_CODE:
            settings.language_label = LANGUAGE_TAGLISH
        if settings.device_mode not in {"Auto", "CPU", "NVIDIA GPU"}:
            settings.device_mode = "Auto"
        if settings.sensitivity_label not in SENSITIVITY_THRESHOLDS:
            settings.sensitivity_label = "Normal"
        if settings.theme_name not in THEME_OPTIONS:
            settings.theme_name = THEME_OLED
        if not isinstance(settings.live_noise_reduction, bool):
            settings.live_noise_reduction = False
        if not isinstance(settings.noise_reduction, bool):
            settings.noise_reduction = True
        if not isinstance(settings.topic_profile_id, str) or not settings.topic_profile_id.strip():
            settings.topic_profile_id = DEFAULT_TOPIC_PROFILE_ID
        if not isinstance(settings.hardware_check_completed, bool):
            settings.hardware_check_completed = False
        if not isinstance(settings.hardware_check_version, int):
            settings.hardware_check_version = 0

        # The independent marker is the source of truth. The hardware report is
        # accepted as a migration signal for users who ran v0.7.2 or earlier.
        if first_run_has_completed():
            settings.hardware_check_completed = True
            if not FIRST_RUN_MARKER_FILE.is_file():
                try:
                    mark_first_run_completed()
                except OSError:
                    pass
        return settings

    def save(self, path: Path = SETTINGS_FILE) -> None:
        ensure_app_directories()
        atomic_write_text(
            path,
            json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n",
        )
        if self.hardware_check_completed:
            mark_first_run_completed()
