from __future__ import annotations

import collections
import queue
import sys
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

TARGET_SAMPLE_RATE = 16_000
SYSTEM_AUDIO_SAMPLE_RATE = 48_000

VIRTUAL_AUDIO_NAME_HINTS = (
    "blackhole",
    "soundflower",
    "loopback",
    "monitor",
    "stereo mix",
    "what u hear",
    "what you hear",
    "vb-audio",
    "vb-cable",
    "virtual cable",
    "cable output",
)


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
class SystemAudioInfo:
    backend_id: Any
    name: str
    is_default: bool = False
    is_native_loopback: bool = True

    @property
    def label(self) -> str:
        suffix = " (System default output)" if self.is_default else ""
        return f"{self.name}{suffix}"


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


def _looks_like_virtual_audio(name: str) -> bool:
    normalized = name.casefold()
    return any(hint in normalized for hint in VIRTUAL_AUDIO_NAME_HINTS)


def _soundcard_sources_with_handles() -> list[tuple[SystemAudioInfo, Any]]:
    """Return system-output sources and their SoundCard microphone handles."""
    try:
        import soundcard as sc
    except ImportError:
        return []

    results: list[tuple[SystemAudioInfo, Any]] = []
    seen: set[str] = set()

    try:
        default_speaker = sc.default_speaker()
        default_speaker_id = getattr(default_speaker, "id", None)
    except Exception:
        default_speaker = None
        default_speaker_id = None

    if sys.platform == "win32":
        # WASAPI exposes every speaker as a loopback microphone.
        try:
            speakers = sc.all_speakers()
        except Exception:
            speakers = []

        for speaker in speakers:
            try:
                loopback = sc.get_microphone(
                    getattr(speaker, "id", getattr(speaker, "name", "")),
                    include_loopback=True,
                )
            except Exception:
                continue

            key = str(getattr(loopback, "id", getattr(speaker, "id", speaker.name)))
            if key in seen:
                continue
            seen.add(key)
            name = str(getattr(speaker, "name", getattr(loopback, "name", "Computer audio")))
            results.append(
                (
                    SystemAudioInfo(
                        backend_id=getattr(loopback, "id", key),
                        name=name,
                        is_default=getattr(speaker, "id", None) == default_speaker_id,
                        is_native_loopback=True,
                    ),
                    loopback,
                )
            )
    else:
        # Linux exposes PulseAudio/PipeWire monitor sources. macOS requires a
        # virtual input such as BlackHole, Loopback, or Soundflower.
        try:
            microphones = sc.all_microphones(include_loopback=True)
        except Exception:
            microphones = []

        for microphone in microphones:
            name = str(getattr(microphone, "name", "System audio"))
            is_loopback = bool(getattr(microphone, "isloopback", False))
            virtual = _looks_like_virtual_audio(name)

            if sys.platform == "darwin" and not virtual:
                continue
            if sys.platform.startswith("linux") and not (is_loopback or virtual):
                continue

            key = str(getattr(microphone, "id", name))
            if key in seen:
                continue
            seen.add(key)

            is_default = False
            if default_speaker is not None:
                speaker_name = str(getattr(default_speaker, "name", "")).casefold()
                is_default = bool(speaker_name and speaker_name in name.casefold())

            results.append(
                (
                    SystemAudioInfo(
                        backend_id=getattr(microphone, "id", key),
                        name=name,
                        is_default=is_default,
                        is_native_loopback=is_loopback,
                    ),
                    microphone,
                )
            )

    results.sort(key=lambda pair: (not pair[0].is_default, pair[0].name.casefold()))
    return results


def list_system_audio_sources() -> list[SystemAudioInfo]:
    return [info for info, _handle in _soundcard_sources_with_handles()]


def detect_default_system_audio_label() -> str:
    sources = list_system_audio_sources()
    for source in sources:
        if source.is_default:
            return source.label
    return sources[0].label if sources else "No system-audio source detected"


def system_audio_setup_help() -> str:
    if sys.platform == "win32":
        return (
            "No Windows system-audio loopback source was detected. Make sure a speaker "
            "or headphones output is enabled, play a short sound, then click Detect again."
        )
    if sys.platform == "darwin":
        return (
            "macOS does not provide native system-audio loopback. Install and configure "
            "a virtual audio device such as BlackHole, route the livestream audio to it, "
            "then click Detect again."
        )
    return (
        "No PulseAudio/PipeWire monitor source was detected. Make sure the livestream "
        "is playing and that a monitor source is available, then click Detect again."
    )


def resolve_system_audio_source(label: str) -> tuple[SystemAudioInfo, Any]:
    sources = _soundcard_sources_with_handles()
    if not sources:
        raise RuntimeError(system_audio_setup_help())

    for info, handle in sources:
        if info.label == label:
            return info, handle

    for info, handle in sources:
        if info.is_default:
            return info, handle

    return sources[0]


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


def downmix_to_mono(samples: np.ndarray) -> np.ndarray:
    """Convert frames x channels data to stable mono float32 audio."""
    array = np.asarray(samples, dtype=np.float32)
    if array.size == 0:
        return np.empty(0, dtype=np.float32)
    if array.ndim == 1:
        return array.reshape(-1)
    if array.ndim != 2:
        return array.reshape(array.shape[0], -1).mean(axis=1, dtype=np.float32)
    if array.shape[1] == 1:
        return array[:, 0]
    return array.mean(axis=1, dtype=np.float32)


