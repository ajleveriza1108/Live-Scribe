from pathlib import Path


def test_topic_profiles_are_managed_from_settings_with_crud_preserved() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui.py"
    ).read_text(encoding="utf-8")

    assert 'self.settings_tabs.add("Topic Profiles")' in source
    assert "Topic profile" in source
    assert "Manage Topic Profiles" in source
    assert "Add New" in source
    assert "Save Changes" in source
    assert "Remove Selected" in source
    assert "_topic_context_for_session" in source
    assert '("Topics", "◎")' not in source
