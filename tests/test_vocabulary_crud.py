from __future__ import annotations

from src.taglish_transcriber.dictionary_engine import VocabularyManager


def test_vocabulary_can_be_added_edited_renamed_and_removed(tmp_path) -> None:
    manager = VocabularyManager(tmp_path)

    manager.add_pronunciation("Project Lakbay", ["project lock buy"])
    assert manager.has_pronunciation("Project Lakbay")

    manager.update_pronunciation(
        "Project Lakbay",
        "Project Lakbay Philippines",
        ["project lock buy philippines", "project lak bai philippines"],
    )

    entries = {entry.written: entry.sounds_like for entry in manager.pronunciation_entries}
    assert "Project Lakbay" not in entries
    assert entries["Project Lakbay Philippines"] == (
        "project lock buy philippines",
        "project lak bai philippines",
    )

    assert manager.remove_pronunciation("Project Lakbay Philippines") is True
    assert manager.pronunciation_entries == ()
