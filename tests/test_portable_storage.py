from __future__ import annotations

from pathlib import Path

from src.taglish_transcriber.portable import (
    STORAGE_GOOD,
    STORAGE_NOT_TESTED,
    STORAGE_SLOW,
    STORAGE_USABLE,
    assess_portable_storage,
    classify_write_speed,
    quick_write_test,
)


def test_portable_speed_classification() -> None:
    assert classify_write_speed(None)[0] == STORAGE_NOT_TESTED
    assert classify_write_speed(50.0)[0] == STORAGE_GOOD
    assert classify_write_speed(15.0)[0] == STORAGE_USABLE
    assert classify_write_speed(5.0)[0] == STORAGE_SLOW


def test_quick_write_test_uses_and_cleans_requested_folder(tmp_path: Path) -> None:
    speed = quick_write_test(tmp_path, total_bytes=2 * 1024 * 1024)
    assert speed is None or speed > 0
    assert not (tmp_path / ".portable-storage-speed-test.bin").exists()


def test_portable_report_is_buyer_readable(tmp_path: Path) -> None:
    report = assess_portable_storage(run_speed_test=False, app_root=tmp_path)
    assert "Portable folder" in report.summary()
    assert report.drive_kind
    assert report.note
