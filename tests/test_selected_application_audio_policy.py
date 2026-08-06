from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_source_label_requires_application_selection() -> None:
    config = (
        ROOT / "src" / "taglish_transcriber" / "config.py"
    ).read_text(encoding="utf-8")
    assert 'AUDIO_SOURCE_APPLICATION = "Computer / livestream — choose application"' in config
    assert "if sys.platform == \"win32\"" in config


def test_capture_uses_include_process_tree() -> None:
    audio = (
        ROOT / "src" / "taglish_transcriber" / "audio.py"
    ).read_text(encoding="utf-8")
    assert '"includetree"' in audio


def test_ui_explains_strict_selected_app_capture() -> None:
    base = (
        ROOT / "src" / "taglish_transcriber" / "ui_base.py"
    ).read_text(encoding="utf-8")
    productivity = (
        ROOT
        / "src"
        / "taglish_transcriber"
        / "productivity_features.py"
    ).read_text(encoding="utf-8")
    assert "Only the chosen" in base
    assert "process tree should be captured" in base
    assert "Window or application to transcribe" in productivity
    assert "Capture only this application" in productivity
