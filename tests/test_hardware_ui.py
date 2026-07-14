from pathlib import Path


def test_models_page_exposes_pc_check_and_filtered_downloads() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui.py"
    ).read_text(encoding="utf-8")

    assert "Check This PC Again" in source
    assert "PC check complete" in source
    assert "Unavailable for download" in source
    assert "_hardware_model_selection_options" in source
    assert "_show_first_run_hardware_notice" in source
    assert "Download disabled by the PC capability check" in source
    assert "This installed model is disabled on this PC" in source
