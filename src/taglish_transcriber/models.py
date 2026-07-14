from __future__ import annotations

import fnmatch
import re
import shutil
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .config import MODEL_OPTIONS
from .paths import MODEL_DIR, ensure_app_directories


AUTO_PROMPT = (
    "Faithful verbatim transcript of a speaker who may naturally switch between "
    "English and Tagalog or Filipino. Preserve the language actually spoken. "
    "Keep proper names, numbers, places, technical terms, and normal punctuation. "
    "Do not translate and do not rewrite grammar."
)

MODEL_REQUIRED_FILES = ("config.json", "model.bin", "tokenizer.json")
MODEL_ALLOW_PATTERNS = (
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
)

MODEL_REPOSITORIES = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "large-v3": "Systran/faster-whisper-large-v3",
}

# Used only when the Hub does not return exact file metadata.
# Exact metadata is requested first for normal online downloads.
MODEL_APPROXIMATE_BYTES = {
    "tiny": 76_000_000,
    "base": 146_000_000,
    "small": 490_000_000,
    "medium": 1_540_000_000,
    "large-v3-turbo": 1_620_000_000,
    "large-v3": 3_100_000_000,
}


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    detected_language: str | None = None
    language_probability: float | None = None
    average_log_probability: float | None = None
    no_speech_probability: float | None = None


@dataclass(frozen=True, slots=True)
class ModelDownloadProgress:
    model_name: str
    phase: str
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed_bytes_per_second: float = 0.0
    eta_seconds: float | None = None
    total_is_estimate: bool = False
    message: str = ""

    @property
    def percent(self) -> float | None:
        if self.total_bytes <= 0:
            return None
        value = (self.downloaded_bytes / self.total_bytes) * 100.0
        return max(0.0, min(100.0, value))


class ModelLoadError(RuntimeError):
    """Raised when a local transcription model cannot be prepared."""


class TranscriptionError(RuntimeError):
    """Raised when speech audio cannot be transcribed."""


def _validate_model_name(model_name: str) -> str:
    clean = model_name.strip()
    if clean not in MODEL_OPTIONS:
        raise ModelLoadError("Select a speech model inside the app first.")
    return clean


def model_folder_name(model_name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", model_name).strip("-.")
    return safe or "whisper-model"


def local_model_path(model_name: str) -> Path:
    return MODEL_DIR / model_folder_name(model_name)


def is_model_downloaded(model_name: str) -> bool:
    if model_name not in MODEL_OPTIONS:
        return False
    folder = local_model_path(model_name)
    return folder.is_dir() and all(
        (folder / filename).is_file() for filename in MODEL_REQUIRED_FILES
    )


def model_status(model_name: str) -> str:
    if model_name not in MODEL_OPTIONS:
        return "Select a speech model, then click Download Selected Model."
    if is_model_downloaded(model_name):
        return f"{model_name} is downloaded and ready for offline use."
    return f"{model_name} is not downloaded yet. Click Download Selected Model."


def _matches_model_file(filename: str) -> bool:
    normalized = filename.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in MODEL_ALLOW_PATTERNS)


def _local_downloaded_bytes(target: Path) -> int:
    """Measure completed model files and active Hugging Face partial files."""
    if not target.exists():
        return 0

    total = 0
    for path in target.rglob("*"):
        if not path.is_file():
            continue

        try:
            relative = path.relative_to(target)
            size = path.stat().st_size
        except OSError:
            continue

        relative_text = relative.as_posix()

        # Hugging Face stores active partial transfers under its local metadata
        # folder. Count only .incomplete data there, not locks or metadata.
        if ".cache" in relative.parts:
            if path.name.endswith(".incomplete"):
                total += size
            continue

        if path.name.endswith(".incomplete") or _matches_model_file(relative_text):
            total += size

    return total


def _remote_model_size(repo_id: str) -> int | None:
    """Ask the Hugging Face Hub for the exact size of required model files."""
    try:
        from huggingface_hub import HfApi

        info = HfApi().model_info(repo_id, files_metadata=True)
        total = 0
        found = False

        for sibling in getattr(info, "siblings", ()) or ():
            filename = str(getattr(sibling, "rfilename", "") or "")
            if not filename or not _matches_model_file(filename):
                continue

            size = getattr(sibling, "size", None)
            if size is None:
                lfs = getattr(sibling, "lfs", None)
                if isinstance(lfs, dict):
                    size = lfs.get("size")
                elif lfs is not None:
                    size = getattr(lfs, "size", None)

            if isinstance(size, int) and size >= 0:
                total += size
                found = True

        return total if found and total > 0 else None
    except Exception:
        return None


