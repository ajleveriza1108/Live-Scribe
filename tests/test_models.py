from pathlib import Path

from src.taglish_transcriber import models


def test_model_download_detection(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(models, "MODEL_DIR", tmp_path)
    folder = models.local_model_path("small")
    folder.mkdir()
    assert not models.is_model_downloaded("small")

    for name in models.MODEL_REQUIRED_FILES:
        (folder / name).write_bytes(b"test")

    assert models.is_model_downloaded("small")
    assert "ready for offline use" in models.model_status("small")


def test_no_model_is_selected_on_first_run() -> None:
    assert models.model_status("").startswith("Choose a speech quality")
    assert not models.is_model_downloaded("")
