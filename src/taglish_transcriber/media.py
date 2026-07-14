from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from .audio import TARGET_SAMPLE_RATE, downmix_to_mono, resample_linear


SUPPORTED_MEDIA_EXTENSIONS = (
    ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma",
    ".aiff", ".aif", ".alac", ".mka",
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mpeg", ".mpg",
    ".3gp", ".ts", ".mts",
)

MEDIA_FILE_TYPES = (
    (
        "Supported video and audio",
        "*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus *.wma "
        "*.aiff *.aif *.alac *.mka *.mp4 *.mkv *.mov *.avi *.webm *.m4v "
        "*.mpeg *.mpg *.3gp *.ts *.mts",
    ),
    ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mpeg *.mpg *.3gp *.ts *.mts"),
    ("Audio files", "*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus *.wma *.aiff *.aif *.alac *.mka"),
    ("All files", "*.*"),
)


@dataclass(frozen=True, slots=True)
class MediaInfo:
    path: Path
    duration_seconds: float | None
    audio_streams: int
    video_streams: int

    @property
    def source_type(self) -> str:
        return "video" if self.video_streams else "audio"


def is_supported_media(path: Path) -> bool:
    return path.suffix.casefold() in SUPPORTED_MEDIA_EXTENSIONS


def inspect_media(path: Path) -> MediaInfo:
    if not path.is_file():
        raise ValueError("The selected recording could not be found.")
    if not is_supported_media(path):
        raise ValueError(
            "Choose a supported recording such as MP4, MKV, MOV, AVI, WebM, "
            "MP3, WAV, M4A, AAC, FLAC, OGG, OPUS, WMA, AIFF, or another listed format."
        )
    try:
        import av
    except ImportError as exc:
        raise RuntimeError(
            "Recorded-file transcription support is missing from this package. "
            "Install the complete Live Scribe dependencies."
        ) from exc

    try:
        with av.open(str(path)) as container:
            audio_streams = sum(1 for stream in container.streams if stream.type == "audio")
            video_streams = sum(1 for stream in container.streams if stream.type == "video")
            duration = (
                float(container.duration / av.time_base)
                if container.duration is not None
                else None
            )
    except Exception as exc:
        raise ValueError(
            "The selected recording could not be opened. It may be damaged, encrypted, "
            f"or use an unsupported codec. Details: {str(exc).strip() or 'media open failed'}"
        ) from exc

    if audio_streams <= 0:
        raise ValueError("The selected file does not contain a usable audio track.")
    return MediaInfo(path=path, duration_seconds=duration, audio_streams=audio_streams, video_streams=video_streams)


def decode_audio_segment(
    path: Path,
    *,
    start_seconds: float,
    duration_seconds: float = 8.0,
) -> np.ndarray:
    try:
        import av
    except ImportError as exc:
        raise RuntimeError("Audio playback support is missing from this package.") from exc

    start_seconds = max(0.0, float(start_seconds))
    duration_seconds = max(0.25, min(30.0, float(duration_seconds)))
    output: list[np.ndarray] = []

    with av.open(str(path)) as container:
        stream = next((item for item in container.streams if item.type == "audio"), None)
        if stream is None:
            raise RuntimeError("No audio track was found.")
        try:
            container.seek(int(start_seconds * av.time_base), backward=True, any_frame=False)
        except Exception:
            pass

        accumulated = 0
        target_samples = int(duration_seconds * TARGET_SAMPLE_RATE)
        for frame in container.decode(stream):
            frame_time = float(frame.time or 0.0)
            frame_duration = float(frame.samples / frame.sample_rate)
            if frame_time + frame_duration < start_seconds:
                continue
            array = frame.to_ndarray()
            if array.ndim == 2 and array.shape[0] <= 16:
                array = array.T
            mono = downmix_to_mono(array)
            if mono.dtype.kind in {"i", "u"}:
                scale = float(max(abs(np.iinfo(mono.dtype).min), np.iinfo(mono.dtype).max))
                mono = mono.astype(np.float32) / scale
            else:
                mono = mono.astype(np.float32)
            mono = resample_linear(mono, float(frame.sample_rate), TARGET_SAMPLE_RATE)
            output.append(mono)
            accumulated += mono.size
            if accumulated >= target_samples:
                break

    if not output:
        raise RuntimeError("No playable audio was found at the selected timestamp.")
    return np.concatenate(output)[:target_samples].astype(np.float32, copy=False)


def play_audio_segment(
    path: Path,
    *,
    start_seconds: float,
    duration_seconds: float = 8.0,
    on_error: Callable[[str], None] | None = None,
) -> threading.Thread:
    def worker() -> None:
        try:
            import sounddevice as sd

            audio = decode_audio_segment(
                path,
                start_seconds=start_seconds,
                duration_seconds=duration_seconds,
            )
            sd.play(audio, TARGET_SAMPLE_RATE, blocking=True)
        except Exception as exc:
            if on_error:
                on_error(str(exc).strip() or "audio playback failed")

    thread = threading.Thread(target=worker, name="media-playback", daemon=True)
    thread.start()
    return thread
