from pathlib import Path


def test_download_progress_panel_is_temporary() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui.py"
    ).read_text(encoding="utf-8")

    assert "ttk.Progressbar" in source
    assert "_show_download_progress" in source
    assert "_hide_download_progress" in source
    assert "download_progress_frame.grid_remove()" in source
    assert "_threadsafe_download_progress" in source
