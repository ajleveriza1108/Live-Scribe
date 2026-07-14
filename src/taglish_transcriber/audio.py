from __future__ import annotations

import collections
import queue
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

TARGET_SAMPLE_RATE = 16_000


@dataclass(frozen=True, slots=True)
class MicrophoneInfo:
    index: int
    name: str
    sample_rate: float
    max_input_channels: int
    is_default: bool = False

    @property
    def label(self) -> str:
        suffix = " (System default)" if self.is_default else ""
        return f"{self.index}: {self.name}{suffix}"


@dataclass(frozen=True, slots=True)
class AudioBlock:
    samples: np.ndarray
    start: float

    @property
    def duration(self) -> float:
        return float(self.samples.size) / TARGET_SAMPLE_RATE


@dataclass(frozen=True, slots=True)
class SpeechChunk:
    samples: np.ndarray
    start: float
    end: float


def _default_input_index(sd) -> int | None:
    try:
        default = sd.default.device
        index = default[0] if isinstance(default, (tuple, list)) else int(default)
        return int(index) if int(index) >= 0 else None
    except Exception:
        return None


def list_microphones() -> list[MicrophoneInfo]:
    try:
        import sounddevice as sd
    except ImportError:
        return []

    default_index = _default_input_index(sd)
    devices = sd.query_devices()
    microphones: list[MicrophoneInfo] = []

    for index, device in enumerate(devices):
        channels = int(device.get("max_input_channels", 0))
        if channels <= 0:
            continue
        microphones.append(
            MicrophoneInfo(
                index=index,
                name=str(device.get("name", f"Input {index}")),
                sample_rate=float(device.get("default_samplerate", 44_100.0)),
                max_input_channels=channels,
                is_default=index == default_index,
            )
        )

    microphones.sort(key=lambda item: (not item.is_default, item.index))
    return microphones


def detect_default_microphone_label() -> str:
    microphones = list_microphones()
    for microphone in microphones:
        if microphone.is_default:
            return microphone.label
    return microphones[0].label if microphones else "Default input"


def parse_microphone_index(label: str) -> int | None:
    if label == "Default input" or ":" not in label:
        return None
    prefix = label.split(":", 1)[0].strip()
    try:
        return int(prefix)
    except ValueError:
        return None


def resample_linear(
    samples: np.ndarray,
    source_rate: float,
    target_rate: int = TARGET_SAMPLE_RATE,
) -> np.ndarray:
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if samples.size == 0:
        return samples

    if abs(source_rate - target_rate) < 1.0:
        return samples

    target_length = max(1, int(round(samples.size * target_rate / source_rate)))
    source_positions = np.linspace(
        0.0, 1.0, num=samples.size, endpoint=False, dtype=np.float64
    )
    target_positions = np.linspace(
        0.0, 1.0, num=target_length, endpoint=False, dtype=np.float64
    )
    return np.interp(target_positions, source_positions, samples).astype(np.float32)


