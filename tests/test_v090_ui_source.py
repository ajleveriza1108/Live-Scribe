from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_settings_expose_smart_vad_and_memory_saver() -> None:
    ui = (
        ROOT / "src" / "taglish_transcriber" / "ui.py"
    ).read_text(encoding="utf-8")
    assert "Smart Silero speech detection" in ui
    assert "Memory Saver" in ui
    assert "Release Model from RAM" in ui


def test_engine_is_reused_instead_of_loaded_twice() -> None:
    base = (
        ROOT / "src" / "taglish_transcriber" / "ui_base.py"
    ).read_text(encoding="utf-8")
    assert "Reusing the loaded speech model" in base
    assert "self._schedule_engine_release()" in base
