from __future__ import annotations

import json
from pathlib import Path

import src.taglish_transcriber.config as config


def test_marker_prevents_popup_when_settings_are_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings_path = tmp_path / "settings.json"
    marker = tmp_path / ".first-run-complete"
    hardware = tmp_path / "hardware_profile.json"
    marker.write_text("done\n", encoding="utf-8")

    monkeypatch.setattr(config, "FIRST_RUN_MARKER_FILE", marker)
    monkeypatch.setattr(config, "HARDWARE_PROFILE_FILE", hardware)

    settings = config.AppSettings.load(settings_path)
    assert settings.hardware_check_completed


def test_legacy_hardware_report_migrates_to_permanent_marker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings_path = tmp_path / "settings.json"
    marker = tmp_path / ".first-run-complete"
    hardware = tmp_path / "hardware_profile.json"
    hardware.write_text("{}\n", encoding="utf-8")
    settings_path.write_text(
        json.dumps({"hardware_check_completed": False}),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "FIRST_RUN_MARKER_FILE", marker)
    monkeypatch.setattr(config, "HARDWARE_PROFILE_FILE", hardware)

    settings = config.AppSettings.load(settings_path)
    assert settings.hardware_check_completed
    assert marker.is_file()


def test_saving_completed_settings_writes_marker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings_path = tmp_path / "settings.json"
    marker = tmp_path / ".first-run-complete"
    hardware = tmp_path / "hardware_profile.json"

    monkeypatch.setattr(config, "FIRST_RUN_MARKER_FILE", marker)
    monkeypatch.setattr(config, "HARDWARE_PROFILE_FILE", hardware)

    settings = config.AppSettings(hardware_check_completed=True)
    settings.save(settings_path)

    assert marker.is_file()
    assert json.loads(settings_path.read_text(encoding="utf-8"))[
        "hardware_check_completed"
    ] is True