class WavRecorder(threading.Thread):
    """Write audio blocks to a PCM WAV file away from capture callbacks."""

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


class _CaptureOutputMixin:
    output_queue: queue.Queue[AudioBlock | None]
    recording_path: Path
    event_callback: Callable[[str, str], None] | None
    _sample_cursor: int
    _source_rate: float
    _recorder: WavRecorder | None
    _end_sent: bool

    def _event(self, level: str, message: str) -> None:
        if self.event_callback:
            self.event_callback(level, message)

    def _submit_samples(self, raw_mono: np.ndarray) -> None:
        raw_mono = np.asarray(raw_mono, dtype=np.float32).reshape(-1)
        if raw_mono.size == 0:
            return

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
                "for the separate verification pass.",
            )

    def _finish_wav(self) -> None:
        if self._recorder is not None:
            self._recorder.close()
            if self._recorder.error:
                self._event(
                    "warning",
                    "The WAV recording could not be completed. " + self._recorder.error,
                )
            self._recorder = None

    def _signal_end(self) -> None:
        if self._end_sent:
            return
        self._end_sent = True
        try:
            self.output_queue.put_nowait(None)
        except queue.Full:
            self.output_queue.put(None)


class MicrophoneCapture(_CaptureOutputMixin):
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
        self._end_sent = False
        self.selected_input_name = "Default input"
        self.selected_microphone_name = self.selected_input_name

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
        self.selected_input_name = str(device_info.get("name", "Default input"))
        self.selected_microphone_name = self.selected_input_name
        blocksize = max(256, int(round(self._source_rate * 0.10)))
        self._sample_cursor = 0
        self._closed = False
        self._end_sent = False
        self._recorder = WavRecorder(self.recording_path, self._source_rate)
        self._recorder.start()

        def callback(indata, frames, time_info, status) -> None:
            del frames, time_info
            if status:
                self._event("warning", f"Microphone notice: {status}")
            self._submit_samples(np.asarray(indata[:, 0], dtype=np.float32))

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
            self._finish_wav()
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
            self._finish_wav()
            self._signal_end()


class SystemAudioCapture(_CaptureOutputMixin):
    """Capture computer playback for live-stream transcription."""

    def __init__(
        self,
        output_queue: queue.Queue[AudioBlock | None],
        source_label: str,
        recording_path: Path,
        event_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        self.output_queue = output_queue
        self.source_label = source_label
        self.recording_path = recording_path
        self.event_callback = event_callback
        self._sample_cursor = 0
        self._source_rate = float(SYSTEM_AUDIO_SAMPLE_RATE)
        self._recorder: WavRecorder | None = None
        self._end_sent = False
        self._closed = True
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._soundcard_context = None
        self._soundcard_recorder = None
        self.selected_input_name = "Computer audio"

    def start(self) -> None:
        try:
            info, source = resolve_system_audio_source(self.source_label)
        except ImportError as exc:
            raise RuntimeError(
                "Computer-audio capture is not included in this package. "
                "Install the complete Live Scribe dependencies and try again."
            ) from exc

        self.selected_input_name = f"Computer audio — {info.name}"
        self._sample_cursor = 0
        self._end_sent = False
        self._closed = False
        self._stop_event.clear()

        try:
            # Record all available channels. SoundCard documents a Windows/WASAPI
            # issue when requesting only one channel; Live Scribe downmixes safely.
            self._soundcard_context = source.recorder(
                samplerate=SYSTEM_AUDIO_SAMPLE_RATE,
                channels=None,
                blocksize=4_096,
            )
            self._soundcard_recorder = self._soundcard_context.__enter__()
        except Exception as exc:
            self._closed = True
            message = str(exc).strip()
            raise RuntimeError(
                "The selected computer-audio source could not be opened. Start playing "
                "the livestream, confirm the correct output device, and try again. "
                f"Details: {message or 'system audio unavailable'}"
            ) from exc

        self._recorder = WavRecorder(self.recording_path, self._source_rate)
        self._recorder.start()
        self._worker = threading.Thread(
            target=self._capture_loop,
            name="system-audio-capture",
            daemon=True,
        )
        self._worker.start()

    def _capture_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                recorder = self._soundcard_recorder
                if recorder is None:
                    break
                data = recorder.record(numframes=4_800)
                mono = downmix_to_mono(data)
                if mono.size:
                    self._submit_samples(mono)
        except Exception as exc:  # pragma: no cover - hardware dependent
            if not self._stop_event.is_set():
                self._event(
                    "error",
                    "Computer-audio capture stopped unexpectedly. "
                    f"Details: {str(exc).strip() or 'unknown audio error'}",
                )
                self._stop_event.set()
                self._finish_wav()
                self._signal_end()

    def _close_soundcard(self) -> None:
        context = self._soundcard_context
        self._soundcard_context = None
        self._soundcard_recorder = None
        if context is not None:
            try:
                context.__exit__(None, None, None)
            except Exception:
                pass

    def stop(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stop_event.set()

        if self._worker is not None:
            self._worker.join(timeout=2.0)
        self._close_soundcard()
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=2.0)
        self._worker = None

        self._finish_wav()
        self._signal_end()


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
