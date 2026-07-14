from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from src.taglish_transcriber.audio import (
    WavRecorder,
    combine_wav_parts,
    recording_parts_dir,
    recover_rolling_recording,
)


def write_part(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes((np.ones(1600, dtype="<i2") * value).tobytes())


def test_recorder_combines_parts_on_normal_close(tmp_path: Path) -> None:
    output = tmp_path / "session.wav"
    recorder = WavRecorder(output, 16000, rollover_seconds=60)
    recorder.start()
    assert recorder.submit(np.zeros(1600, dtype=np.float32))
    recorder.close()

    assert output.is_file()
    assert not recording_parts_dir(output).exists()
    with wave.open(str(output), "rb") as wav_file:
        assert wav_file.getnframes() == 1600


def test_interrupted_parts_can_be_recovered(tmp_path: Path) -> None:
    output = tmp_path / "recover.wav"
    folder = recording_parts_dir(output)
    write_part(folder / "part_0001.wav", 1)
    write_part(folder / "part_0002.wav", 2)

    assert recover_rolling_recording(output)
    with wave.open(str(output), "rb") as wav_file:
        assert wav_file.getnframes() == 3200
