from pathlib import Path

from src.taglish_transcriber.models import TranscriptSegment
from src.taglish_transcriber.review_engine import ReviewComment
from src.taglish_transcriber.transcript import TranscriptDocument, format_clock


def test_format_clock() -> None:
    assert format_clock(65.4) == "00:01:05"
    assert format_clock(3661.25) == "01:01:01"


def test_duplicate_live_segment_is_ignored() -> None:
    document = TranscriptDocument()
    first = TranscriptSegment(0.0, 1.0, "Magandang umaga.")
    duplicate = TranscriptSegment(1.0, 2.0, "magandang umaga")

    assert document.add(first) is not None
    assert document.add(duplicate) is None
    assert len(document.live_entries) == 1


def test_final_transcript_replaces_live_for_exports(tmp_path: Path) -> None:
    document = TranscriptDocument()
    document.add_live(TranscriptSegment(0.25, 2.5, "Hello, come esta?"))
    recording = tmp_path / "recording.wav"
    recording.write_bytes(b"RIFF")
    document.set_final(
        [TranscriptSegment(0.25, 2.5, "Hello, kumusta?")],
        [
            ReviewComment(
                timestamp=0.25,
                category="WAV verification",
                original="Live: Hello, come esta?",
                suggestion="Final pass: Hello, kumusta?",
                explanation="Replay the WAV.",
            )
        ],
        recording_path=recording,
        enhanced_recording_path=None,
    )

    assert document.is_finalized
    assert document.plain_text(False) == "Hello, kumusta?"
    assert document.plain_text(False, use_live=True) == "Hello, come esta?"
    assert "Hello, kumusta?" in document.srt_text()
