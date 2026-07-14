from __future__ import annotations

from pathlib import Path

from src.taglish_transcriber.models import TranscriptSegment
from src.taglish_transcriber.transcript import TranscriptDocument


def test_transcript_can_be_edited_labeled_marked_and_serialized(tmp_path: Path) -> None:
    document = TranscriptDocument(title="Weekly Meeting")
    document.add_live(TranscriptSegment(start=1.0, end=3.0, text="Original words"))
    document.update_entry(
        0,
        text="Corrected words",
        speaker="Maria Santos",
        verified=True,
        use_live=True,
    )
    document.add_marker(1.0, "Action Item", "Send the report")

    restored = TranscriptDocument.from_dict(document.to_dict())
    assert restored.title == "Weekly Meeting"
    assert restored.live_entries[0].text == "Corrected words"
    assert restored.live_entries[0].speaker == "Maria Santos"
    assert restored.live_entries[0].verified
    assert restored.markers[0].kind == "Action Item"

    restored.save_vtt(tmp_path / "meeting.vtt")
    restored.save_csv(tmp_path / "meeting.csv")
    restored.save_markdown(tmp_path / "meeting.md")

    assert "Maria Santos" in (tmp_path / "meeting.vtt").read_text(encoding="utf-8")
    assert "Action Item" in (tmp_path / "meeting.csv").read_text(encoding="utf-8-sig")
    assert "Send the report" in (tmp_path / "meeting.md").read_text(encoding="utf-8")
