from __future__ import annotations

import collections
import queue
import os
import subprocess
import sys
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .application_audio import (
    WINDOWS_APP_AUDIO_HELPER,
    application_audio_support,
    parse_application_pid,
)
from .paths import RECORDING_IN_PROGRESS_DIR, TEMP_DIR
from .resource_policy import resource_policy

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
    available: bool = True
    unavailable_reason: str = ""

    @property
    def label(self) -> str:
        default_suffix = " (System default)" if self.is_default else ""
        availability_suffix = " — Unavailable" if not self.available else ""
        return f"{self.index}: {self.name}{default_suffix}{availability_suffix}"


@dataclass(frozen=True, slots=True)
class AudioOutputInfo:
    index: int
    name: str
    sample_rate: float
    max_output_channels: int
    is_default: bool = False
    available: bool = True
    unavailable_reason: str = ""

    @property
    def label(self) -> str:
        default_suffix = " (System default output)" if self.is_default else ""
        availability_suffix = " — Unavailable" if not self.available else ""
        return f"{self.index}: {self.name}{default_suffix}{availability_suffix}"


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



def _probe_microphone(sd, index: int, sample_rate: float) -> tuple[bool, str]:
    try:
        sd.check_input_settings(
            device=index,
            channels=1,
            samplerate=sample_rate,
            dtype="float32",
        )
        return True, ""
    except Exception as exc:
        message = str(exc).strip()
        return False, message or "The device cannot currently be opened."


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
        sample_rate = float(device.get("default_samplerate", 44_100.0))
        available, reason = _probe_microphone(sd, index, sample_rate)
        microphones.append(
            MicrophoneInfo(
                index=index,
                name=str(device.get("name", f"Input {index}")),
                sample_rate=sample_rate,
                max_input_channels=channels,
                is_default=index == default_index,
                available=available,
                unavailable_reason=reason,
            )
        )

    microphones.sort(key=lambda item: (not item.available, not item.is_default, item.index))
    return microphones


def detect_default_microphone_label() -> str:
    microphones = list_microphones()
    for microphone in microphones:
        if microphone.is_default and microphone.available:
            return microphone.label
    for microphone in microphones:
        if microphone.available:
            return microphone.label
    return "No available microphone detected"


def parse_microphone_index(label: str) -> int | None:
    if label == "Default input" or ":" not in label:
        return None
    prefix = label.split(":", 1)[0].strip()
    try:
        return int(prefix)
    except ValueError:
        return None


def _default_output_index(sd) -> int | None:
    try:
        default = sd.default.device
        if isinstance(default, (tuple, list)):
            index = default[1]
        else:
            index = int(default)
        return int(index) if int(index) >= 0 else None
    except Exception:
        return None


def _probe_audio_output(
    sd,
    index: int,
    sample_rate: float,
    max_output_channels: int,
) -> tuple[bool, str]:
    channels = 2 if max_output_channels >= 2 else 1
    try:
        sd.check_output_settings(
            device=index,
            channels=channels,
            samplerate=sample_rate,
            dtype="float32",
        )
        return True, ""
    except Exception as exc:
        message = str(exc).strip()
        return False, message or "The playback device cannot currently be opened."


def list_audio_outputs() -> list[AudioOutputInfo]:
    try:
        import sounddevice as sd
    except ImportError:
        return []

    default_index = _default_output_index(sd)
    devices = sd.query_devices()
    outputs: list[AudioOutputInfo] = []

    for index, device in enumerate(devices):
        channels = int(device.get("max_output_channels", 0))
        if channels <= 0:
            continue
        sample_rate = float(device.get("default_samplerate", 44_100.0))
        available, reason = _probe_audio_output(
            sd,
            index,
            sample_rate,
            channels,
        )
        outputs.append(
            AudioOutputInfo(
                index=index,
                name=str(device.get("name", f"Output {index}")),
                sample_rate=sample_rate,
                max_output_channels=channels,
                is_default=index == default_index,
                available=available,
                unavailable_reason=reason,
            )
        )

    outputs.sort(
        key=lambda item: (
            not item.available,
            not item.is_default,
            item.index,
        )
    )
    return outputs


