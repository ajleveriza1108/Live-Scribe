from __future__ import annotations

from pathlib import Path
import numpy as np

from src.taglish_transcriber.config import AppSettings
from src.taglish_transcriber.audio import SpeechChunk
from src.taglish_transcriber.session import LiveTranscriptionSession


class RecordingEngine:
    def __init__(self) -> None:
        self.audio_received = None

    def transcribe(self, *, audio, **_kwargs):
        self.audio_received = np.asarray(audio, dtype=np.float32).copy()
        return []


def test_live_noise_option_defaults_off() -> None:
    assert AppSettings().live_noise_reduction is False


def test_live_session_sends_cleaned_phrase_when_enabled(tmp_path: Path) -> None:
    engine = RecordingEngine()
    session = LiveTranscriptionSession(
        engine=engine, microphone_index=None, language_code="en",
        language_label="English", rms_threshold=0.01,
        recording_path=tmp_path / "session.wav", live_noise_reduction=True,
    )
    rate = 16_000
    t = np.arange(rate * 2, dtype=np.float32) / rate
    source = (0.025 * np.sin(2 * np.pi * 90 * t) + 0.18 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    session.chunk_queue.put(SpeechChunk(samples=source, start=0.0, end=2.0))
    session.chunk_queue.put(None)
    session._transcribe_loop()
    assert engine.audio_received is not None
    assert engine.audio_received.shape == source.shape
    assert not np.allclose(engine.audio_received, source)


def test_live_session_uses_original_phrase_when_disabled(tmp_path: Path) -> None:
    engine = RecordingEngine()
    session = LiveTranscriptionSession(
        engine=engine, microphone_index=None, language_code="en",
        language_label="English", rms_threshold=0.01,
        recording_path=tmp_path / "session.wav", live_noise_reduction=False,
    )
    source = np.linspace(-0.1, 0.1, 16_000, dtype=np.float32)
    session.chunk_queue.put(SpeechChunk(samples=source, start=0.0, end=1.0))
    session.chunk_queue.put(None)
    session._transcribe_loop()
    assert engine.audio_received is not None
    assert np.array_equal(engine.audio_received, source)
