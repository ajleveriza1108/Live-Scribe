from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_recorded_file_buttons_remain_available_while_idle() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "productivity_features.py"
    ).read_text(encoding="utf-8")

    assert "Choosing a recorded file is a primary entry point" in source
    assert 'else "normal"' in source
    assert "self.import_media_button.configure(state=recorded_file_state)" in source
    assert (
        "self.import_media_primary_button.configure(state=recorded_file_state)"
        in source
    )


def test_missing_model_redirects_user_to_models_page() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "productivity_features.py"
    ).read_text(encoding="utf-8")

    assert 'messagebox.askokcancel(' in source
    assert '"Open the Models page now?"' in source
    assert 'self._show_page("Models")' in source
