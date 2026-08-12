from __future__ import annotations

from pathlib import Path

from src.taglish_transcriber.audio import (
    MicrophoneInfo,
    clean_microphone_label,
    parse_microphone_index,
)

ROOT = Path(__file__).resolve().parents[1]


def _mic(index: int, name: str, *, default: bool = False) -> MicrophoneInfo:
    return MicrophoneInfo(
        index=index,
        name=name,
        sample_rate=48000.0,
        max_input_channels=2,
        is_default=default,
        available=True,
        host_api_name="Windows WASAPI",
    )


def test_microphone_label_hides_internal_portaudio_index() -> None:
    microphone = _mic(26, "Microphone (Realtek(R) Audio)", default=True)
    assert microphone.label == "Microphone (Realtek(R) Audio) (System default)"
    assert not microphone.label.startswith("26:")


def test_legacy_saved_microphone_label_is_cleaned() -> None:
    assert clean_microphone_label(
        "26: Microphone (Realtek(R) Audio) (System default)"
    ) == "Microphone (Realtek(R) Audio) (System default)"


def test_legacy_numeric_label_still_resolves_without_device_scan() -> None:
    assert parse_microphone_index("27: CABLE Output (VB-Audio Virtual Cable)") == 27


def test_clean_label_resolves_back_to_internal_index(monkeypatch) -> None:
    microphones = [
        _mic(26, "Microphone (Realtek(R) Audio)", default=True),
        _mic(29, "Microphone (Camo)"),
    ]
    monkeypatch.setattr(
        "src.taglish_transcriber.audio.list_available_microphones",
        lambda: microphones,
    )
    assert parse_microphone_index("Microphone (Camo)") == 29


def test_ui_does_not_show_numeric_microphone_counts() -> None:
    source = (
        ROOT / "src/taglish_transcriber/ui_base.py"
    ).read_text(encoding="utf-8")
    assert "Connected microphones available. Selected:" in source
    assert "connected microphones are available." in source
    assert "count = len(available_labels)" not in source


def test_microphone_availability_check_uses_filtered_list() -> None:
    source = (
        ROOT / "src/taglish_transcriber/ui_base.py"
    ).read_text(encoding="utf-8")
    assert "item.label: item for item in list_available_microphones()" in source