class _ProgressTracker:
    def __init__(
        self,
        model_name: str,
        total_bytes: int,
        total_is_estimate: bool,
        callback: Callable[[ModelDownloadProgress], None] | None,
    ) -> None:
        self.model_name = model_name
        self.total_bytes = max(0, int(total_bytes))
        self.total_is_estimate = total_is_estimate
        self.callback = callback
        self._lock = threading.Lock()
        self._started_at = time.monotonic()
        self._last_time = self._started_at
        self._last_bytes = 0
        self._max_bytes = 0
        self._smoothed_speed = 0.0
        self._last_emit = 0.0

    def emit(
        self,
        *,
        phase: str,
        downloaded_bytes: int | None = None,
        message: str = "",
        force: bool = False,
    ) -> None:
        if self.callback is None:
            return

        now = time.monotonic()
        with self._lock:
            if not force and now - self._last_emit < 0.15:
                return

            if downloaded_bytes is not None:
                self._max_bytes = max(self._max_bytes, int(downloaded_bytes))

            if self.total_bytes > 0:
                self._max_bytes = min(self._max_bytes, self.total_bytes)

            elapsed = max(0.001, now - self._last_time)
            delta = max(0, self._max_bytes - self._last_bytes)
            instant_speed = delta / elapsed

            if instant_speed > 0:
                if self._smoothed_speed <= 0:
                    self._smoothed_speed = instant_speed
                else:
                    self._smoothed_speed = (
                        self._smoothed_speed * 0.72 + instant_speed * 0.28
                    )

            eta: float | None = None
            if self.total_bytes > 0 and self._smoothed_speed > 0:
                remaining = max(0, self.total_bytes - self._max_bytes)
                eta = remaining / self._smoothed_speed

            progress = ModelDownloadProgress(
                model_name=self.model_name,
                phase=phase,
                downloaded_bytes=self._max_bytes,
                total_bytes=self.total_bytes,
                speed_bytes_per_second=self._smoothed_speed,
                eta_seconds=eta,
                total_is_estimate=self.total_is_estimate,
                message=message,
            )

            self._last_time = now
            self._last_bytes = self._max_bytes
            self._last_emit = now

        try:
            self.callback(progress)
        except Exception:
            # UI callbacks must never interrupt or corrupt the model download.
            pass


def _make_tqdm_class(tracker: _ProgressTracker):
    """Create a silent tqdm-compatible class that forwards byte progress."""
    from tqdm.auto import tqdm

    class CallbackTqdm(tqdm):
        def __init__(self, *args, **kwargs):
            self._live_scribe_byte_bar = kwargs.get("unit") == "B"
            kwargs["disable"] = True
            super().__init__(*args, **kwargs)
            if self._live_scribe_byte_bar:
                tracker.emit(
                    phase="downloading",
                    downloaded_bytes=int(getattr(self, "n", 0) or 0),
                )

        def update(self, n=1):
            result = super().update(n)
            if self._live_scribe_byte_bar:
                tracker.emit(
                    phase="downloading",
                    downloaded_bytes=int(getattr(self, "n", 0) or 0),
                )
            return result

        def refresh(self, *args, **kwargs):
            result = super().refresh(*args, **kwargs)
            if getattr(self, "_live_scribe_byte_bar", False):
                total = int(getattr(self, "total", 0) or 0)
                if total > tracker.total_bytes:
                    tracker.total_bytes = total
                    tracker.total_is_estimate = False
                tracker.emit(
                    phase="downloading",
                    downloaded_bytes=int(getattr(self, "n", 0) or 0),
                )
            return result

    return CallbackTqdm


