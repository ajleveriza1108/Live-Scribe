from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_idle_start_remains_clickable_and_explains_setup() -> None:
    base = (
        ROOT / "src" / "taglish_transcriber" / "ui_base.py"
    ).read_text(encoding="utf-8")
    ui = (
        ROOT / "src" / "taglish_transcriber" / "ui.py"
    ).read_text(encoding="utf-8")

    assert '"Set Up Listening"' in base
    assert "Open Models now" in base
    assert '"Download Model to Start"' in ui
    assert '"Choose a Lighter Model"' in ui
    assert 'self._show_page("Models")' in ui
