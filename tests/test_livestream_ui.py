from pathlib import Path

from src.taglish_transcriber.config import (
    AUDIO_SOURCE_MICROPHONE,
    AUDIO_SOURCE_OPTIONS,
    AUDIO_SOURCE_SYSTEM,
    AppSettings,
)


def test_audio_source_settings_default_to_microphone() -> None:
    settings = AppSettings()
    assert settings.audio_source_mode == AUDIO_SOURCE_MICROPHONE
    assert AUDIO_SOURCE_SYSTEM in AUDIO_SOURCE_OPTIONS


def test_ui_exposes_livestream_mode() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui.py"
    ).read_text(encoding="utf-8")

    assert "AUDIO_SOURCE_SYSTEM" in source
    assert "_refresh_audio_inputs" in source
    assert "audio_source_mode=self.settings.audio_source_mode" in source
