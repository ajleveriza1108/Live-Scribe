from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_interview_mode_is_in_navigation_and_final_app() -> None:
    ui = (ROOT / "src" / "taglish_transcriber" / "ui.py").read_text(encoding="utf-8")
    assert '("Interview Mode", "◆", "Interview Mode")' in ui
    assert "InterviewModeMixin, ProductivityFeaturesMixin" in ui


def test_private_answer_panel_is_separate_from_transcript() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "interview_ui.py"
    ).read_text(encoding="utf-8")
    assert "Private Interview Assistant" in source
    assert "It is not added to the official transcript" in source
    assert "Interview transcript" in source


def test_profile_template_generates_question_bank() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "interview_ui.py"
    ).read_text(encoding="utf-8")
    assert "Generate Interview Template and Question Bank" in source
    assert "prepare_question_bank(profile)" in source


def test_interview_page_has_audio_readiness_tools() -> None:
    source = (ROOT / "src/taglish_transcriber/interview_ui.py").read_text(encoding="utf-8")
    assert "Interview audio readiness" in source
    assert "Test Interview App" in source
    assert "Start Interview Capture" in source


def test_interview_mode_exposes_floating_captions_and_uses_interview_role_labels() -> None:
    source = (ROOT / "src/taglish_transcriber/interview_ui.py").read_text(encoding="utf-8")
    assert 'text="Floating Captions (F11)"' in source
    assert "command=self._toggle_caption_window" in source
    assert "self.caption_window.update(updated.text, updated.speaker)" in source
    assert 'text="Start Interview Capture"' in source