def detect_default_audio_output_label() -> str:
    outputs = list_audio_outputs()
    for output in outputs:
        if output.is_default and output.available:
            return output.label
    for output in outputs:
        if output.available:
            return output.label
    return "No available playback device detected"


def parse_audio_output_index(label: str) -> int | None:
    if not label or label == "System default output" or ":" not in label:
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


def recording_parts_dir(path: Path) -> Path:
    return RECORDING_IN_PROGRESS_DIR / path.stem


def list_recording_parts(path: Path) -> list[Path]:
    folder = recording_parts_dir(path)
    if not folder.is_dir():
        return []
    return sorted(folder.glob("part_*.wav"))


def combine_wav_parts(parts: list[Path], output_path: Path) -> int:
    """Combine compatible mono PCM WAV parts without loading them into memory."""
    valid: list[Path] = []
    parameters: tuple[int, int, int] | None = None

    for part in parts:
        try:
            with wave.open(str(part), "rb") as wav_file:
                current = (
                    wav_file.getnchannels(),
                    wav_file.getsampwidth(),
                    wav_file.getframerate(),
                )
                if parameters is None:
                    parameters = current
                if current != parameters:
                    continue
            valid.append(part)
        except (OSError, wave.Error):
            continue

    if not valid or parameters is None:
        raise RuntimeError("No recoverable WAV recording parts were found.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".combining")
    with wave.open(str(temporary), "wb") as output:
        output.setnchannels(parameters[0])
        output.setsampwidth(parameters[1])
        output.setframerate(parameters[2])
        for part in valid:
            with wave.open(str(part), "rb") as source:
                while True:
                    frames = source.readframes(65_536)
                    if not frames:
                        break
                    output.writeframesraw(frames)
    temporary.replace(output_path)
    return len(valid)


def recover_rolling_recording(path: Path) -> bool:
    """Recover a final WAV from closed rollover parts after an interrupted session."""
    if path.is_file():
        return True
    parts = list_recording_parts(path)
    if not parts:
        return False
    try:
        combine_wav_parts(parts, path)
        if path.is_file():
            return True
        return False
    except Exception:
        return False


class WavRecorder(threading.Thread):
    """Write crash-contained WAV parts and combine them on a normal stop."""

    def __init__(
        self,
        path: Path,
        sample_rate: float,
        *,
        rollover_seconds: float = 5 * 60,
    ) -> None:
        super().__init__(name="wav-recorder", daemon=True)
        self.path = path
        self.sample_rate = int(round(sample_rate))
        self.rollover_seconds = max(60.0, float(rollover_seconds))
        self.queue: queue.Queue[np.ndarray | None] = queue.Queue(
            maxsize=resource_policy(True).recorder_queue_blocks
        )
        self.error: str | None = None
        self.completed = threading.Event()
        self.part_paths: list[Path] = []

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
        self.join(timeout=30)

    def _part_path(self, index: int) -> Path:
        folder = recording_parts_dir(self.path)
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"part_{index:04d}.wav"

    def _open_part(self, index: int):
        part_path = self._part_path(index)
        wav_file = wave.open(str(part_path), "wb")
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(self.sample_rate)
        self.part_paths.append(part_path)
        return wav_file

    def _combine_and_clean(self) -> None:
        combine_wav_parts(self.part_paths, self.path)

    def run(self) -> None:
        wav_file = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            frames_per_part = max(
                self.sample_rate * 60,
                int(round(self.sample_rate * self.rollover_seconds)),
            )
            current_frames = 0
            part_index = 1
            wav_file = self._open_part(part_index)

            while True:
                samples = self.queue.get()
                if samples is None:
                    break
                pcm = np.clip(samples, -1.0, 1.0)
                pcm = (pcm * 32767.0).astype("<i2", copy=False)
                wav_file.writeframesraw(pcm.tobytes())
                current_frames += int(pcm.size)

                if current_frames >= frames_per_part:
                    wav_file.close()
                    wav_file = None
                    part_index += 1
                    current_frames = 0
                    wav_file = self._open_part(part_index)

            if wav_file is not None:
                wav_file.close()
                wav_file = None
            self._combine_and_clean()
        except Exception as exc:  # pragma: no cover - hardware/filesystem dependent
            self.error = str(exc).strip() or "unknown WAV recording error"
        finally:
            if wav_file is not None:
                try:
                    wav_file.close()
                except Exception:
                    pass
            self.completed.set()


class _CaptureOutputMixin:
    output_queue: queue.Queue[AudioBlock | None]
    recording_path: Path
    event_callback: Callable[[str, Any], None] | None
    _sample_cursor: int
    _source_rate: float
    _recorder: WavRecorder | None
    _end_sent: bool
    _paused: threading.Event
    _last_level_emit: float
    _quiet_since: float | None

    def _event(self, level: str, message: Any) -> None:
        if self.event_callback:
            self.event_callback(level, message)

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._paused.set()
        else:
            self._paused.clear()
            self._quiet_since = None

    def _report_audio_level(self, raw_mono: np.ndarray) -> None:
        now = time.monotonic()
        if now - self._last_level_emit < 0.15:
            return
        self._last_level_emit = now

        rms = float(np.sqrt(np.mean(np.square(raw_mono), dtype=np.float64)))
        peak = float(np.max(np.abs(raw_mono))) if raw_mono.size else 0.0
        if rms < 0.0015:
            if self._quiet_since is None:
                self._quiet_since = now
        else:
            self._quiet_since = None

        quiet_seconds = 0.0 if self._quiet_since is None else now - self._quiet_since
        self._event(
            "audio_level",
            {
                "rms": rms,
                "peak": peak,
                "clipping": peak >= 0.98,
                "quiet_seconds": quiet_seconds,
                "paused": self._paused.is_set(),
            },
        )

    def _submit_samples(self, raw_mono: np.ndarray) -> None:
        raw_mono = np.asarray(raw_mono, dtype=np.float32).reshape(-1)
        if raw_mono.size == 0:
            return

        self._report_audio_level(raw_mono)
        if self._paused.is_set():
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


class MicrophoneOutputMonitor:
    """Route microphone samples to a selected playback device.

    Monitoring is output-only. The microphone capture callback places copies of
    raw samples into a bounded queue, so playback cannot block transcription or
    WAV recording. The original captured samples remain unchanged.
    """

    def __init__(
        self,
        output_label: str,
        event_callback: Callable[[str, Any], None] | None = None,
    ) -> None:
        self.output_label = output_label
        self.event_callback = event_callback
        self._queue: queue.Queue[tuple[np.ndarray, float] | None] = queue.Queue(
            maxsize=resource_policy(True).monitor_queue_blocks
        )
        self._stream = None
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._enabled = False
        self._source_rate = 44_100.0
        self._output_rate = 44_100.0
        self._output_channels = 2
        self._warning_sent = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _event(self, kind: str, payload: Any) -> None:
        if self.event_callback is not None:
            self.event_callback(kind, payload)

    def start(self, source_rate: float) -> None:
        with self._lock:
            if self._enabled:
                return
            try:
                import sounddevice as sd
            except ImportError as exc:
                raise RuntimeError(
                    "Microphone listening is not included in this package."
                ) from exc

            output_index = parse_audio_output_index(self.output_label)
            try:
                info = sd.query_devices(output_index, "output")
            except Exception as exc:
                raise RuntimeError(
                    "The selected playback device could not be found."
                ) from exc

            output_rate = float(info.get("default_samplerate", source_rate))
            max_channels = int(info.get("max_output_channels", 0))
            if max_channels <= 0:
                raise RuntimeError(
                    "The selected device cannot play microphone audio."
                )
            output_channels = 2 if max_channels >= 2 else 1

            try:
                stream = sd.OutputStream(
                    device=output_index,
                    channels=output_channels,
                    samplerate=output_rate,
                    dtype="float32",
                    latency="low",
                )
                stream.start()
            except Exception as exc:
                message = str(exc).strip()
                raise RuntimeError(
                    "The selected playback device could not be opened for "
                    "microphone listening. Use headphones and choose another "
                    f"output if needed. Details: {message or 'output unavailable'}"
                ) from exc

            self._source_rate = float(source_rate)
            self._output_rate = output_rate
            self._output_channels = output_channels
            self._stream = stream
            self._stop_event.clear()
            self._warning_sent = False
            self._enabled = True
            self._worker = threading.Thread(
                target=self._playback_loop,
                name="microphone-playback-monitor",
                daemon=True,
            )
            self._worker.start()

    def submit(self, samples: np.ndarray, source_rate: float) -> None:
        if not self._enabled:
            return
        item = (
            np.asarray(samples, dtype=np.float32).reshape(-1).copy(),
            float(source_rate),
        )
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(item)
            except queue.Full:
                if not self._warning_sent:
                    self._warning_sent = True
                    self._event(
                        "warning",
                        "Microphone listening briefly fell behind. "
                        "Transcription and the WAV recording were not interrupted.",
                    )

    def _playback_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.20)
            except queue.Empty:
                continue
            if item is None:
                break
            samples, source_rate = item
            if samples.size == 0:
                continue
            output = resample_linear(
                samples,
                source_rate,
                int(round(self._output_rate)),
            )
            if self._output_channels > 1:
                output = np.repeat(
                    output.reshape(-1, 1),
                    self._output_channels,
                    axis=1,
                )
            else:
                output = output.reshape(-1, 1)
            stream = self._stream
            if stream is None:
                continue
            try:
                stream.write(output)
            except Exception as exc:
                if not self._warning_sent:
                    self._warning_sent = True
                    self._event(
                        "warning",
                        "Microphone listening stopped, but transcription and "
                        "recording are continuing. "
                        f"Details: {str(exc).strip() or 'playback error'}",
                    )
                break

    def stop(self) -> None:
        """Stop playback promptly without holding the caller on driver I/O."""
        with self._lock:
            if not self._enabled and self._stream is None and self._worker is None:
                return

            self._enabled = False
            self._stop_event.set()
            stream = self._stream
            self._stream = None
            worker = self._worker
            self._worker = None

            if stream is not None:
                try:
                    abort = getattr(stream, "abort", None)
                    if callable(abort):
                        abort()
                except Exception:
                    pass

            try:
                self._queue.put_nowait(None)
            except queue.Full:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._queue.put_nowait(None)
                except queue.Full:
                    pass

        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=1.0)

        if stream is not None:
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass

        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def set_enabled(self, enabled: bool, source_rate: float) -> bool:
        if enabled:
            try:
                self.start(source_rate)
            except RuntimeError as exc:
                self._event("warning", str(exc))
                return False
            return True
        self.stop()
        return True

    def set_output_label(self, label: str, source_rate: float) -> bool:
        clean = label.strip()
        if not clean or clean == self.output_label:
            return True
        was_enabled = self._enabled
        previous = self.output_label
        self.stop()
        self.output_label = clean
        if not was_enabled:
            return True
        try:
            self.start(source_rate)
        except RuntimeError as exc:
            self.output_label = previous
            try:
                self.start(source_rate)
            except RuntimeError:
                pass
            self._event("warning", str(exc))
            return False
        return True


