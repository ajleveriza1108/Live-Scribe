from __future__ import annotations

import json
from pathlib import Path

from src.taglish_transcriber.dictionary_engine import VocabularyManager
from src.taglish_transcriber.skill_library import SkillLibrary


def test_vocabulary_hotwords_and_replacements(tmp_path: Path) -> None:
    dictionary = tmp_path / "dictionary"
    dictionary.mkdir()
    (dictionary / "starter_terms.txt").write_text("Taglish\nBarangay Mabini\n", encoding="utf-8")
    (dictionary / "custom_terms.txt").write_text("Pastor Santos\n", encoding="utf-8")
    (dictionary / "replacements.json").write_text(
        json.dumps({"tag lish": "Taglish"}), encoding="utf-8"
    )
    (dictionary / "pronunciation_guide.json").write_text(
        json.dumps({"Cantos": ["kan tos", "cant toes"]}), encoding="utf-8"
    )

    vocabulary = VocabularyManager(dictionary)
    hotwords = vocabulary.hotwords(["Sampaguita Church"])
    corrected, corrections = vocabulary.apply_replacements("This is tag lish speech.")

    assert "Pastor Santos" in hotwords
    assert "Sampaguita Church" in hotwords
    assert "Cantos" in hotwords
    assert "kan tos" in hotwords
    assert corrected == "This is Taglish speech."
    assert corrections[0].corrected == "Taglish"


def test_markdown_skill_hotwords_are_discovered(tmp_path: Path) -> None:
    skills = tmp_path / "Skills"
    knowledge = tmp_path / "Knowledge"
    skills.mkdir()
    knowledge.mkdir()
    (skills / "accuracy.skill.md").write_text(
        "# Accuracy\n\n## ASR hotwords\n- Project Lakbay\n- San Isidro\n",
        encoding="utf-8",
    )
    (knowledge / "notes.md").write_text("# Notes\n\nCompact context.", encoding="utf-8")

    library = SkillLibrary(skills, knowledge)

    assert library.asr_hotwords() == ["Project Lakbay", "San Isidro"]
    assert "Compact context" in library.prompt_context()


def test_pronunciation_guide_can_be_saved_and_applied(tmp_path: Path) -> None:
    dictionary = tmp_path / "dictionary"
    dictionary.mkdir()
    (dictionary / "starter_terms.txt").write_text("", encoding="utf-8")
    (dictionary / "custom_terms.txt").write_text("", encoding="utf-8")
    (dictionary / "replacements.json").write_text("{}", encoding="utf-8")

    vocabulary = VocabularyManager(dictionary)
    vocabulary.save_pronunciation("Project Lakbay", ["project lock buy", "project lak bai"])
    corrected, corrections = vocabulary.apply_replacements(
        "Welcome to project lock buy."
    )

    assert corrected == "Welcome to Project Lakbay."
    assert corrections[0].source == "Pronunciation guide"
    assert vocabulary.pronunciation_entries[0].written == "Project Lakbay"
