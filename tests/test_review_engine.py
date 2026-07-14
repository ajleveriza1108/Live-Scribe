from __future__ import annotations

from src.taglish_transcriber.models import TranscriptSegment
from src.taglish_transcriber.review_engine import (
    GrammarDictionReviewEngine,
    compare_live_and_final,
)


def test_grammar_and_diction_are_comments_only() -> None:
    entry = TranscriptSegment(
        1.0,
        4.0,
        "Um, he don't know the the exact thing.",
        average_log_probability=-1.2,
    )
    comments = GrammarDictionReviewEngine().review([entry])
    categories = {comment.category for comment in comments}

    assert "Grammar" in categories
    assert "Diction" in categories
    assert "Accuracy check" in categories
    assert entry.text == "Um, he don't know the the exact thing."


def test_live_final_difference_is_flagged_for_wav_review() -> None:
    live = [TranscriptSegment(0.0, 3.0, "The amount is fifteen thousand pesos.")]
    final = [TranscriptSegment(0.0, 3.0, "The amount is fifty thousand pesos.")]

    comments = compare_live_and_final(live, final, similarity_threshold=0.95)

    assert len(comments) == 1
    assert comments[0].category == "WAV verification"
    assert comments[0].severity == "Check audio"
