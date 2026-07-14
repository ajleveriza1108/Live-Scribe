from pathlib import Path

from src.taglish_transcriber.config import THEME_LIGHT, THEME_OLED


def test_modern_gui_uses_customtkinter_and_two_themes() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui.py"
    ).read_text(encoding="utf-8")

    assert "import customtkinter as ctk" in source
    assert THEME_OLED == "OLED Black"
    assert THEME_LIGHT == "Dirty White"
    assert "Live Session" in source
    assert "Vocabulary" in source
    assert "Models" in source
    assert "Settings" in source
    assert "Stop & Save WAV" in source
    assert "Verify from WAV" in source
    assert "download_progress_frame.grid_remove()" in source
