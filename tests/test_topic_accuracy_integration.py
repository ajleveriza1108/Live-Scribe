from __future__ import annotations

from pathlib import Path

from src.taglish_transcriber.dictionary_engine import VocabularyManager
from src.taglish_transcriber.models import compose_initial_prompt


def test_topic_terms_have_priority_in_hotword_budget(tmp_path: Path) -> None:
    directory = tmp_path / "dictionary"
    directory.mkdir()
    (directory / "starter_terms.txt").write_text(
        "ordinary one\nordinary two\nordinary three\n",
        encoding="utf-8",
    )
    (directory / "custom_terms.txt").write_text("", encoding="utf-8")
    (directory / "replacements.json").write_text("{}\n", encoding="utf-8")
    (directory / "pronunciation_guide.json").write_text("{}\n", encoding="utf-8")

    vocabulary = VocabularyManager(directory)
    result = vocabulary.hotwords(
        ["late skill term"],
        max_characters=45,
        priority_terms=["Pastor Noel A. Cantos", "Joshua 24:15"],
    )

    assert result is not None
    assert result.startswith("Pastor Noel A. Cantos, Joshua 24:15")


def test_topic_context_is_appended_to_language_prompt() -> None:
    prompt = compose_initial_prompt(
        "English",
        "Topic profile: Office & Business Meeting. Recording context: Weekly budget review.",
    )
    assert "Faithful verbatim transcript in English" in prompt
    assert "Office & Business Meeting" in prompt
    assert "Weekly budget review" in prompt
