from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Iterable, Protocol


class EntryLike(Protocol):
    start: float
    text: str
    average_log_probability: float | None
    language_probability: float | None


@dataclass(frozen=True, slots=True)
class ReviewComment:
    timestamp: float
    category: str
    original: str
    suggestion: str
    explanation: str
    severity: str = "Suggestion"


def compare_live_and_final(
    live_entries: Iterable[EntryLike],
    final_entries: Iterable[EntryLike],
    *,
    similarity_threshold: float = 0.64,
) -> list[ReviewComment]:
    """Flag material differences between the fast live pass and full-WAV pass.

    This does not decide which text is correct. The full WAV remains the source
    that a person can replay when the two recognition passes disagree.
    """
    live = list(live_entries)
    final = list(final_entries)
    if not live or not final:
        return []

    comments: list[ReviewComment] = []
    for final_entry in final:
        overlapping = [
            item
            for item in live
            if getattr(item, "end", item.start + 1.0) >= final_entry.start - 0.75
            and item.start <= getattr(final_entry, "end", final_entry.start + 1.0) + 0.75
        ]
        if not overlapping:
            comments.append(
                ReviewComment(
                    timestamp=final_entry.start,
                    category="WAV verification",
                    original="No matching live phrase",
                    suggestion=final_entry.text,
                    explanation=(
                        "This phrase appeared only during the full-recording pass. "
                        "Replay the WAV here when names, numbers, or exact wording matter."
                    ),
                    severity="Check audio",
                )
            )
            continue

        live_text = " ".join(item.text for item in overlapping).strip()
        live_norm = re.sub(r"\W+", " ", live_text.casefold(), flags=re.UNICODE).strip()
        final_norm = re.sub(
            r"\W+", " ", final_entry.text.casefold(), flags=re.UNICODE
        ).strip()
        similarity = difflib.SequenceMatcher(None, live_norm, final_norm).ratio()
        if similarity >= similarity_threshold:
            continue
        comments.append(
            ReviewComment(
                timestamp=final_entry.start,
                category="WAV verification",
                original=f"Live: {live_text}",
                suggestion=f"Final pass: {final_entry.text}",
                explanation=(
                    f"The fast live pass and full-WAV pass differed materially "
                    f"(text similarity {similarity:.0%}). Replay this timestamp "
                    "before relying on exact names, numbers, quotations, or technical terms."
                ),
                severity="Check audio",
            )
        )
    return comments


