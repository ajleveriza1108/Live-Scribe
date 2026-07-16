from pathlib import Path

from src.taglish_transcriber.application_audio import (
    application_audio_support,
    parse_application_pid,
)


ROOT = Path(__file__).resolve().parents[1]


def test_application_pid_parser() -> None:
    assert parse_application_pid("Browser — chrome.exe — PID 12345") == 12345
    assert parse_application_pid("No application") is None


def test_non_windows_support_is_safely_reported() -> None:
    supported, reason = application_audio_support()
    assert isinstance(supported, bool)
    assert reason


def test_input_test_is_visible_and_does_not_record() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "productivity_features.py"
    ).read_text(encoding="utf-8")
    assert 'text="Live input check"' in source
    assert 'text="Test Input"' in source
    assert "This does not start transcription or save audio" in source


def test_selected_app_can_be_toggled_during_session() -> None:
    session = (
        ROOT / "src" / "taglish_transcriber" / "session.py"
    ).read_text(encoding="utf-8")
    assert "set_application_audio_enabled" in session
    assert "set_application_audio_target" in session
