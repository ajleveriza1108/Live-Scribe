from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from src.taglish_transcriber.audio import WavRecorder
from src.taglish_transcriber.noise_reduction import (
    reduce_live_chunk_noise,
    reduce_stationary_noise,
)


def test_wav_recorder_writes_pcm_file(tmp_path: Path) -> None:
    path = tmp_path / "session.wav"
    recorder = WavRecorder(path, 16_000)
    recorder.start()
    assert recorder.submit(np.zeros(1_600, dtype=np.float32))
    assert recorder.submit(np.full(1_600, 0.25, dtype=np.float32))
    recorder.close()

    assert recorder.error is None
    assert path.is_file()
    with wave.open(str(path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16_000
        assert wav_file.getnframes() == 3_200


def test_noise_reduction_keeps_original_and_creates_output(tmp_path: Path) -> None:
    source = tmp_path / "original.wav"
    output = tmp_path / "enhanced.wav"
    sample_rate = 16_000
    time = np.arange(sample_rate, dtype=np.float32) / sample_rate
    samples = 0.03 * np.sin(2 * np.pi * 60 * time)
    samples += 0.20 * np.sin(2 * np.pi * 440 * time)
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    with wave.open(str(source), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())

    original_bytes = source.read_bytes()
    result = reduce_stationary_noise(source, output)

    assert result.output_path == output
    assert output.is_file()
    assert source.read_bytes() == original_bytes
    with wave.open(str(output), "rb") as wav_file:
        assert wav_file.getframerate() == sample_rate
        assert wav_file.getnframes() == sample_rate


def test_live_noise_reduction_preserves_shape_and_reduces_quiet_noise() -> None:
    sample_rate = 16_000
    time_axis = np.arange(sample_rate * 2, dtype=np.float32) / sample_rate
    steady_noise = 0.025 * np.sin(2 * np.pi * 90 * time_axis)
    speech = np.zeros_like(steady_noise)
    speech_start = sample_rate // 2
    speech_end = speech_start + sample_rate
    speech[speech_start:speech_end] = 0.18 * np.sin(
        2 * np.pi * 440 * time_axis[speech_start:speech_end]
    )
    source = (steady_noise + speech).astype(np.float32)
    cleaned = reduce_live_chunk_noise(source, sample_rate)
    assert cleaned.shape == source.shape
    assert cleaned.dtype == np.float32
    assert np.all(np.isfinite(cleaned))
    quiet_source_rms = float(np.sqrt(np.mean(source[:speech_start] ** 2)))
    quiet_cleaned_rms = float(np.sqrt(np.mean(cleaned[:speech_start] ** 2)))
    assert quiet_cleaned_rms < quiet_source_rms
