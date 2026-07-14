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


def reduce_stationary_noise(
    input_path: Path,
    output_path: Path,
    *,
    strength: float = 1.0,
    spectral_floor: float = 0.18,
) -> NoiseReductionResult:
    """Apply conservative spectral subtraction to a completed WAV recording.

    This lightweight engine targets steady fan, air-conditioner, and room noise.
    It intentionally avoids aggressive processing that can damage consonants.
    """
    samples, sample_rate = _read_pcm_wav(input_path)
    if samples.size < max(2048, sample_rate // 2):
        shutil.copy2(input_path, output_path)
        return NoiseReductionResult(
            output_path=output_path,
            applied=False,
            message="Recording was too short for safe noise estimation; original WAV used.",
        )

    frame_size = 1024 if sample_rate >= 32_000 else 512
    hop = frame_size // 4
    window = np.hanning(frame_size).astype(np.float32)

    padding = (-samples.size - frame_size) % hop
    padded = np.pad(samples, (0, max(0, padding + frame_size)))
    frame_count = 1 + (padded.size - frame_size) // hop

    spectra: list[np.ndarray] = []
    energies: list[float] = []
    for index in range(frame_count):
        start = index * hop
        frame = padded[start : start + frame_size] * window
        spectrum = np.fft.rfft(frame)
        spectra.append(spectrum)
        energies.append(float(np.mean(frame * frame)))

    energy_array = np.asarray(energies)
    quiet_count = max(4, int(round(frame_count * 0.12)))
    quiet_indices = np.argsort(energy_array)[:quiet_count]
    noise_magnitude = np.median(
        np.stack([np.abs(spectra[index]) for index in quiet_indices]),
        axis=0,
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
        output[start : start + frame_size] += cleaned_frame * window
        weight[start : start + frame_size] += window_squared

    valid = weight > 1e-8
    output[valid] /= weight[valid]
    cleaned = output[: samples.size].astype(np.float32)

    original_peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    cleaned_peak = float(np.max(np.abs(cleaned))) if cleaned.size else 0.0
    if original_peak > 0 and cleaned_peak > 0:
        cleaned *= min(1.5, original_peak / cleaned_peak)

    _write_pcm_wav(output_path, cleaned, sample_rate)
    return NoiseReductionResult(
        output_path=output_path,
        applied=True,
        message="Conservative post-session noise reduction completed.",
    )