def download_model_once(
    model_name: str,
    progress_callback: Callable[[ModelDownloadProgress], None] | None = None,
) -> Path:
    """Download one explicitly selected model with live in-app progress."""
    model_name = _validate_model_name(model_name)
    ensure_app_directories()
    target = local_model_path(model_name)
    repo_id = MODEL_REPOSITORIES[model_name]

    if is_model_downloaded(model_name):
        if progress_callback:
            progress_callback(
                ModelDownloadProgress(
                    model_name=model_name,
                    phase="complete",
                    downloaded_bytes=_local_downloaded_bytes(target),
                    total_bytes=_local_downloaded_bytes(target),
                    message="The selected model is already downloaded and ready.",
                )
            )
        return target

    target.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback(
            ModelDownloadProgress(
                model_name=model_name,
                phase="preparing",
                message="Checking model files and download size…",
            )
        )

    exact_total = _remote_model_size(repo_id)
    total_is_estimate = exact_total is None
    total_bytes = exact_total or MODEL_APPROXIMATE_BYTES.get(model_name, 0)

    tracker = _ProgressTracker(
        model_name=model_name,
        total_bytes=total_bytes,
        total_is_estimate=total_is_estimate,
        callback=progress_callback,
    )

    initial_bytes = _local_downloaded_bytes(target)
    tracker.emit(
        phase="downloading",
        downloaded_bytes=initial_bytes,
        message=(
            "Resuming the selected model download…"
            if initial_bytes > 0
            else "Downloading the selected speech model…"
        ),
        force=True,
    )

    monitor_stop = threading.Event()

    def monitor_local_files() -> None:
        while not monitor_stop.wait(0.25):
            tracker.emit(
                phase="downloading",
                downloaded_bytes=_local_downloaded_bytes(target),
            )

    monitor = threading.Thread(
        target=monitor_local_files,
        name="model-download-progress",
        daemon=True,
    )
    monitor.start()

    try:
        from huggingface_hub import snapshot_download

        downloaded_path = Path(
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(target),
                local_files_only=False,
                allow_patterns=list(MODEL_ALLOW_PATTERNS),
                tqdm_class=_make_tqdm_class(tracker),
            )
        )
    except Exception as exc:
        message = str(exc).strip()
        if len(message) > 300:
            message = message[:297] + "…"
        raise ModelLoadError(
            "The speech model could not be downloaded. Check the internet "
            "connection and available storage, then try again. "
            f"Details: {message or 'model download did not finish'}"
        ) from exc
    finally:
        monitor_stop.set()
        monitor.join(timeout=1.0)

    resolved = downloaded_path if downloaded_path.is_dir() else target
    if resolved != target and resolved.is_dir():
        for child in resolved.iterdir():
            destination = target / child.name
            if destination.exists():
                continue
            if child.is_dir():
                shutil.copytree(child, destination)
            else:
                shutil.copy2(child, destination)

    if not all((target / filename).is_file() for filename in MODEL_REQUIRED_FILES):
        raise ModelLoadError(
            "The speech model download is incomplete. Open the app while connected "
            "to the internet and click Download Selected Model again to resume."
        )

    (target / ".download-complete").write_text("0.4.1", encoding="utf-8")
    final_bytes = _local_downloaded_bytes(target)
    tracker.emit(
        phase="complete",
        downloaded_bytes=tracker.total_bytes or final_bytes,
        message="Model download finished. This model can now be used offline.",
        force=True,
    )
    return target


