from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .transcript import TranscriptEntry, format_clock


STOP_WORDS = {
    "a", "about", "after", "again", "all", "also", "am", "an", "and", "any",
    "are", "as", "at", "be", "because", "been", "before", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "he", "her", "here", "him", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "just", "me", "more", "my", "no", "not", "of", "on", "or",
    "our", "out", "so", "some", "than", "that", "the", "their", "them", "then",
    "there", "they", "this", "to", "too", "up", "us", "was", "we", "were",
    "what", "when", "where", "which", "who", "why", "will", "with", "would",
    "you", "your",
}

ACTION_PATTERNS = (
    r"\bwill\b",
    r"\bneed to\b",
    r"\bmust\b",
    r"\bshould\b",
    r"\bfollow up\b",
    r"\baction item\b",
    r"\bdeadline\b",
    r"\bassigned\b",
    r"\bby (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
)
DECISION_PATTERNS = (
    r"\bdecided\b",
    r"\bagreed\b",
    r"\bapproved\b",
    r"\bconfirmed\b",
    r"\bconcluded\b",
    r"\bwe are going to\b",
    r"\bthe plan is\b",
)


@dataclass(frozen=True, slots=True)
class TranscriptSummary:
    overview: str
    key_points: tuple[str, ...]
    action_items: tuple[str, ...]
    decisions: tuple[str, ...]
    formatted_transcript: str

    def render(self) -> str:
        sections = ["QUICK SUMMARY", "", self.overview or "No summary could be created."]
        sections.extend(["", "KEY POINTS"])
        sections.extend(f"• {item}" for item in self.key_points)
        sections.extend(["", "DECISIONS"])
        sections.extend(
            [f"• {item}" for item in self.decisions]
            or ["• No explicit decisions detected."]
        )
        sections.extend(["", "ACTION ITEMS"])
        sections.extend(
            [f"• {item}" for item in self.action_items]
            or ["• No explicit action items detected."]
        )
        sections.extend(["", "FORMATTED TRANSCRIPT", "", self.formatted_transcript])
        return "\n".join(sections).strip() + "\n"


def _clean_sentence(text: str) -> str:
    value = " ".join(text.strip().split())
    if not value:
        return ""
    if value[-1] not in ".!?":
        value += "."
    return value[0].upper() + value[1:] if value else value


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+", text.casefold())
        if len(token) > 2 and token not in STOP_WORDS
    ]


def _merge_entries(entries: Iterable[TranscriptEntry]) -> list[tuple[str, float, str]]:
    merged: list[tuple[str, float, str]] = []
    for entry in entries:
        text = _clean_sentence(entry.text)
        if not text:
            continue
        speaker = entry.speaker.strip() or "Speaker"
        if merged and merged[-1][0] == speaker:
            prior_speaker, prior_start, prior_text = merged[-1]
            merged[-1] = (prior_speaker, prior_start, f"{prior_text} {text}")
        else:
            merged.append((speaker, entry.start, text))
    return merged


def _formatted_transcript(entries: Iterable[TranscriptEntry]) -> str:
    groups = _merge_entries(entries)
    return "\n\n".join(
        f"[{format_clock(start)}] {speaker}:\n{text}"
        for speaker, start, text in groups
    )


def summarize_entries(entries: Iterable[TranscriptEntry], max_points: int = 6) -> TranscriptSummary:
    entry_list = list(entries)
    candidates: list[tuple[int, str]] = []
    for index, entry in enumerate(entry_list):
        sentence = _clean_sentence(entry.text)
        if sentence:
            candidates.append((index, sentence))

    if not candidates:
        return TranscriptSummary("", (), (), (), "")

    frequency = Counter(
        token for _index, sentence in candidates for token in _tokens(sentence)
    )
    if frequency:
        maximum = max(frequency.values())
        weights = {word: value / maximum for word, value in frequency.items()}
    else:
        weights = {}

    scored: list[tuple[float, int, str]] = []
    for index, sentence in candidates:
        words = _tokens(sentence)
        if not words:
            score = 0.0
        else:
            score = sum(weights.get(word, 0.0) for word in words) / math.sqrt(len(words))
        # Slight preference for early context and complete information.
        score += max(0.0, 0.12 - index * 0.002)
        if any(char.isdigit() for char in sentence):
            score += 0.08
        scored.append((score, index, sentence))

    best = sorted(scored, key=lambda item: item[0], reverse=True)[:max_points]
    best.sort(key=lambda item: item[1])
    key_points = tuple(item[2] for item in best)

    overview_parts = key_points[:3]
    overview = " ".join(overview_parts)
    if len(overview) > 650:
        overview = overview[:647].rstrip() + "..."

    action_items = tuple(
        sentence
        for _index, sentence in candidates
        if any(re.search(pattern, sentence, flags=re.IGNORECASE) for pattern in ACTION_PATTERNS)
    )[:8]
    decisions = tuple(
        sentence
        for _index, sentence in candidates
        if any(re.search(pattern, sentence, flags=re.IGNORECASE) for pattern in DECISION_PATTERNS)
    )[:8]

    return TranscriptSummary(
        overview=overview,
        key_points=key_points,
        action_items=action_items,
        decisions=decisions,
        formatted_transcript=_formatted_transcript(entry_list),
    )


