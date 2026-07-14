from __future__ import annotations

from pathlib import Path

from src.taglish_transcriber.models import TranscriptSegment
from src.taglish_transcriber.recovery import RecoveryManager
from src.taglish_transcriber.session_store import SessionStore
from src.taglish_transcriber.transcript import TranscriptDocument


def make_document() -> TranscriptDocument:
    document = TranscriptDocument(title="Supplier Review")
    document.language = "English"
    document.topic = "Office & Business Meeting"
    document.add_live(
        TranscriptSegment(
            start=0.0,
            end=2.0,
            text="Review the supplier inventory and action items.",
        )
    )
    return document


def test_session_store_searches_transcript_and_reopens_document(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions.sqlite3")
    document = make_document()
    store.save(document)

    results = store.search("inventory")
    assert len(results) == 1
    assert results[0].title == "Supplier Review"

    reopened = store.load(document.session_id)
    assert reopened is not None
    assert reopened.live_entries[0].text.startswith("Review the supplier")


def test_recovery_round_trip(tmp_path: Path) -> None:
    recovery = RecoveryManager(tmp_path / "unfinished.json")
    document = make_document()
    recovery.save(document, state="recording")

    loaded = recovery.load()
    assert loaded is not None
    state, restored = loaded
    assert state == "recording"
    assert restored.title == "Supplier Review"

    recovery.clear()
    assert recovery.load() is None
