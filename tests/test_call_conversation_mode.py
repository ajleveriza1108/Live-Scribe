from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

from src.taglish_transcriber.audio import mix_conversation_wavs
from src.taglish_transcriber.config import (
    AUDIO_SOURCE_CONVERSATION,
    AUDIO_SOURCE_OPTIONS,
    LANGUAGE_AMERICAN_ENGLISH,
    LANGUAGE_AUSTRALIAN_ENGLISH,
    LANGUAGE_BRITISH_ENGLISH,
    LANGUAGE_CANADIAN_ENGLISH,
    LANGUAGE_ENGLISH,
    LANGUAGE_FILIPINO_ENGLISH,
    LANGUAGE_INDIAN_ENGLISH,
    LANGUAGE_LABEL_TO_CODE,
    AppSettings,
    language_priority_terms,
)
from src.taglish_transcriber.models import TranscriptSegment
from src.taglish_transcriber.transcript import TranscriptDocument
from src.taglish_transcriber.transcript_summary import summarize_call_entries


def _write_tone(path: Path, *, rate: int, seconds: float, frequency: float) -> None:
    t = np.arange(int(rate * seconds), dtype=np.float32) / rate
    samples = (0.15 * np.sin(2.0 * np.pi * frequency * t)).astype(np.float32)
    pcm = (samples * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())


def test_windows_call_mode_is_a_normal_audio_source() -> None:
    if sys.platform == "win32":
        assert AUDIO_SOURCE_CONVERSATION in AUDIO_SOURCE_OPTIONS
    else:
        assert AUDIO_SOURCE_CONVERSATION not in AUDIO_SOURCE_OPTIONS


def test_call_labels_are_saved_settings() -> None:
    settings = AppSettings()
    assert settings.conversation_caller_label == "Caller"
    assert settings.conversation_me_label == "Me"


def test_global_english_is_generic_and_locale_profiles_share_english_asr() -> None:
    variants = (
        LANGUAGE_ENGLISH,
        LANGUAGE_AMERICAN_ENGLISH,
        LANGUAGE_BRITISH_ENGLISH,
        LANGUAGE_AUSTRALIAN_ENGLISH,
        LANGUAGE_CANADIAN_ENGLISH,
        LANGUAGE_INDIAN_ENGLISH,
        LANGUAGE_FILIPINO_ENGLISH,
    )
    assert all(LANGUAGE_LABEL_TO_CODE[label] == "en" for label in variants)
    assert language_priority_terms(LANGUAGE_ENGLISH) == ()
    assert "postcode" in language_priority_terms(LANGUAGE_BRITISH_ENGLISH)
    assert "Medicare" in language_priority_terms(LANGUAGE_AUSTRALIAN_ENGLISH)
    assert "postal code" in language_priority_terms(LANGUAGE_CANADIAN_ENGLISH)
    assert "Aadhaar" in language_priority_terms(LANGUAGE_INDIAN_ENGLISH)
    assert "barangay" in language_priority_terms(LANGUAGE_FILIPINO_ENGLISH)


def test_transcript_segment_speaker_flows_into_document() -> None:
    document = TranscriptDocument(source_type="conversation")
    entry = document.add_live(
        TranscriptSegment(
            start=0.2,
            end=1.1,
            text="Good morning, I am calling about my appointment.",
            speaker="Caller",
        )
    )
    assert entry is not None
    assert entry.speaker == "Caller"
    assert "Caller:" in document.plain_text()


def test_conversation_metadata_round_trips(tmp_path: Path) -> None:
    document = TranscriptDocument(source_type="conversation")
    document.source_recordings = {
        "caller": tmp_path / "caller.wav",
        "me": tmp_path / "me.wav",
    }
    document.source_offsets = {"caller": 0.0, "me": 0.12}
    document.speaker_labels = {"caller": "Patient", "me": "Receptionist"}

    restored = TranscriptDocument.from_dict(document.to_dict())
    assert restored.source_recordings["caller"].name == "caller.wav"
    assert restored.source_offsets["me"] == 0.12
    assert restored.speaker_labels["me"] == "Receptionist"


def test_conversation_wav_mixer_keeps_bounded_combined_file(tmp_path: Path) -> None:
    caller = tmp_path / "caller.wav"
    me = tmp_path / "me.wav"
    combined = tmp_path / "combined.wav"
    _write_tone(caller, rate=44_100, seconds=0.5, frequency=440.0)
    _write_tone(me, rate=48_000, seconds=0.5, frequency=660.0)

    result = mix_conversation_wavs(
        caller,
        me,
        combined,
        offsets={"caller": 0.0, "me": 0.1},
    )
    assert result == combined
    with wave.open(str(combined), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getframerate() == 16_000
        assert handle.getnframes() >= 8_000


def test_call_summary_keeps_original_speaker_context() -> None:
    document = TranscriptDocument(source_type="conversation")
    document.add_live(
        TranscriptSegment(
            0.0,
            2.0,
            "Hi, my name is Sarah and I am calling about my appointment tomorrow.",
            speaker="Caller",
        )
    )
    document.add_live(
        TranscriptSegment(
            2.2,
            4.0,
            "I will confirm the booking and call you back this afternoon.",
            speaker="Me",
        )
    )

    summary = summarize_call_entries(document.entries)
    rendered = summary.render()
    assert "REASON FOR CALL" in rendered
    assert "APPOINTMENT / SCHEDULE" in rendered
    assert "ACTION REQUIRED" in rendered
    assert "Caller:" in rendered
    assert "Me:" in rendered
