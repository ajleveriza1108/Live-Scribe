from __future__ import annotations

import sys
import types

import numpy as np

from src.taglish_transcriber.smart_vad import SmartVoiceGate


class FakeVadOptions:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


def test_silero_gate_trims_to_detected_region(monkeypatch) -> None:
    fake_module = types.ModuleType("faster_whisper.vad")
    fake_module.VadOptions = FakeVadOptions
    fake_module.get_speech_timestamps = (
        lambda audio, options, sampling_rate=16000: [
            {"start": 1600, "end": 8000}
        ]
    )
    monkeypatch.setitem(sys.modules, "faster_whisper.vad", fake_module)

    gate = SmartVoiceGate(enabled=True)
    audio = np.ones(16000, dtype=np.float32) * 0.1
    result = gate.process(audio)

    assert result.speech_detected
    assert result.backend == "silero"
    assert result.samples.size == 6400
    assert result.start_offset_seconds == 0.1


def test_silero_gate_skips_clear_silence(monkeypatch) -> None:
    fake_module = types.ModuleType("faster_whisper.vad")
    fake_module.VadOptions = FakeVadOptions
    fake_module.get_speech_timestamps = (
        lambda audio, options, sampling_rate=16000: []
    )
    monkeypatch.setitem(sys.modules, "faster_whisper.vad", fake_module)

    result = SmartVoiceGate(enabled=True).process(
        np.zeros(8000, dtype=np.float32)
    )
    assert not result.speech_detected
    assert result.samples.size == 0
