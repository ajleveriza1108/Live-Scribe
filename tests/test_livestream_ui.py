from pathlib import Path
import sys

from src.taglish_transcriber.config import (
    AUDIO_SOURCE_APPLICATION,
    AUDIO_SOURCE_MICROPHONE,
    AUDIO_SOURCE_OPTIONS,
    AUDIO_SOURCE_SYSTEM,
    AppSettings,
)


def test_audio_source_settings_default_to_microphone() -> None:
    settings = AppSettings()
    assert settings.audio_source_mode == AUDIO_SOURCE_MICROPHONE


def test_platform_audio_source_policy() -> None:
    assert AUDIO_SOURCE_MICROPHONE in AUDIO_SOURCE_OPTIONS
    if sys.platform == "win32":
        assert AUDIO_SOURCE_APPLICATION in AUDIO_SOURCE_OPTIONS
        assert AUDIO_SOURCE_SYSTEM not in AUDIO_SOURCE_OPTIONS
    else:
        assert AUDIO_SOURCE_SYSTEM in AUDIO_SOURCE_OPTIONS
        assert AUDIO_SOURCE_APPLICATION not in AUDIO_SOURCE_OPTIONS


def test_ui_exposes_audio_source_refresh() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "taglish_transcriber"
    ui_source = (root / "ui.py").read_text(encoding="utf-8")
    base_source = (root / "ui_base.py").read_text(encoding="utf-8")

    assert "AUDIO_SOURCE_OPTIONS" in ui_source
    assert "_refresh_audio_inputs" in ui_source
    assert "audio_source_mode=self.settings.audio_source_mode" in base_source
