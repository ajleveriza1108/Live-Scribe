from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_call_mode_ui_exposes_two_sources_and_speaker_labels() -> None:
    config = (ROOT / "src/taglish_transcriber/config.py").read_text(encoding="utf-8")
    base = (ROOT / "src/taglish_transcriber/ui_base.py").read_text(encoding="utf-8")
    productivity = (ROOT / "src/taglish_transcriber/productivity_features.py").read_text(encoding="utf-8")

    assert 'AUDIO_SOURCE_CONVERSATION = "Call / conversation — app + microphone"' in config
    assert "application_audio_label=self.settings.application_audio_label" in base
    assert "conversation_caller_label=self.settings.conversation_caller_label" in base
    assert 'text="Remote speaker"' in productivity
    assert 'text="My microphone"' in productivity
    assert "summarize_call_entries" in productivity


def test_call_session_uses_one_transcription_worker_for_low_ram() -> None:
    source = (ROOT / "src/taglish_transcriber/session.py").read_text(encoding="utf-8")
    assert "conversation-transcription-worker" in source
    assert "self._engine_lock" in source
    assert "self.application_capture" in source
    assert "self.microphone_capture" in source
    assert "mix_conversation_wavs" in source
