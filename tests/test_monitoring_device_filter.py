from __future__ import annotations

from pathlib import Path

from src.taglish_transcriber.audio import (
    AudioOutputInfo,
    _audio_output_matches_connected_key,
    _deduplicate_audio_outputs,
)

ROOT = Path(__file__).resolve().parents[1]


def _output(
    index: int,
    name: str,
    *,
    host: str,
    default: bool = False,
    available: bool = True,
) -> AudioOutputInfo:
    return AudioOutputInfo(
        index=index,
        name=name,
        sample_rate=48000.0,
        max_output_channels=2,
        is_default=default,
        available=available,
        host_api_name=host,
    )


def test_duplicate_output_backends_collapse_to_wasapi(monkeypatch) -> None:
    monkeypatch.setattr("src.taglish_transcriber.audio.sys.platform", "win32")
    outputs = [
        _output(2, "Speakers (Realtek Audio)", host="MME", default=True),
        _output(18, "Speakers (Realtek Audio)", host="Windows DirectSound"),
        _output(31, "Speakers (Realtek Audio)", host="Windows WASAPI"),
    ]
    result = _deduplicate_audio_outputs(
        outputs,
        native_default_key="speakers realtek audio",
    )
    assert len(result) == 1
    assert result[0].index == 31
    assert result[0].is_default is True


def test_connected_output_matching_accepts_backend_decoration() -> None:
    output = _output(
        31,
        "Speakers (Realtek(R) Audio)",
        host="Windows WASAPI",
    )
    assert _audio_output_matches_connected_key(
        output,
        {"speakers realtek audio"},
    )


def test_monitoring_uses_filtered_output_list() -> None:
    source = (
        ROOT / "src/taglish_transcriber/productivity_features.py"
    ).read_text(encoding="utf-8")
    assert "list_available_audio_outputs()" in source
    assert "Uses the same filtered microphone selected above." in source


def test_detect_refreshes_monitor_source_and_output_devices() -> None:
    source = (
        ROOT / "src/taglish_transcriber/productivity_features.py"
    ).read_text(encoding="utf-8")
    assert "self._refresh_microphone_monitor_devices()" in source
    assert "self.microphone_monitor_source_var.set(" in source


def test_monitoring_is_allowed_in_conversation_mode() -> None:
    source = (
        ROOT / "src/taglish_transcriber/productivity_features.py"
    ).read_text(encoding="utf-8")
    assert "AUDIO_SOURCE_CONVERSATION" in source
    assert "set_microphone_monitor_enabled" in source
    assert "set_microphone_monitor_output" in source
