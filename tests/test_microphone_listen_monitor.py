from __future__ import annotations

import sys
import time
import types

import numpy as np

from src.taglish_transcriber.audio import (
    MicrophoneOutputMonitor,
    parse_audio_output_index,
)
from src.taglish_transcriber.config import AppSettings


class FakeOutputStream:
    instances = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.started = False
        self.closed = False
        self.writes = []
        self.__class__.instances.append(self)

    def start(self) -> None:
        self.started = True

    def write(self, data) -> None:
        self.writes.append(np.asarray(data).copy())

    def stop(self) -> None:
        self.started = False

    def close(self) -> None:
        self.closed = True


def fake_sounddevice_module():
    module = types.ModuleType("sounddevice")
    module.OutputStream = FakeOutputStream
    module.query_devices = lambda _device, _kind: {
        "name": "Headphones",
        "default_samplerate": 48_000.0,
        "max_output_channels": 2,
    }
    return module


def test_microphone_listening_defaults_off() -> None:
    settings = AppSettings()
    assert settings.microphone_listen_enabled is False
    assert settings.microphone_monitor_output_label == ""


def test_output_label_parser() -> None:
    assert parse_audio_output_index("7: USB Headphones") == 7
    assert parse_audio_output_index("System default output") is None
    assert parse_audio_output_index("") is None


def test_output_monitor_plays_copies_without_blocking_capture(monkeypatch) -> None:
    FakeOutputStream.instances.clear()
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sounddevice_module())
    monitor = MicrophoneOutputMonitor("7: USB Headphones")
    monitor.start(44_100.0)
    source = np.linspace(-0.2, 0.2, 4_410, dtype=np.float32)
    monitor.submit(source, 44_100.0)

    deadline = time.time() + 1.5
    while time.time() < deadline:
        if FakeOutputStream.instances[-1].writes:
            break
        time.sleep(0.01)

    monitor.stop()
    stream = FakeOutputStream.instances[-1]
    assert stream.writes
    assert stream.writes[0].ndim == 2
    assert stream.writes[0].shape[1] == 2
    assert np.array_equal(source, np.linspace(-0.2, 0.2, 4_410, dtype=np.float32))
    assert stream.closed is True
