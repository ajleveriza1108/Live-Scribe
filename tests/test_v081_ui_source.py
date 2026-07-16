from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_summary_button_and_tab_exist() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "productivity_features.py"
    ).read_text(encoding="utf-8")
    assert "Summarize & Format" in source
    assert 'self.notebook.add("Summary & format")' in source
    assert "The raw transcript was not changed" in source


def test_modern_microphone_dropdown_is_whole_clickable() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "ui.py"
    ).read_text(encoding="utf-8")
    assert "WholeClickableDropdown" in source
    assert "self.microphone_combo = WholeClickableDropdown" in source
