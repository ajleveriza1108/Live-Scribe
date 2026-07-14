from __future__ import annotations

import re
import shutil
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


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    detected_language: str | None = None
    language_probability: float | None = None
    average_log_probability: float | None = None
    no_speech_probability: float | None = None


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


def download_model_once(
    model_name: str,
    progress_callback: Callable[[str], None] | None = None,
) -> Path:
    """Download a selected model only after an explicit in-app buyer action."""
    model_name = _validate_model_name(model_name)
    ensure_app_directories()
    target = local_model_path(model_name)

    def notify(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    if is_model_downloaded(model_name):
        notify("The selected model is already downloaded and ready.")
        return target

    notify(
        "Downloading the selected speech model. Keep the app open and keep the "
        "internet connection active until the download finishes."
    )

    try:
        from faster_whisper.utils import download_model

        target.mkdir(parents=True, exist_ok=True)
        downloaded_path = Path(
            download_model(
                model_name,
                output_dir=str(target),
                local_files_only=False,
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

    resolved = downloaded_path if downloaded_path.is_dir() else target
    if resolved != target and resolved.is_dir():
        # The current Faster-Whisper downloader normally writes directly to target.
        # Copy defensively so the portable app always knows where the model lives.
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

    (target / ".download-complete").write_text("0.3.2", encoding="utf-8")
    notify("Model download finished. This model can now be used offline.")
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
