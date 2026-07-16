from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_interview_mode_is_in_navigation_and_final_app() -> None:
    ui = (ROOT / "src" / "taglish_transcriber" / "ui.py").read_text(encoding="utf-8")
    assert '("Interview Mode", "◆")' in ui
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
