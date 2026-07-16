from __future__ import annotations

import shutil
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class NoiseReductionResult:
    output_path: Path
    applied: bool
    message: str


def _read_pcm_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())
    if sample_width != 2:
        raise ValueError("Only 16-bit PCM WAV recordings are supported.")
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, sample_rate


def _write_pcm_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2", copy=False)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def _reduce_stationary_noise_samples(
    samples: np.ndarray,
    sample_rate: int,
    *,
    strength: float,
    spectral_floor: float,
    quiet_fraction: float,
) -> np.ndarray:
    """Lightweight model-free spectral subtraction for one complete phrase."""
    source = np.asarray(samples, dtype=np.float32).reshape(-1)
    if source.size < max(2048, sample_rate // 2):
        return source.copy()

    frame_size = 1024 if sample_rate >= 32_000 else 512
    hop = frame_size // 4
    window = np.hanning(frame_size).astype(np.float32)
    padding = (-source.size - frame_size) % hop
    padded = np.pad(source, (0, max(0, padding + frame_size)))
    frame_count = 1 + (padded.size - frame_size) // hop

    spectra: list[np.ndarray] = []
    energies: list[float] = []
    for index in range(frame_count):
        start = index * hop
        frame = padded[start:start + frame_size] * window
        spectrum = np.fft.rfft(frame)
        spectra.append(spectrum)
        energies.append(float(np.mean(frame * frame)))

    quiet_count = min(frame_count, max(4, int(round(frame_count * quiet_fraction))))
    quiet_indices = np.argsort(np.asarray(energies, dtype=np.float64))[:quiet_count]
    noise_magnitude = np.median(
        np.stack([np.abs(spectra[index]) for index in quiet_indices]), axis=0
    )

    output = np.zeros_like(padded, dtype=np.float64)
    weight = np.zeros_like(padded, dtype=np.float64)
    window_squared = np.square(window, dtype=np.float64)
    for index, spectrum in enumerate(spectra):
        magnitude = np.abs(spectrum)
        phase = np.exp(1j * np.angle(spectrum))
        reduced = np.maximum(
            magnitude - strength * noise_magnitude,
            spectral_floor * magnitude,
        )
        cleaned_frame = np.fft.irfft(reduced * phase, n=frame_size).real
        start = index * hop
        output[start:start + frame_size] += cleaned_frame * window
        weight[start:start + frame_size] += window_squared

    valid = weight > 1e-8
    output[valid] /= weight[valid]
    cleaned = output[:source.size].astype(np.float32)
    source_peak = float(np.max(np.abs(source))) if source.size else 0.0
    cleaned_peak = float(np.max(np.abs(cleaned))) if cleaned.size else 0.0
    if source_peak > 0 and cleaned_peak > 0:
        cleaned *= min(1.25, source_peak / cleaned_peak)
    return np.nan_to_num(
        np.clip(cleaned, -1.0, 1.0), nan=0.0, posinf=1.0, neginf=-1.0
    ).astype(np.float32, copy=False)


def reduce_live_chunk_noise(samples: np.ndarray, sample_rate: int = 16_000) -> np.ndarray:
    """Conservatively clean a completed live phrase for recognition only.

    The original recorder receives untouched audio. This targets steady fan,
    air-conditioner, hum, and room hiss without adding an AI model.
    """
    return _reduce_stationary_noise_samples(
        samples,
        sample_rate,
        strength=0.55,
        spectral_floor=0.42,
        quiet_fraction=0.10,
    )


def reduce_stationary_noise(
    input_path: Path,
    output_path: Path,
    *,
    strength: float = 1.0,
    spectral_floor: float = 0.18,
) -> NoiseReductionResult:
    """Apply conservative spectral subtraction to a completed WAV recording."""
    samples, sample_rate = _read_pcm_wav(input_path)
    if samples.size < max(2048, sample_rate // 2):
        shutil.copy2(input_path, output_path)
        return NoiseReductionResult(
            output_path=output_path,
            applied=False,
            message="Recording was too short for safe noise estimation; original WAV used.",
        )
    cleaned = _reduce_stationary_noise_samples(
        samples,
        sample_rate,
        strength=strength,
        spectral_floor=spectral_floor,
        quiet_fraction=0.12,
    )
    _write_pcm_wav(output_path, cleaned, sample_rate)
    return NoiseReductionResult(
        output_path=output_path,
        applied=True,
        message="Conservative post-session noise reduction completed.",
    )
