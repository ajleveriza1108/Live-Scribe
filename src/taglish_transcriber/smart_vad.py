from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class VoiceGateResult:
    samples: np.ndarray
    start_offset_seconds: float
    speech_detected: bool
    speech_ratio: float
    backend: str


class SmartVoiceGate:
    """Fast phrase gate using Faster-Whisper's bundled Silero VAD.

    Faster-Whisper already ships the Silero ONNX asset used by its own
    transcription VAD. This wrapper reuses it before model inference so
    clear non-speech chunks can be rejected without adding Torch or a
    second VAD download. Imports and model loading remain lazy.
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        sample_rate: int = 16_000,
        threshold: float = 0.50,
    ) -> None:
        self.enabled = bool(enabled)
        self.sample_rate = int(sample_rate)
        self.threshold = float(threshold)
        self._lock = threading.Lock()
        self._backend_failed = False

    @staticmethod
    def _energy_fallback(samples: np.ndarray) -> VoiceGateResult:
        if samples.size == 0:
            return VoiceGateResult(
                samples=samples,
                start_offset_seconds=0.0,
                speech_detected=False,
                speech_ratio=0.0,
                backend="energy-fallback",
            )
        rms = float(
            np.sqrt(np.mean(np.square(samples), dtype=np.float64))
        )
        detected = rms >= 0.0025
        return VoiceGateResult(
            samples=samples if detected else np.empty(0, dtype=np.float32),
            start_offset_seconds=0.0,
            speech_detected=detected,
            speech_ratio=1.0 if detected else 0.0,
            backend="energy-fallback",
        )

    def process(self, samples: np.ndarray) -> VoiceGateResult:
        audio = np.asarray(samples, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            return VoiceGateResult(
                samples=audio,
                start_offset_seconds=0.0,
                speech_detected=False,
                speech_ratio=0.0,
                backend="empty",
            )
        if not self.enabled:
            return VoiceGateResult(
                samples=audio,
                start_offset_seconds=0.0,
                speech_detected=True,
                speech_ratio=1.0,
                backend="disabled",
            )
        if self._backend_failed:
            return self._energy_fallback(audio)

        try:
            from faster_whisper.vad import (
                VadOptions,
                get_speech_timestamps,
            )

            options = VadOptions(
                threshold=self.threshold,
                min_speech_duration_ms=160,
                max_speech_duration_s=12.0,
                min_silence_duration_ms=260,
                speech_pad_ms=120,
            )
            with self._lock:
                regions = get_speech_timestamps(
                    audio,
                    options,
                    sampling_rate=self.sample_rate,
                )
        except Exception:
            self._backend_failed = True
            return self._energy_fallback(audio)

        if not regions:
            return VoiceGateResult(
                samples=np.empty(0, dtype=np.float32),
                start_offset_seconds=0.0,
                speech_detected=False,
                speech_ratio=0.0,
                backend="silero",
            )

        first = max(0, int(regions[0]["start"]))
        last = min(audio.size, int(regions[-1]["end"]))
        if last <= first:
            return VoiceGateResult(
                samples=np.empty(0, dtype=np.float32),
                start_offset_seconds=0.0,
                speech_detected=False,
                speech_ratio=0.0,
                backend="silero",
            )

        speech_samples = sum(
            max(0, int(region["end"]) - int(region["start"]))
            for region in regions
        )
        return VoiceGateResult(
            samples=audio[first:last],
            start_offset_seconds=first / float(self.sample_rate),
            speech_detected=True,
            speech_ratio=min(1.0, speech_samples / float(audio.size)),
            backend="silero",
        )
