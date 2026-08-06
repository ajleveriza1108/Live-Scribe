from __future__ import annotations

from pathlib import Path

from src.taglish_transcriber.audio import AudioInputMonitor


ROOT = Path(__file__).resolve().parents[1]


class FakeStream:
    def __init__(self) -> None:
        self.aborted = False
        self.stopped = False
        self.closed = False

    def abort(self) -> None:
        self.aborted = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class FakeMonitorOutput:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


def test_audio_input_stop_is_idempotent_and_aborts_stream() -> None:
    monitor = AudioInputMonitor(
        source_mode="Microphone",
        input_label="0: Fake",
        microphone_index=0,
        application_enabled=True,
        event_callback=lambda _payload: None,
    )
    stream = FakeStream()
    output = FakeMonitorOutput()
    monitor._stream = stream
    monitor._microphone_output_monitor = output

    monitor.stop()
    monitor.stop()

    assert stream.aborted
    assert stream.stopped
    assert stream.closed
    assert output.stopped


def test_ui_stops_input_test_on_cleanup_worker() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "productivity_features.py"
    ).read_text(encoding="utf-8")

    assert 'name="input-test-cleanup"' in source
    assert "self._input_test_stop_in_progress = True" in source
    assert "The window remains responsive" in source
    assert "on_stopped=self._continue_start_requested" in source
    assert "_input_test_generation" in source
