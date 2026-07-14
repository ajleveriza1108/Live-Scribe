from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .paths import SETTINGS_FILE, ensure_app_directories


MODEL_PLACEHOLDER = "Select a model…"
MODEL_OPTIONS = (
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3-turbo",
    "large-v3",
)
MODEL_SELECTION_OPTIONS = (MODEL_PLACEHOLDER, *MODEL_OPTIONS)

AUDIO_SOURCE_MICROPHONE = "Microphone"
AUDIO_SOURCE_SYSTEM = "Computer audio / livestream"
AUDIO_SOURCE_OPTIONS = (AUDIO_SOURCE_MICROPHONE, AUDIO_SOURCE_SYSTEM)

LANGUAGE_LABEL_TO_CODE = {
    "Auto — English + Tagalog": None,
    "English": "en",
    "Tagalog / Filipino": "tl",
}

SENSITIVITY_THRESHOLDS = {
    "High — quiet speaker": 0.006,
    "Normal": 0.012,
    "Low — noisy room": 0.022,
}


@dataclass(slots=True)
class AppSettings:
    # Empty means the buyer has not selected a speech model yet.
    model_name: str = ""
    language_label: str = "Auto — English + Tagalog"
    audio_source_mode: str = AUDIO_SOURCE_MICROPHONE
    microphone_label: str = "Default input"
    device_mode: str = "Auto"
    sensitivity_label: str = "Normal"
    include_timestamps: bool = True
    # Legacy preference retained for existing settings files. Verification is manual in v0.4.1.
    final_accuracy_pass: bool = False
    noise_reduction: bool = True
    grammar_diction_comments: bool = True
    include_live_appendix: bool = True

    @classmethod
    def load(cls, path: Path = SETTINGS_FILE) -> "AppSettings":
        ensure_app_directories()
        if not path.exists():
            return cls()

        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()

        allowed = {field_name for field_name in cls.__dataclass_fields__}
        safe = {key: value for key, value in raw.items() if key in allowed}

        try:
            settings = cls(**safe)
        except TypeError:
            return cls()

        if settings.model_name not in MODEL_OPTIONS:
            settings.model_name = ""
        if settings.audio_source_mode not in AUDIO_SOURCE_OPTIONS:
            settings.audio_source_mode = AUDIO_SOURCE_MICROPHONE
        if settings.language_label not in LANGUAGE_LABEL_TO_CODE:
            settings.language_label = "Auto — English + Tagalog"
        if settings.device_mode not in {"Auto", "CPU", "NVIDIA GPU"}:
            settings.device_mode = "Auto"
        if settings.sensitivity_label not in SENSITIVITY_THRESHOLDS:
            settings.sensitivity_label = "Normal"
        return settings

    def save(self, path: Path = SETTINGS_FILE) -> None:
        ensure_app_directories()
        path.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
