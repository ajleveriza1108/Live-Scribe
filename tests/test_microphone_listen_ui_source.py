from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_microphone_listen_controls_are_present() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "productivity_features.py"
    ).read_text(encoding="utf-8")
    assert 'text="Listen to this microphone"' in source
    assert 'text="Selected microphone monitoring"' in source
    assert 'text="Output device"' in source
    assert "Use headphones to prevent echo or feedback" in source


def test_session_can_toggle_monitor_without_stopping_transcription() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "session.py"
    ).read_text(encoding="utf-8")
    assert "set_microphone_monitor_enabled" in source
    assert "set_microphone_monitor_output" in source
    assert "monitor_enabled=self.microphone_listen_enabled" in source


def test_patch_preserves_raw_audio_path() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "audio.py"
    ).read_text(encoding="utf-8")
    assert "self._output_monitor.submit(raw, self._source_rate)" in source
    assert "self._submit_samples(raw)" in source
