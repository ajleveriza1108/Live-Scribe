from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_productivity_gui_exposes_requested_controls() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "productivity_features.py"
    ).read_text(encoding="utf-8")

    for text in (
        "Pause",
        "Transcribe Video / Audio",
        "Floating Captions",
        "Transcript editor",
        "Set Speaker",
        "Play 8 Seconds",
        "Action Item",
        "Saved Sessions",
        "Storage Manager",
        "Recover unfinished session",
    ):
        assert text in source


def test_modern_navigation_includes_sessions() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "ui.py"
    ).read_text(encoding="utf-8")
    assert '("Sessions", "▤")' in source
    assert "ProductivityFeaturesMixin" in source
