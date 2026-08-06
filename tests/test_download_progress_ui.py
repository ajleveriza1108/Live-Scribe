from pathlib import Path


def test_download_progress_panel_is_temporary() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "taglish_transcriber"
    modern = (root / "ui.py").read_text(encoding="utf-8")
    legacy = (root / "ui_base.py").read_text(encoding="utf-8")
    combined = modern + "\n" + legacy

    assert "CTkProgressBar" in modern
    assert "ttk.Progressbar" in legacy
    assert "_show_download_progress" in combined
    assert "_hide_download_progress" in combined
    assert "download_progress_frame.grid_remove()" in combined
    assert "_threadsafe_download_progress" in combined