class GrammarDictionReviewEngine:
    """Conservative comments only; never silently rewrites the transcript."""

    FILLERS = (
        "um",
        "uh",
        "ah",
        "erm",
        "you know",
        "like",
        "ano",
        "parang",
        "alam mo",
        "kumbaga",
    )
    VAGUE_WORDS = (
        "thing",
        "things",
        "stuff",
        "nice",
        "good",
        "bad",
        "bagay",
        "ganoon",
        "ganun",
    )
    DIRECT_RULES = (
        (re.compile(r"\bI is\b", re.IGNORECASE), "I am", "English subject–verb agreement"),
        (re.compile(r"\bhe don't\b", re.IGNORECASE), "he doesn't", "English subject–verb agreement"),
        (re.compile(r"\bshe don't\b", re.IGNORECASE), "she doesn't", "English subject–verb agreement"),
        (re.compile(r"\bthey was\b", re.IGNORECASE), "they were", "English subject–verb agreement"),
        (re.compile(r"\bwe was\b", re.IGNORECASE), "we were", "English subject–verb agreement"),
        (re.compile(r"\bmas better\b", re.IGNORECASE), "better or mas mabuti", "Avoid a double comparative"),
        (re.compile(r"\bpinaka best\b", re.IGNORECASE), "best or pinakamabuti", "Avoid a double superlative"),
    )

    def review(self, entries: Iterable[EntryLike]) -> list[ReviewComment]:
        comments: list[ReviewComment] = []
        for entry in entries:
            text = entry.text.strip()
            if not text:
                continue

            comments.extend(self._direct_grammar_comments(entry.start, text))
            comments.extend(self._filler_comments(entry.start, text))
            comments.extend(self._repetition_comments(entry.start, text))
            comments.extend(self._diction_comments(entry.start, text))
            comments.extend(self._sentence_comments(entry.start, text))
            comments.extend(self._confidence_comments(entry))

        unique: list[ReviewComment] = []
        seen: set[tuple[float, str, str]] = set()
        for comment in comments:
            key = (round(comment.timestamp, 2), comment.category, comment.original.casefold())
            if key not in seen:
                unique.append(comment)
                seen.add(key)
        return unique

    def _direct_grammar_comments(self, timestamp: float, text: str) -> list[ReviewComment]:
        output: list[ReviewComment] = []
        for pattern, suggestion, explanation in self.DIRECT_RULES:
            match = pattern.search(text)
            if match:
                output.append(
                    ReviewComment(
                        timestamp=timestamp,
                        category="Grammar",
                        original=match.group(0),
                        suggestion=suggestion,
                        explanation=explanation + ". Keep the original transcript unchanged if verbatim wording is required.",
                    )
                )
        return output

    def _filler_comments(self, timestamp: float, text: str) -> list[ReviewComment]:
        found: list[str] = []
        lowered = text.casefold()
        for filler in self.FILLERS:
            if re.search(rf"(?<!\w){re.escape(filler)}(?!\w)", lowered):
                found.append(filler)
        if not found:
            return []
        return [
            ReviewComment(
                timestamp=timestamp,
                category="Diction",
                original=", ".join(found),
                suggestion="Consider removing repeated filler words in a polished copy.",
                explanation="Filler words are valid in a verbatim transcript but may reduce clarity in a formal version.",
            )
        ]

    def _repetition_comments(self, timestamp: float, text: str) -> list[ReviewComment]:
        match = re.search(r"\b([A-Za-zÀ-ÿ]+)\s+\1\b", text, re.IGNORECASE)
        if not match:
            return []
        return [
            ReviewComment(
                timestamp=timestamp,
                category="Diction",
                original=match.group(0),
                suggestion=match.group(1),
                explanation="This may be an intentional spoken repetition or an ASR duplication. Verify it against the WAV recording.",
                severity="Check audio",
            )
        ]

    def _diction_comments(self, timestamp: float, text: str) -> list[ReviewComment]:
        lowered = text.casefold()
        found = [
            word
            for word in self.VAGUE_WORDS
            if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", lowered)
        ]
        if not found:
            return []
        return [
            ReviewComment(
                timestamp=timestamp,
                category="Diction",
                original=", ".join(found),
                suggestion="Use a more specific noun or description when preparing the polished document.",
                explanation="The spoken wording is preserved, but these terms may be vague without context.",
            )
        ]

    def _sentence_comments(self, timestamp: float, text: str) -> list[ReviewComment]:
        words = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
        output: list[ReviewComment] = []
        if len(words) >= 45:
            output.append(
                ReviewComment(
                    timestamp=timestamp,
                    category="Clarity",
                    original=text[:140] + ("…" if len(text) > 140 else ""),
                    suggestion="Consider dividing this into two or more sentences in the polished copy.",
                    explanation="Long spoken sentences can be difficult to read even when the transcription is accurate.",
                )
            )
        if text and text[0].isalpha() and text[0].islower():
            output.append(
                ReviewComment(
                    timestamp=timestamp,
                    category="Formatting",
                    original=text[:80],
                    suggestion=text[0].upper() + text[1:80],
                    explanation="The sentence may need initial capitalization after the final transcription review.",
                )
            )
        return output

    def _confidence_comments(self, entry: EntryLike) -> list[ReviewComment]:
        low_log_probability = (
            entry.average_log_probability is not None
            and entry.average_log_probability < -1.0
        )
        low_language_probability = (
            entry.language_probability is not None
            and entry.language_probability < 0.50
        )
        if not (low_log_probability or low_language_probability):
            return []
        return [
            ReviewComment(
                timestamp=entry.start,
                category="Accuracy check",
                original=entry.text,
                suggestion="Replay this section of the WAV recording and verify names, numbers, and uncommon terms.",
                explanation="The speech model reported lower confidence for this segment.",
                severity="Check audio",
            )
        ]
