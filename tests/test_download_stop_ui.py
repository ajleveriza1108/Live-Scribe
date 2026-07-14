from pathlib import Path


def test_modern_ui_exposes_stop_download_and_resume_wording() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui.py"
    ).read_text(encoding="utf-8")
    base = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui_base.py"
    ).read_text(encoding="utf-8")

    assert 'text="Stop Download"' in source
    assert "_stop_model_download_requested" in base
    assert "Partial files were kept" in base
    assert "resume" in base.casefold()


def test_vocabulary_dialog_has_explicit_crud_actions() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "vocabulary_dialog.py"
    ).read_text(encoding="utf-8")

    assert 'text="Add New"' in source
    assert 'text="Save Changes"' in source
    assert 'text="Remove Selected"' in source
