from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from src.taglish_transcriber.media import (
    SUPPORTED_MEDIA_EXTENSIONS,
    inspect_media,
    is_supported_media,
)


def test_common_recorded_video_and_audio_extensions_are_available() -> None:
    for extension in (".mp4", ".mkv", ".mp3", ".wav", ".m4a", ".flac", ".webm"):
        assert extension in SUPPORTED_MEDIA_EXTENSIONS
        assert is_supported_media(Path("sample" + extension))


def test_wav_media_can_be_inspected(tmp_path: Path) -> None:
    path = tmp_path / "recording.wav"
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(np.zeros(16000, dtype="<i2").tobytes())

    info = inspect_media(path)
    assert info.audio_streams >= 1
    assert info.source_type == "audio"
