from __future__ import annotations

import numpy as np

from src.taglish_transcriber.audio import (
    SystemAudioInfo,
    _looks_like_virtual_audio,
    downmix_to_mono,
)


def test_stereo_system_audio_is_downmixed_to_mono() -> None:
    stereo = np.array(
        [
            [1.0, -1.0],
            [0.50, 0.50],
            [-0.25, 0.75],
        ],
        dtype=np.float32,
    )

    mono = downmix_to_mono(stereo)

    assert mono.dtype == np.float32
    assert mono.shape == (3,)
    assert np.allclose(mono, [0.0, 0.5, 0.25])


def test_virtual_audio_names_are_detected() -> None:
    assert _looks_like_virtual_audio("BlackHole 2ch")
    assert _looks_like_virtual_audio("alsa_output.monitor")
    assert _looks_like_virtual_audio("Stereo Mix")
    assert not _looks_like_virtual_audio("Built-in Microphone")


def test_system_audio_label_marks_default_output() -> None:
    info = SystemAudioInfo(
        backend_id="speaker-id",
        name="Speakers",
        is_default=True,
    )
    assert info.label == "Speakers (System default output)"
