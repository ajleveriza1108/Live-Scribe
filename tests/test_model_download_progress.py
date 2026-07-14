from pathlib import Path

from src.taglish_transcriber import models


def test_download_progress_percentage_is_bounded() -> None:
    progress = models.ModelDownloadProgress(
        model_name="small",
        phase="downloading",
        downloaded_bytes=50,
        total_bytes=100,
    )
    assert progress.percent == 50.0

    over = models.ModelDownloadProgress(
        model_name="small",
        phase="downloading",
        downloaded_bytes=200,
        total_bytes=100,
    )
    assert over.percent == 100.0


def test_local_download_size_counts_model_and_partial_files(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_bytes(b"a" * 10)
    (tmp_path / "model.bin").write_bytes(b"b" * 20)

    partial = tmp_path / ".cache" / "huggingface" / "download"
    partial.mkdir(parents=True)
    (partial / "tokenizer.json.incomplete").write_bytes(b"c" * 30)
    (partial / "ignored.metadata").write_bytes(b"d" * 100)

    assert models._local_downloaded_bytes(tmp_path) == 60


def test_every_selectable_model_has_a_repository() -> None:
    assert set(models.MODEL_OPTIONS).issubset(models.MODEL_REPOSITORIES)
