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

from .config import (
    MODEL_CATALOG,
    MODEL_OPTIONS,
    language_prompt,
    model_friendly_name,
    model_size_label,
)
from .paths import MODEL_DIR, ensure_app_directories


MODEL_REQUIRED_FILES = ("config.json", "model.bin", "tokenizer.json")
MODEL_ALLOW_PATTERNS = (
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
)

MODEL_REPOSITORIES = {
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "large-v3": "Systran/faster-whisper-large-v3",
}

# Used only when the Hub does not return exact file metadata.
# Exact metadata is requested first for normal online downloads.
MODEL_APPROXIMATE_BYTES = {
    model_name: int(details["bytes"])
    for model_name, details in MODEL_CATALOG.items()
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


class ModelDownloadCancelled(RuntimeError):
    """Raised when the user safely stops an active model download."""


class TranscriptionError(RuntimeError):
    """Raised when speech audio cannot be transcribed."""


def _raise_if_download_cancelled(
    cancel_event: threading.Event | None,
) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise ModelDownloadCancelled(
            "The model download was stopped. Partial files were kept and can be resumed."
        )


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
        return "Choose a speech quality option in Models."
    friendly = model_friendly_name(model_name)
    size = model_size_label(model_name)
    if is_model_downloaded(model_name):
        return f"{friendly} ({size}) is ready for offline use."
    return f"{friendly} ({size}) is not downloaded yet."


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
        cancel_event: threading.Event | None = None,
    ) -> None:
        self.model_name = model_name
        self.total_bytes = max(0, int(total_bytes))
        self.total_is_estimate = total_is_estimate
        self.callback = callback
        self.cancel_event = cancel_event
        self._lock = threading.Lock()
        self._started_at = time.monotonic()
        self._last_time = self._started_at
        self._last_bytes = 0
        self._max_bytes = 0
        self._smoothed_speed = 0.0
        self._last_emit = 0.0

    def check_cancelled(self) -> None:
        _raise_if_download_cancelled(self.cancel_event)

    def emit(
        self,
        *,
        phase: str,
        downloaded_bytes: int | None = None,
        message: str = "",
        force: bool = False,
    ) -> None:
        self.check_cancelled()
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
    """Create a silent tqdm-compatible class with progress and stop support."""
    from tqdm.auto import tqdm

    class CallbackTqdm(tqdm):
        def __init__(self, *args, **kwargs):
            tracker.check_cancelled()
            self._live_scribe_byte_bar = kwargs.get("unit") == "B"
            kwargs["disable"] = True
            super().__init__(*args, **kwargs)
            if self._live_scribe_byte_bar:
                tracker.emit(
                    phase="downloading",
                    downloaded_bytes=int(getattr(self, "n", 0) or 0),
                )

        def update(self, n=1):
            tracker.check_cancelled()
            result = super().update(n)
            if self._live_scribe_byte_bar:
                tracker.emit(
                    phase="downloading",
                    downloaded_bytes=int(getattr(self, "n", 0) or 0),
                )
            tracker.check_cancelled()
            return result

        def refresh(self, *args, **kwargs):
            tracker.check_cancelled()
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
            tracker.check_cancelled()
            return result

    return CallbackTqdm


def download_model_once(
    model_name: str,
    progress_callback: Callable[[ModelDownloadProgress], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> Path:
    """Download one selected model, preserving partial files when stopped."""
    _raise_if_download_cancelled(cancel_event)
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
    _raise_if_download_cancelled(cancel_event)
    total_is_estimate = exact_total is None
    total_bytes = exact_total or MODEL_APPROXIMATE_BYTES.get(model_name, 0)

    tracker = _ProgressTracker(
        model_name=model_name,
        total_bytes=total_bytes,
        total_is_estimate=total_is_estimate,
        callback=progress_callback,
        cancel_event=cancel_event,
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
            if cancel_event is not None and cancel_event.is_set():
                return
            try:
                tracker.emit(
                    phase="downloading",
                    downloaded_bytes=_local_downloaded_bytes(target),
                )
            except ModelDownloadCancelled:
                return

    monitor = threading.Thread(
        target=monitor_local_files,
        name="model-download-progress",
        daemon=True,
    )
    monitor.start()

    try:
        _raise_if_download_cancelled(cancel_event)
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
    except ModelDownloadCancelled:
        raise
    except Exception as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise ModelDownloadCancelled(
                "The model download was stopped. Partial files were kept and can be resumed."
            ) from exc
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

    required_complete = all(
        (target / filename).is_file() for filename in MODEL_REQUIRED_FILES
    )
    if cancel_event is not None and cancel_event.is_set() and not required_complete:
        raise ModelDownloadCancelled(
            "The model download was stopped. Partial files were kept and can be resumed."
        )

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

    (target / ".download-complete").write_text("0.6.0", encoding="utf-8")
    final_bytes = _local_downloaded_bytes(target)
    tracker.emit(
        phase="complete",
        downloaded_bytes=tracker.total_bytes or final_bytes,
        message="Model download finished. This model can now be used offline.",
        force=True,
    )
    return target


def compose_initial_prompt(
    language_label: str | None,
    context_prompt: str | None = None,
) -> str:
    """Combine the language rule with a short user-selected recording context."""
    base = language_prompt(language_label)
    context = " ".join((context_prompt or "").strip().split())
    if not context:
        return base
    context = context[:650].rstrip()
    return f"{base} {context}"


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
        language_label: str | None = None,
        context_prompt: str | None = None,
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
            "initial_prompt": compose_initial_prompt(language_label, context_prompt),
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
        language_label: str | None = None,
        context_prompt: str | None = None,
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
            "initial_prompt": compose_initial_prompt(language_label, context_prompt),
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
