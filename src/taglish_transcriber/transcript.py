from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .docx_export import DocxExportInfo, save_formatted_docx
from .models import TranscriptSegment
from .review_engine import ReviewComment


@dataclass(frozen=True, slots=True)
class TranscriptEntry:
    start: float
    end: float
    text: str
    detected_language: str | None = None
    language_probability: float | None = None
    average_log_probability: float | None = None
    no_speech_probability: float | None = None


def format_clock(seconds: float, include_milliseconds: bool = False) -> str:
    seconds = max(0.0, seconds)
    if include_milliseconds:
        total_milliseconds = int(round(seconds * 1000))
        hours, remainder = divmod(total_milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        whole_seconds, milliseconds = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"

    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}"


def _normalise(text: str) -> str:
    return re.sub(r"\W+", " ", text.casefold(), flags=re.UNICODE).strip()


def _entry_from_segment(segment: TranscriptSegment) -> TranscriptEntry:
    return TranscriptEntry(
        start=segment.start,
        end=max(segment.start, segment.end),
        text=" ".join(segment.text.strip().split()),
        detected_language=segment.detected_language,
        language_probability=segment.language_probability,
        average_log_probability=segment.average_log_probability,
        no_speech_probability=segment.no_speech_probability,
    )


class TranscriptDocument:
    def __init__(self) -> None:
        self.live_entries: list[TranscriptEntry] = []
        self.final_entries: list[TranscriptEntry] = []
        self.review_comments: list[ReviewComment] = []
        self.recording_path: Path | None = None
        self.enhanced_recording_path: Path | None = None

    @property
    def entries(self) -> list[TranscriptEntry]:
        return self.final_entries if self.final_entries else self.live_entries

    @property
    def is_finalized(self) -> bool:
        return bool(self.final_entries)

    def clear(self) -> None:
        self.live_entries.clear()
        self.final_entries.clear()
        self.review_comments.clear()
        self.recording_path = None
        self.enhanced_recording_path = None

    def add(self, segment: TranscriptSegment) -> TranscriptEntry | None:
        return self.add_live(segment)

    def add_live(self, segment: TranscriptSegment) -> TranscriptEntry | None:
        entry = _entry_from_segment(segment)
        if not entry.text:
            return None
        if self.live_entries and _normalise(self.live_entries[-1].text) == _normalise(entry.text):
            return None
        self.live_entries.append(entry)
        return entry

    def set_final(
        self,
        segments: list[TranscriptSegment] | tuple[TranscriptSegment, ...],
        comments: list[ReviewComment] | tuple[ReviewComment, ...],
        *,
        recording_path: Path,
        enhanced_recording_path: Path | None,
    ) -> None:
        self.final_entries = [
            _entry_from_segment(segment)
            for segment in segments
            if segment.text.strip()
        ]
        self.review_comments = list(comments)
        self.recording_path = recording_path
        self.enhanced_recording_path = enhanced_recording_path

    def plain_text(self, include_timestamps: bool = True, *, use_live: bool = False) -> str:
        entries = self.live_entries if use_live else self.entries
        if include_timestamps:
            return "\n".join(
                f"[{format_clock(entry.start)}] {entry.text}" for entry in entries
            )
        return "\n".join(entry.text for entry in entries)

    def srt_text(self) -> str:
        blocks: list[str] = []
        for index, entry in enumerate(self.entries, start=1):
            start = format_clock(entry.start, include_milliseconds=True)
            end_value = entry.end if entry.end > entry.start else entry.start + 1.0
            end = format_clock(end_value, include_milliseconds=True)
            blocks.append(f"{index}\n{start} --> {end}\n{entry.text}")
        return "\n\n".join(blocks) + ("\n" if blocks else "")

    def suggested_filename(self, extension: str) -> str:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"live-scribe-transcript_{stamp}.{extension.lstrip('.')}"

    def save_txt(self, path: Path, include_timestamps: bool = True) -> None:
        path.write_text(
            self.plain_text(include_timestamps=include_timestamps),
            encoding="utf-8",
        )

    def save_srt(self, path: Path) -> None:
        path.write_text(self.srt_text(), encoding="utf-8")

    def save_docx(
        self,
        path: Path,
        *,
        include_timestamps: bool,
        title: str,
        language: str,
        model: str,
        microphone: str,
        include_live_appendix: bool = True,
    ) -> None:
        save_formatted_docx(
            path,
            final_entries=self.entries,
            live_entries=self.live_entries if include_live_appendix else (),
            review_comments=self.review_comments,
            include_timestamps=include_timestamps,
            info=DocxExportInfo(
                title=title,
                language=language,
                model=model,
                microphone=microphone,
                recording_name=self.recording_path.name if self.recording_path else "Not available",
                enhanced_recording_name=(
                    self.enhanced_recording_path.name
                    if self.enhanced_recording_path
                    else "Not created"
                ),
                final_accuracy_pass=self.is_finalized,
            ),
        )