class WhisperEngine:
    def __init__(
        self,
        model_name: str,
        device_mode: str = "Auto",
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.model_name = model_name
        self.device_mode = device_mode
        self.progress_callback = progress_callback
        self._model: Any = None
        self.device = "cpu"
        self.compute_type = "int8"

    def _notify(self, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(message)

    def _resolve_device(self) -> tuple[str, str]:
        if self.device_mode == "CPU":
            return "cpu", "int8"

        try:
            import ctranslate2

            cuda_available = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            cuda_available = False

        if self.device_mode == "NVIDIA GPU":
            if not cuda_available:
                raise ModelLoadError(
                    "NVIDIA GPU mode was selected, but a compatible CUDA device "
                    "was not detected. Choose Auto or CPU."
                )
            return "cuda", "float16"

        if cuda_available:
            return "cuda", "float16"
        return "cpu", "int8"

    def load(self) -> None:
        self.model_name = _validate_model_name(self.model_name)
        self._notify("Preparing the local speech recognition engine…")

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ModelLoadError(
                "This portable package is incomplete. Download and extract the "
                "complete product package again."
            ) from exc

        if not is_model_downloaded(self.model_name):
            raise ModelLoadError(
                "The selected speech model has not been downloaded. Return to the "
                "main window and click Download Selected Model first."
            )

        self.device, self.compute_type = self._resolve_device()
        model_path = local_model_path(self.model_name)
        self._notify("Loading the downloaded model from the portable folder…")

        try:
            self._model = WhisperModel(
                str(model_path),
                device=self.device,
                compute_type=self.compute_type,
                local_files_only=True,
            )
        except Exception as exc:
            message = str(exc).strip()
            if len(message) > 300:
                message = message[:297] + "…"
            raise ModelLoadError(
                "The downloaded speech model could not be opened. "
                "Download that model again from inside the app. "
                f"Details: {message or 'unknown model loading error'}"
            ) from exc

        target = "NVIDIA GPU" if self.device == "cuda" else "CPU"
        self._notify(f"Model ready on {target}.")

    @staticmethod
    def _segment_from_raw(
        raw_segment: Any,
        *,
        offset: float,
        detected_language: str | None,
        language_probability: float | None,
    ) -> TranscriptSegment | None:
        text = " ".join(str(raw_segment.text).strip().split())
        if not text:
            return None
        return TranscriptSegment(
            start=max(0.0, offset + float(raw_segment.start)),
            end=max(0.0, offset + float(raw_segment.end)),
            text=text,
            detected_language=detected_language,
            language_probability=language_probability,
            average_log_probability=getattr(raw_segment, "avg_logprob", None),
            no_speech_probability=getattr(raw_segment, "no_speech_prob", None),
        )

    def transcribe(
        self,
        audio: np.ndarray,
        chunk_start: float,
        language_code: str | None,
        hotwords: str | None = None,
    ) -> list[TranscriptSegment]:
        """Fast phrase-level pass used while the speaker is still talking."""
        if self._model is None:
            raise TranscriptionError("The speech model has not been loaded.")
        if audio.size == 0:
            return []

        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        kwargs: dict[str, Any] = {
            "task": "transcribe",
            "beam_size": 3,
            "best_of": 3,
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "vad_filter": True,
            "vad_parameters": {
                "min_silence_duration_ms": 350,
                "speech_pad_ms": 180,
            },
            "word_timestamps": False,
            "initial_prompt": AUTO_PROMPT,
        }
        if language_code:
            kwargs["language"] = language_code
        if hotwords:
            kwargs["hotwords"] = hotwords

        return self._run_transcription(audio, chunk_start, kwargs)

    def transcribe_file(
        self,
        audio_path: Path,
        language_code: str | None,
        hotwords: str | None = None,
    ) -> list[TranscriptSegment]:
        """Slower, more accurate pass used after the WAV recording is complete."""
        if self._model is None:
            raise TranscriptionError("The speech model has not been loaded.")
        if not audio_path.is_file():
            raise TranscriptionError("The saved WAV recording could not be found.")

        kwargs: dict[str, Any] = {
            "task": "transcribe",
            "beam_size": 5,
            "best_of": 5,
            "patience": 1.2,
            "temperature": (0.0, 0.2, 0.4),
            "condition_on_previous_text": True,
            "vad_filter": True,
            "vad_parameters": {
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 250,
            },
            "word_timestamps": True,
            "hallucination_silence_threshold": 2.0,
            "initial_prompt": AUTO_PROMPT,
        }
        if language_code:
            kwargs["language"] = language_code
        if hotwords:
            kwargs["hotwords"] = hotwords

        return self._run_transcription(str(audio_path), 0.0, kwargs)

    def _run_transcription(
        self,
        audio: str | np.ndarray,
        offset: float,
        kwargs: dict[str, Any],
    ) -> list[TranscriptSegment]:
        try:
            raw_segments, info = self._model.transcribe(audio, **kwargs)
            detected_language = getattr(info, "language", None)
            language_probability = getattr(info, "language_probability", None)
            output: list[TranscriptSegment] = []
            for raw_segment in raw_segments:
                segment = self._segment_from_raw(
                    raw_segment,
                    offset=offset,
                    detected_language=detected_language,
                    language_probability=language_probability,
                )
                if segment is not None:
                    output.append(segment)
            return output
        except Exception as exc:
            message = str(exc).strip()
            if len(message) > 280:
                message = message[:277] + "…"
            raise TranscriptionError(
                "The audio could not be transcribed. "
                f"Details: {message or 'unknown transcription error'}"
            ) from exc


def replace_segment_text(segment: TranscriptSegment, text: str) -> TranscriptSegment:
    return replace(segment, text=text)
