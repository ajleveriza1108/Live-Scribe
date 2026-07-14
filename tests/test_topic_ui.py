from pathlib import Path


def test_modern_ui_exposes_topic_profiles_and_crud() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui.py"
    ).read_text(encoding="utf-8")

    assert '("Topics", "◎")' in source
    assert "Topic profile" in source
    assert "Manage Topics" in source
    assert "Add New" in source
    assert "Save Changes" in source
    assert "Remove Selected" in source
    assert "_topic_context_for_session" in source