class MicrophoneCapture(_CaptureOutputMixin):
    def __init__(
        self,
        output_queue: queue.Queue[AudioBlock | None],
        microphone_index: int | None,
        recording_path: Path,
        event_callback: Callable[[str, str], None] | None = None,
        monitor_enabled: bool = False,
        monitor_output_label: str = "System default output",
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
        self._paused = threading.Event()
        self._last_level_emit = 0.0
        self._quiet_since: float | None = None
        self.monitor_enabled = bool(monitor_enabled)
        self.monitor_output_label = monitor_output_label
        self._output_monitor = MicrophoneOutputMonitor(
            monitor_output_label,
            event_callback=event_callback,
        )

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
            raw = np.asarray(indata[:, 0], dtype=np.float32)
            self._output_monitor.submit(raw, self._source_rate)
            self._submit_samples(raw)

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
            if self.monitor_enabled:
                self.monitor_enabled = self._output_monitor.set_enabled(
                    True,
                    self._source_rate,
                )
        except Exception as exc:
            self._closed = True
            self._finish_wav()
            message = str(exc).strip()
            raise RuntimeError(
                "The selected microphone could not be opened. Check microphone permission "
                f"and try again. Details: {message or 'microphone unavailable'}"
            ) from exc

    def set_monitor_enabled(self, enabled: bool) -> bool:
        self.monitor_enabled = bool(enabled)
        result = self._output_monitor.set_enabled(
            self.monitor_enabled,
            self._source_rate,
        )
        if not result:
            self.monitor_enabled = False
        return result

    def set_monitor_output(self, label: str) -> bool:
        result = self._output_monitor.set_output_label(
            label,
            self._source_rate,
        )
        if result:
            self.monitor_output_label = label
        return result

    def stop(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._output_monitor.stop()

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
        self._paused = threading.Event()
        self._last_level_emit = 0.0
        self._quiet_since: float | None = None

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


def _wave_data_offset(path: Path) -> int | None:
    try:
        with path.open("rb") as handle:
            header = handle.read(256)
    except OSError:
        return None
    marker = header.find(b"data")
    if marker < 0 or marker + 8 > len(header):
        return None
    return marker + 8


def _decode_process_loopback_pcm(data: bytes) -> np.ndarray:
    usable = len(data) - (len(data) % 4)
    if usable <= 0:
        return np.empty(0, dtype=np.float32)
    stereo = np.frombuffer(data[:usable], dtype="<i2").reshape(-1, 2)
    return stereo.astype(np.float32).mean(axis=1) / 32768.0


class ApplicationAudioCapture(_CaptureOutputMixin):
    """Windows process-loopback capture using the optional native helper."""

    def __init__(
        self,
        output_queue: queue.Queue[AudioBlock | None],
        target_label: str,
        recording_path: Path,
        *,
        enabled: bool = True,
        event_callback: Callable[[str, Any], None] | None = None,
        monitor_only: bool = False,
    ) -> None:
        self.output_queue = output_queue
        self.target_label = target_label
        self.recording_path = recording_path
        self.event_callback = event_callback
        self.monitor_only = monitor_only
        self._sample_cursor = 0
        self._source_rate = 44_100.0
        self._recorder: WavRecorder | None = None
        self._end_sent = False
        self._closed = True
        self._stop_event = threading.Event()
        self._enabled = threading.Event()
        if enabled:
            self._enabled.set()
        self._worker: threading.Thread | None = None
        self._process: subprocess.Popen | None = None
        self._process_lock = threading.Lock()
        self._target_lock = threading.Lock()
        self._target_generation = 0
        self.selected_input_name = "Selected app audio"
        self._paused = threading.Event()
        self._last_level_emit = 0.0
        self._quiet_since: float | None = None

    def _submit_samples(self, raw_mono: np.ndarray) -> None:
        if self.monitor_only:
            self._report_audio_level(np.asarray(raw_mono, dtype=np.float32))
            return
        super()._submit_samples(raw_mono)

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self._enabled.set()
            self._event("status", "Selected-app listening turned on.")
        else:
            self._enabled.clear()
            self._terminate_helper()
            self._event("app_audio_toggle", {"enabled": False})

    def set_target(self, label: str) -> None:
        with self._target_lock:
            if label == self.target_label:
                return
            self.target_label = label
            self._target_generation += 1
        self._terminate_helper()
        self._event("status", f"Selected-app audio changed to: {label}")

    def start(self) -> None:
        supported, reason = application_audio_support()
        if not supported:
            raise RuntimeError(reason)
        if parse_application_pid(self.target_label) is None:
            raise RuntimeError(
                "Choose a running Windows application before starting selected-app audio."
            )
        self._closed = False
        self._stop_event.clear()
        self._end_sent = False
        self._sample_cursor = 0
        self.selected_input_name = f"Selected app — {self.target_label}"
        if not self.monitor_only:
            self._recorder = WavRecorder(self.recording_path, self._source_rate)
            self._recorder.start()
        self._worker = threading.Thread(
            target=self._capture_loop,
            name="application-audio-capture",
            daemon=True,
        )
        self._worker.start()

    def _target_snapshot(self) -> tuple[str, int]:
        with self._target_lock:
            return self.target_label, self._target_generation

    def _terminate_helper(self) -> None:
        with self._process_lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
        except OSError:
            pass

    def _capture_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                if not self._enabled.is_set():
                    self._event(
                        "audio_level",
                        {
                            "rms": 0.0,
                            "peak": 0.0,
                            "clipping": False,
                            "quiet_seconds": 0.0,
                            "paused": False,
                            "source_muted": True,
                        },
                    )
                    self._stop_event.wait(0.25)
                    continue

                label, generation = self._target_snapshot()
                pid = parse_application_pid(label)
                if pid is None:
                    self._stop_event.wait(0.25)
                    continue
                self._capture_helper_window(pid, generation)
        except Exception as exc:
            if not self._stop_event.is_set():
                self._event(
                    "error",
                    "Selected-app audio stopped unexpectedly. "
                    f"Details: {str(exc).strip() or 'unknown app-audio error'}",
                )
        finally:
            self._terminate_helper()
            if not self.monitor_only:
                self._finish_wav()
                self._signal_end()

    def _capture_helper_window(self, pid: int, generation: int) -> None:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        wav_path = TEMP_DIR / f"app-audio-{os.getpid()}-{pid}-{time.time_ns()}.wav"
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        command = [
            str(WINDOWS_APP_AUDIO_HELPER),
            str(pid),
            "includetree",
            str(wav_path),
        ]
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
            )
        except OSError as exc:
            raise RuntimeError(
                "The selected-app audio helper could not start."
            ) from exc

        with self._process_lock:
            self._process = process

        offset: int | None = None
        last_read = 0
        try:
            while not self._stop_event.is_set():
                _label, current_generation = self._target_snapshot()
                if current_generation != generation or not self._enabled.is_set():
                    break

                if offset is None and wav_path.is_file():
                    offset = _wave_data_offset(wav_path)
                    if offset is not None:
                        last_read = offset

                if offset is not None:
                    try:
                        size = wav_path.stat().st_size
                    except OSError:
                        size = last_read
                    available = size - last_read
                    available -= available % 4
                    if available > 0:
                        try:
                            with wav_path.open("rb") as handle:
                                handle.seek(last_read)
                                payload = handle.read(available)
                        except OSError:
                            payload = b""
                        if payload:
                            last_read += len(payload)
                            mono = _decode_process_loopback_pcm(payload)
                            if mono.size:
                                self._submit_samples(mono)

                if process.poll() is not None:
                    # Read a final completed block before starting the next
                    # ten-second helper window.
                    if offset is not None:
                        try:
                            size = wav_path.stat().st_size
                            available = size - last_read
                            available -= available % 4
                            if available > 0:
                                with wav_path.open("rb") as handle:
                                    handle.seek(last_read)
                                    payload = handle.read(available)
                                mono = _decode_process_loopback_pcm(payload)
                                if mono.size:
                                    self._submit_samples(mono)
                        except OSError:
                            pass
                    break
                self._stop_event.wait(0.06)
        finally:
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except Exception:
                    try:
                        process.kill()
                    except OSError:
                        pass
            with self._process_lock:
                if self._process is process:
                    self._process = None
            try:
                wav_path.unlink(missing_ok=True)
            except OSError:
                pass

    def stop(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stop_event.set()
        self._terminate_helper()
        if self._worker is not None:
            self._worker.join(timeout=4)
        self._worker = None
        if not self.monitor_only:
            self._finish_wav()
            self._signal_end()


class AudioInputMonitor:
    """Lightweight input test that does not transcribe or save a recording."""

    def __init__(
        self,
        *,
        source_mode: str,
        input_label: str,
        microphone_index: int | None,
        application_enabled: bool,
        event_callback: Callable[[dict[str, Any]], None],
        microphone_monitor_enabled: bool = False,
        microphone_monitor_output_label: str = "System default output",
    ) -> None:
        self.source_mode = source_mode
        self.input_label = input_label
        self.microphone_index = microphone_index
        self.application_enabled = application_enabled
        self.event_callback = event_callback
        self._stream = None
        self._context = None
        self._recorder = None
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._app_capture: ApplicationAudioCapture | None = None
        self._last_emit = 0.0
        self.microphone_monitor_enabled = bool(microphone_monitor_enabled)
        self.microphone_monitor_output_label = microphone_monitor_output_label
        self._microphone_output_monitor = MicrophoneOutputMonitor(
            microphone_monitor_output_label,
        )
        self._microphone_sample_rate = 44_100.0
        self._stop_lock = threading.Lock()
        self._stopped = False

    def _emit(self, samples: np.ndarray) -> None:
        now = time.monotonic()
        if now - self._last_emit < 0.12:
            return
        self._last_emit = now
        mono = np.asarray(samples, dtype=np.float32).reshape(-1)
        if mono.size == 0:
            return
        rms = float(np.sqrt(np.mean(np.square(mono), dtype=np.float64)))
        peak = float(np.max(np.abs(mono)))
        self.event_callback(
            {
                "rms": rms,
                "peak": peak,
                "clipping": peak >= 0.98,
                "quiet_seconds": 0.0,
                "paused": False,
                "input_test": True,
            }
        )

    def start(self) -> None:
        from .config import AUDIO_SOURCE_APPLICATION, AUDIO_SOURCE_SYSTEM

        self._stop_event.clear()
        if self.source_mode == AUDIO_SOURCE_APPLICATION:
            queue_stub: queue.Queue[AudioBlock | None] = queue.Queue(maxsize=2)
            self._app_capture = ApplicationAudioCapture(
                queue_stub,
                self.input_label,
                TEMP_DIR / "input-test-unused.wav",
                enabled=self.application_enabled,
                event_callback=self._on_app_event,
                monitor_only=True,
            )
            self._app_capture.start()
            return

        if self.source_mode == AUDIO_SOURCE_SYSTEM:
            info, source = resolve_system_audio_source(self.input_label)
            self._context = source.recorder(
                samplerate=SYSTEM_AUDIO_SAMPLE_RATE,
                channels=None,
                blocksize=4_096,
            )
            self._recorder = self._context.__enter__()
            self._worker = threading.Thread(
                target=self._system_loop,
                name="system-input-test",
                daemon=True,
            )
            self._worker.start()
            return

        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("Microphone testing is not included in this package.") from exc
        device_info = sd.query_devices(self.microphone_index, "input")
        sample_rate = float(device_info["default_samplerate"])
        self._microphone_sample_rate = sample_rate
        blocksize = max(256, int(sample_rate * 0.08))

        def callback(indata, _frames, _time_info, _status) -> None:
            raw = np.asarray(indata[:, 0], dtype=np.float32)
            self._microphone_output_monitor.submit(raw, sample_rate)
            self._emit(raw)

        self._stream = sd.InputStream(
            device=self.microphone_index,
            channels=1,
            samplerate=sample_rate,
            blocksize=blocksize,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()
        if self.microphone_monitor_enabled:
            try:
                self._microphone_output_monitor.start(sample_rate)
            except RuntimeError:
                self._stream.stop()
                self._stream.close()
                self._stream = None
                raise

    def set_microphone_monitor_enabled(self, enabled: bool) -> bool:
        self.microphone_monitor_enabled = bool(enabled)
        result = self._microphone_output_monitor.set_enabled(
            self.microphone_monitor_enabled,
            self._microphone_sample_rate,
        )
        if not result:
            self.microphone_monitor_enabled = False
        return result

    def set_microphone_monitor_output(self, label: str) -> bool:
        result = self._microphone_output_monitor.set_output_label(
            label,
            self._microphone_sample_rate,
        )
        if result:
            self.microphone_monitor_output_label = label
        return result

    def _on_app_event(self, kind: str, payload: Any) -> None:
        if kind == "audio_level" and isinstance(payload, dict):
            payload = dict(payload)
            payload["input_test"] = True
            self.event_callback(payload)

    def _system_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                recorder = self._recorder
                if recorder is None:
                    break
                data = recorder.record(numframes=3_840)
                mono = downmix_to_mono(data)
                if mono.size:
                    self._emit(mono)
        except Exception:
            pass

    def stop(self) -> None:
        """Release a test input safely and idempotently.

        The GUI runs this on a cleanup worker because some Windows drivers may
        wait inside stop/close. Resources are detached and aborted first.
        """
        with self._stop_lock:
            if self._stopped:
                return
            self._stopped = True
            self._stop_event.set()
            app_capture = self._app_capture
            self._app_capture = None
            stream = self._stream
            self._stream = None
            worker = self._worker
            self._worker = None
            context = self._context
            self._context = None
            self._recorder = None

        self._microphone_output_monitor.stop()

        if stream is not None:
            try:
                abort = getattr(stream, "abort", None)
                if callable(abort):
                    abort()
            except Exception:
                pass

        if context is not None:
            try:
                context.__exit__(None, None, None)
            except Exception:
                pass

        if app_capture is not None:
            try:
                app_capture.stop()
            except Exception:
                pass

        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=1.0)

        if stream is not None:
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass

class SpeechSegmenter(threading.Thread):
    def __init__(
        self,
        input_queue: queue.Queue[AudioBlock | None],
        output_queue: queue.Queue[SpeechChunk | None],
        rms_threshold: float,
        min_speech_seconds: float = 0.25,
        end_silence_seconds: float = 0.55,
        max_chunk_seconds: float = 12.0,
        pre_roll_seconds: float = 0.25,
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
        active_duration = 0.0

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
                    active_duration = sum(
                        item.duration for item in active_blocks
                    )
                    pre_roll.clear()
                    pre_roll_duration = 0.0
                continue

            active_blocks.append(block)
            active_duration += block.duration
            if speech:
                silence_seconds = 0.0
                speech_seconds += block.duration
            else:
                silence_seconds += block.duration

            phrase_finished = silence_seconds >= self.end_silence_seconds
            maximum_reached = active_duration >= self.max_chunk_seconds

            if phrase_finished or maximum_reached:
                self._emit(active_blocks, speech_seconds)
                active = False
                active_blocks = []
                silence_seconds = 0.0
                speech_seconds = 0.0
                active_duration = 0.0
                pre_roll.clear()
                pre_roll_duration = 0.0
