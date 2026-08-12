from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_main_navigation_is_task_based() -> None:
    source = (ROOT / "src/taglish_transcriber/ui.py").read_text(encoding="utf-8")
    assert 'WORKSPACE_MEETINGS = "Online Class & Meetings"' in source
    assert 'WORKSPACE_LIVESTREAM = "Livestreaming"' in source
    assert '("Live Session", "●")' not in source
    assert '("Topics", "◎")' not in source
    for label in (
        "Online Class & Meetings",
        "Livestreaming",
        "Interview Mode",
        "Vocabulary",
        "Sessions",
        "Models",
        "Settings",
    ):
        assert label in source


def test_workspace_modes_own_the_audio_source() -> None:
    source = (ROOT / "src/taglish_transcriber/ui.py").read_text(encoding="utf-8")
    assert "self.audio_source_combo.grid_remove()" in source
    assert "self.audio_source_var.set(AUDIO_SOURCE_CONVERSATION)" in source
    assert "self.audio_source_var.set(AUDIO_SOURCE_APPLICATION)" in source
    assert "Start Meeting / Class" in source
    assert "Start Livestream Transcription" in source


def test_selected_app_audio_has_a_separate_test_meter() -> None:
    source = (
        ROOT / "src/taglish_transcriber/productivity_features.py"
    ).read_text(encoding="utf-8")
    assert 'text="Selected app audio test"' in source
    assert 'text="Test App Audio"' in source
    assert "source_mode=AUDIO_SOURCE_APPLICATION" in source
    assert "unrelated apps should not drive this meter" in source


def test_meeting_microphone_test_does_not_mix_in_app_audio() -> None:
    source = (
        ROOT / "src/taglish_transcriber/productivity_features.py"
    ).read_text(encoding="utf-8")
    assert "if test_source_mode == AUDIO_SOURCE_CONVERSATION:" in source
    assert "test_source_mode = AUDIO_SOURCE_MICROPHONE" in source


def test_interview_mode_has_audio_readiness_and_capture_tools() -> None:
    source = (
        ROOT / "src/taglish_transcriber/interview_ui.py"
    ).read_text(encoding="utf-8")
    assert "Interview audio readiness" in source
    assert "Test Interview App" in source
    assert "Test Microphone" in source
    assert "Start Interview Capture" in source
    assert "_toggle_interview_capture" in source


def test_settings_are_categorized_and_appearance_moved_out_of_sidebar() -> None:
    source = (ROOT / "src/taglish_transcriber/ui.py").read_text(encoding="utf-8")
    assert 'self.settings_tabs.add("General")' in source
    assert 'self.settings_tabs.add("Transcription")' in source
    assert 'self.settings_tabs.add("Verification & Export")' in source
    assert 'self.settings_tabs.add("Topic Profiles")' in source
    assert "Appearance" in source
    assert "Manage Topic Profiles" in source
    assert 'theme_holder = ctk.CTkFrame(self.sidebar' not in source


def test_topic_profiles_are_a_settings_subarea() -> None:
    source = (ROOT / "src/taglish_transcriber/ui.py").read_text(encoding="utf-8")
    assert "← Back to Settings" in source
    assert 'active_nav = "Settings" if requested_name == "Topics"' in source


def test_sessions_distinguish_livestream_and_meeting_sources() -> None:
    productivity = (ROOT / "src/taglish_transcriber/productivity_features.py").read_text(encoding="utf-8")
    store = (ROOT / "src/taglish_transcriber/session_store.py").read_text(encoding="utf-8")
    assert '"livestream"' in productivity
    assert '"Meeting / Call"' in productivity
    assert '"Livestream"' in productivity
    assert '"Meeting / Call"' in store
    assert '"Livestream"' in store