class WavRecorder(threading.Thread):
    """Write microphone blocks to a PCM WAV file away from the audio callback."""

    def __init__(self, path: Path, sample_rate: float) -> None:
        super().__init__(name="wav-recorder", daemon=True)
        self.path = path
        self.sample_rate = int(round(sample_rate))
        self.queue: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=600)
        self.error: str | None = None
        self.completed = threading.Event()

    def submit(self, samples: np.ndarray) -> bool:
        try:
            self.queue.put_nowait(np.asarray(samples, dtype=np.float32).copy())
            return True
        except queue.Full:
            return False

    def close(self) -> None:
        try:
            self.queue.put_nowait(None)
        except queue.Full:
            self.queue.put(None)
        self.join(timeout=15)

    def run(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(self.path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                while True:
                    samples = self.queue.get()
                    if samples is None:
                        break
                    pcm = np.clip(samples, -1.0, 1.0)
                    pcm = (pcm * 32767.0).astype("<i2", copy=False)
                    wav_file.writeframesraw(pcm.tobytes())
        except Exception as exc:  # pragma: no cover - hardware/filesystem dependent
            self.error = str(exc).strip() or "unknown WAV recording error"
        finally:
            self.completed.set()


class MicrophoneCapture:
    def __init__(
        self,
        output_queue: queue.Queue[AudioBlock | None],
        microphone_index: int | None,
        recording_path: Path,
        event_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        self.output_queue = output_queue
        self.microphone_index = microphone_index
        self.recording_path = recording_path
        self.event_callback = event_callback
        self._stream = None
        self._sample_cursor = 0
        self._source_rate = 44_100.0
        self._closed = True
        self._recorder: WavRecorder | None = None
        self.selected_microphone_name = "Default input"

    def _event(self, level: str, message: str) -> None:
        if self.event_callback:
            self.event_callback(level, message)

    def start(self) -> None:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "Microphone support is not included in this package. Download and "
                "extract the complete portable release again."
            ) from exc

        device_info = sd.query_devices(self.microphone_index, "input")
        self._source_rate = float(device_info["default_samplerate"])
        self.selected_microphone_name = str(device_info.get("name", "Default input"))
        blocksize = max(256, int(round(self._source_rate * 0.10)))
        self._sample_cursor = 0
        self._closed = False
        self._recorder = WavRecorder(self.recording_path, self._source_rate)
        self._recorder.start()

        def callback(indata, frames, time_info, status) -> None:
            del frames, time_info
            if status:
                self._event("warning", f"Microphone notice: {status}")

            raw_mono = np.asarray(indata[:, 0], dtype=np.float32)
            if self._recorder is not None and not self._recorder.submit(raw_mono):
                self._event(
                    "warning",
                    "The WAV recorder briefly fell behind. Keep other heavy programs closed.",
                )

            converted = resample_linear(raw_mono, self._source_rate)
            block_start = self._sample_cursor / TARGET_SAMPLE_RATE
            self._sample_cursor += converted.size

            try:
                self.output_queue.put_nowait(
                    AudioBlock(samples=converted, start=block_start)
                )
            except queue.Full:
                self._event(
                    "warning",
                    "Live transcription briefly fell behind. The saved WAV remains available "
                    "for the final accuracy pass.",
                )

        try:
            self._stream = sd.InputStream(
                device=self.microphone_index,
                channels=1,
                samplerate=self._source_rate,
                blocksize=blocksize,
                dtype="float32",
                callback=callback,
            )
            self._stream.start()
        except Exception as exc:
            self._closed = True
            if self._recorder is not None:
                self._recorder.close()
            self._recorder = None
            message = str(exc).strip()
            raise RuntimeError(
                "The selected microphone could not be opened. Check microphone permission "
                f"and try again. Details: {message or 'microphone unavailable'}"
            ) from exc

    def stop(self) -> None:
        if self._closed:
            return
        self._closed = True

        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None
            if self._recorder is not None:
                self._recorder.close()
                if self._recorder.error:
                    self._event(
                        "warning",
                        "The WAV recording could not be completed. " + self._recorder.error,
                    )
                self._recorder = None
            try:
                self.output_queue.put_nowait(None)
            except queue.Full:
                self.output_queue.put(None)


class SpeechSegmenter(threading.Thread):
    def __init__(
        self,
        input_queue: queue.Queue[AudioBlock | None],
        output_queue: queue.Queue[SpeechChunk | None],
        rms_threshold: float,
        min_speech_seconds: float = 0.35,
        end_silence_seconds: float = 0.80,
        max_chunk_seconds: float = 15.0,
        pre_roll_seconds: float = 0.35,
    ) -> None:
        super().__init__(name="speech-segmenter", daemon=True)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.rms_threshold = rms_threshold
        self.min_speech_seconds = min_speech_seconds
        self.end_silence_seconds = end_silence_seconds
        self.max_chunk_seconds = max_chunk_seconds
        self.pre_roll_seconds = pre_roll_seconds

    @staticmethod
    def _rms(samples: np.ndarray) -> float:
        if samples.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(samples), dtype=np.float64)))

    def _emit(self, blocks: list[AudioBlock], speech_seconds: float) -> None:
        if not blocks or speech_seconds < self.min_speech_seconds:
            return
        samples = np.concatenate([block.samples for block in blocks]).astype(
            np.float32, copy=False
        )
        start = blocks[0].start
        end = blocks[-1].start + blocks[-1].duration
        self.output_queue.put(SpeechChunk(samples=samples, start=start, end=end))

    def run(self) -> None:
        pre_roll: collections.deque[AudioBlock] = collections.deque()
        pre_roll_duration = 0.0
        active_blocks: list[AudioBlock] = []
        active = False
        silence_seconds = 0.0
        speech_seconds = 0.0

        while True:
            block = self.input_queue.get()
            if block is None:
                if active:
                    self._emit(active_blocks, speech_seconds)
                self.output_queue.put(None)
                return

            rms = self._rms(block.samples)
            speech = rms >= self.rms_threshold

            if not active:
                pre_roll.append(block)
                pre_roll_duration += block.duration
                while pre_roll and pre_roll_duration > self.pre_roll_seconds:
                    old = pre_roll.popleft()
                    pre_roll_duration -= old.duration

                if speech:
                    active = True
                    active_blocks = list(pre_roll)
                    silence_seconds = 0.0
                    speech_seconds = block.duration
                    pre_roll.clear()
                    pre_roll_duration = 0.0
                continue

            active_blocks.append(block)
            if speech:
                silence_seconds = 0.0
                speech_seconds += block.duration
            else:
                silence_seconds += block.duration

            total_seconds = sum(item.duration for item in active_blocks)
            phrase_finished = silence_seconds >= self.end_silence_seconds
            maximum_reached = total_seconds >= self.max_chunk_seconds

            if phrase_finished or maximum_reached:
                self._emit(active_blocks, speech_seconds)
                active = False
                active_blocks = []
                silence_seconds = 0.0
                speech_seconds = 0.0
                pre_roll.clear()
                pre_roll_duration = 0.0