@dataclass(frozen=True, slots=True)
class CallSummary:
    caller_or_contact: tuple[str, ...]
    reason_for_call: tuple[str, ...]
    contact_details: tuple[str, ...]
    appointment_or_schedule: tuple[str, ...]
    action_required: tuple[str, ...]
    follow_up: tuple[str, ...]
    key_points: tuple[str, ...]
    formatted_transcript: str

    def render(self) -> str:
        sections = ["CALL / CONVERSATION NOTES", ""]
        fields = (
            ("CALLER / CONTACT", self.caller_or_contact, "No explicit name detected."),
            ("REASON FOR CALL", self.reason_for_call, "No explicit reason detected."),
            ("CONTACT DETAILS", self.contact_details, "No explicit contact details detected."),
            ("APPOINTMENT / SCHEDULE", self.appointment_or_schedule, "No explicit appointment or schedule detected."),
            ("ACTION REQUIRED", self.action_required, "No explicit action item detected."),
            ("FOLLOW-UP", self.follow_up, "No explicit follow-up detected."),
            ("KEY POINTS", self.key_points, "No key points detected."),
        )
        for heading, values, fallback in fields:
            sections.append(heading)
            sections.extend([f"• {value}" for value in values] or [f"• {fallback}"])
            sections.append("")
        sections.extend(["SPEAKER-LABELLED TRANSCRIPT", "", self.formatted_transcript])
        return "\n".join(sections).strip() + "\n"


def _unique_sentences(values: Iterable[str], limit: int = 8) -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = _clean_sentence(value)
        key = clean.casefold()
        if not clean or key in seen:
            continue
        seen.add(key)
        output.append(clean)
        if len(output) >= limit:
            break
    return tuple(output)


def summarize_call_entries(entries: Iterable[TranscriptEntry]) -> CallSummary:
    """Create deterministic offline call notes without an LLM.

    The extractor intentionally keeps the original spoken sentences rather than
    inventing missing values. It is useful for reception, VA, customer-service,
    scheduling, and interview calls while remaining completely local.
    """

    entry_list = list(entries)
    sentences = [
        (entry.speaker.strip() or "Speaker", _clean_sentence(entry.text))
        for entry in entry_list
        if _clean_sentence(entry.text)
    ]

    name_patterns = (
        r"\bmy name is\b",
        r"\bthis is\b",
        r"\bmy name's\b",
        r"\bspeaking\b",
    )
    reason_patterns = (
        r"\bcalling (?:about|regarding|to|for)\b",
        r"\bcall(?:ing)? in regards? to\b",
        r"\bthe reason (?:for|i'm calling)\b",
        r"\bi need (?:help|to|an?|some)\b",
        r"\bi'm enquiring\b",
        r"\bi am enquiring\b",
    )
    appointment_patterns = (
        r"\bappointment\b",
        r"\bbooking\b",
        r"\bschedule\b",
        r"\breschedule\b",
        r"\bcancel(?:lation|led|ing)?\b",
        r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b(?:today|tomorrow|next week|this week)\b",
        r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    )
    follow_patterns = (
        r"\bfollow[ -]?up\b",
        r"\bcall (?:you|them|him|her) back\b",
        r"\bget back to\b",
        r"\bsend (?:you|them|him|her)\b",
        r"\bemail (?:you|them|him|her)\b",
        r"\bconfirm(?:ation)?\b",
    )
    contact_pattern = re.compile(
        r"(?:\b(?:\+?61|0)\s*\d[\d\s-]{7,}\b)|"
        r"(?:\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)|"
        r"(?:\b(?:phone|mobile|email|e-mail|postcode|address)\b)",
        flags=re.IGNORECASE,
    )

    def matching(patterns: tuple[str, ...]) -> tuple[str, ...]:
        return _unique_sentences(
            text
            for _speaker, text in sentences
            if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
        )

    contact_details = _unique_sentences(
        text for _speaker, text in sentences if contact_pattern.search(text)
    )
    action_required = _unique_sentences(
        text
        for _speaker, text in sentences
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in ACTION_PATTERNS)
    )

    general = summarize_entries(entry_list, max_points=6)
    return CallSummary(
        caller_or_contact=matching(name_patterns),
        reason_for_call=matching(reason_patterns),
        contact_details=contact_details,
        appointment_or_schedule=matching(appointment_patterns),
        action_required=action_required,
        follow_up=matching(follow_patterns),
        key_points=general.key_points,
        formatted_transcript=_formatted_transcript(entry_list),
    )
