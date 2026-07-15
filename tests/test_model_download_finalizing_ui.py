from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_modern_download_ui_has_real_finalizing_state() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "ui.py"
    ).read_text(encoding="utf-8")

    assert 'progress.phase in {"preparing", "finalizing"}' in source
    assert 'text=f"Finalizing {friendly}"' in source
    assert 'self.status_var.set("Finalizing model")' in source
    assert "Do not close" in source


def test_download_progress_reserves_full_bar_for_complete_phase() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "models.py"
    ).read_text(encoding="utf-8")

    assert 'upper_bound = 100.0 if self.phase == "complete" else 99.0' in source
    assert "tracker.set_initial_bytes(initial_bytes)" in source
    assert 'phase="finalizing"' in source
