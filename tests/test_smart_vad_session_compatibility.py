from pathlib import Path

from src.taglish_transcriber.config import AppSettings
from src.taglish_transcriber.session import LiveTranscriptionSession


def test_ui_setting_keeps_smart_vad_enabled_by_default() -> None:
    assert AppSettings().smart_vad is True


def test_low_level_session_constructor_is_backwards_compatible() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "session.py"
    ).read_text(encoding="utf-8")
    assert "smart_vad: bool = False" in source


def test_ui_passes_the_saved_smart_vad_setting() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui_base.py"
    ).read_text(encoding="utf-8")
    assert "smart_vad=self.settings.smart_vad" in source
