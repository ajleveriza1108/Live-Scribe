from __future__ import annotations

import csv
import json
import re
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .docx_export import DocxExportInfo, save_formatted_docx
from .models import TranscriptSegment
from .paths import APP_ROOT
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
    speaker: str = ""
    verified: bool = False


@dataclass(frozen=True, slots=True)
class TranscriptMarker:
    id: str
    timestamp: float
    kind: str
    note: str = ""


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


def _serialize_path(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        relative = path.resolve().relative_to(APP_ROOT.resolve())
        return "portable://" + relative.as_posix()
    except (OSError, ValueError):
        return str(path)


def _restore_path(value: str) -> Path | None:
    clean = value.strip()
    if not clean:
        return None
    prefix = "portable://"
    if clean.startswith(prefix):
        return APP_ROOT / Path(clean[len(prefix):])
    return Path(clean)


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
    def __init__(
        self,
        *,
        session_id: str | None = None,
        title: str = "",
        source_type: str = "live",
    ) -> None:
        self.session_id = session_id or uuid.uuid4().hex
        self.title = title.strip() or "Untitled Session"
        self.source_type = source_type
        self.live_entries: list[TranscriptEntry] = []
        self.final_entries: list[TranscriptEntry] = []
        self.review_comments: list[ReviewComment] = []
        self.markers: list[TranscriptMarker] = []
        self.recording_path: Path | None = None
        self.enhanced_recording_path: Path | None = None
        self.created_at = datetime.now().isoformat(timespec="seconds")
        self.updated_at = self.created_at
        self.language = ""
        self.topic = ""
        self.model = ""
        self.audio_input = ""

    @property
    def entries(self) -> list[TranscriptEntry]:
        return self.final_entries if self.final_entries else self.live_entries

    @property
    def is_finalized(self) -> bool:
        return bool(self.final_entries)

    @property
    def media_path(self) -> Path | None:
        return self.recording_path

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat(timespec="seconds")

    def clear(self) -> None:
        self.live_entries.clear()
        self.final_entries.clear()
        self.review_comments.clear()
        self.markers.clear()
        self.recording_path = None
        self.enhanced_recording_path = None
        self.touch()

    def add(self, segment: TranscriptSegment) -> TranscriptEntry | None:
        return self.add_live(segment)

    def add_live(self, segment: TranscriptSegment) -> TranscriptEntry | None:
        entry = _entry_from_segment(segment)
        if not entry.text:
            return None
        if self.live_entries and _normalise(self.live_entries[-1].text) == _normalise(entry.text):
            return None
        self.live_entries.append(entry)
        self.touch()
        return entry

    def set_final(
        self,
        segments: list[TranscriptSegment] | tuple[TranscriptSegment, ...],
        comments: list[ReviewComment] | tuple[ReviewComment, ...],
        *,
        recording_path: Path,
        enhanced_recording_path: Path | None,
    ) -> None:
        prior_speakers = {
            _normalise(entry.text): entry.speaker
            for entry in self.entries
            if entry.speaker
        }
        self.final_entries = []
        for segment in segments:
            if not segment.text.strip():
                continue
            entry = _entry_from_segment(segment)
            speaker = prior_speakers.get(_normalise(entry.text), "")
            self.final_entries.append(replace(entry, speaker=speaker))
        self.review_comments = list(comments)
        self.recording_path = recording_path
        self.enhanced_recording_path = enhanced_recording_path
        self.touch()

    def update_entry(
        self,
        index: int,
        *,
        text: str | None = None,
        speaker: str | None = None,
        verified: bool | None = None,
        use_live: bool = False,
    ) -> TranscriptEntry:
        entries = self.live_entries if use_live else self.entries
        if not 0 <= index < len(entries):
            raise IndexError("Transcript entry is no longer available.")
        current = entries[index]
        updated = replace(
            current,
            text=(" ".join(text.strip().split()) if text is not None else current.text),
            speaker=(speaker.strip() if speaker is not None else current.speaker),
            verified=(bool(verified) if verified is not None else current.verified),
        )
        entries[index] = updated
        self.touch()
        return updated

    def add_marker(self, timestamp: float, kind: str, note: str = "") -> TranscriptMarker:
        marker = TranscriptMarker(
            id=uuid.uuid4().hex,
            timestamp=max(0.0, float(timestamp)),
            kind=" ".join(kind.strip().split()) or "Important",
            note=" ".join(note.strip().split()),
        )
        self.markers.append(marker)
        self.markers.sort(key=lambda item: item.timestamp)
        self.touch()
        return marker

    def remove_marker(self, marker_id: str) -> bool:
        before = len(self.markers)
        self.markers = [marker for marker in self.markers if marker.id != marker_id]
        changed = len(self.markers) != before
        if changed:
            self.touch()
        return changed

    def marker_labels_at(self, timestamp: float, tolerance: float = 1.0) -> str:
        values = [
            marker.kind
            for marker in self.markers
            if abs(marker.timestamp - timestamp) <= tolerance
        ]
        return ", ".join(values)

    def plain_text(self, include_timestamps: bool = True, *, use_live: bool = False) -> str:
        entries = self.live_entries if use_live else self.entries
        lines: list[str] = []
        for entry in entries:
            pieces: list[str] = []
            if include_timestamps:
                pieces.append(f"[{format_clock(entry.start)}]")
            if entry.speaker:
                pieces.append(f"{entry.speaker}:")
            pieces.append(entry.text)
            lines.append(" ".join(pieces))
        return "\n".join(lines)

    def markdown_text(self) -> str:
        lines = [f"# {self.title}", ""]
        for entry in self.entries:
            prefix = f"**[{format_clock(entry.start)}]"
            if entry.speaker:
                prefix += f" {entry.speaker}"
            prefix += "**"
            verified = " ✓" if entry.verified else ""
            lines.append(f"{prefix}{verified} {entry.text}")
        if self.markers:
            lines.extend(["", "## Markers", ""])
            for marker in self.markers:
                note = f" — {marker.note}" if marker.note else ""
                lines.append(f"- [{format_clock(marker.timestamp)}] **{marker.kind}**{note}")
        return "\n".join(lines) + "\n"

    def srt_text(self) -> str:
        blocks: list[str] = []
        for index, entry in enumerate(self.entries, start=1):
            start = format_clock(entry.start, include_milliseconds=True)
            end_value = entry.end if entry.end > entry.start else entry.start + 1.0
            end = format_clock(end_value, include_milliseconds=True)
            speaker = f"{entry.speaker}: " if entry.speaker else ""
            blocks.append(f"{index}\n{start} --> {end}\n{speaker}{entry.text}")
        return "\n\n".join(blocks) + ("\n" if blocks else "")

    def vtt_text(self) -> str:
        blocks = ["WEBVTT", ""]
        for entry in self.entries:
            start = format_clock(entry.start, include_milliseconds=True).replace(",", ".")
            end_value = entry.end if entry.end > entry.start else entry.start + 1.0
            end = format_clock(end_value, include_milliseconds=True).replace(",", ".")
            speaker = f"<v {entry.speaker}>" if entry.speaker else ""
            blocks.extend([f"{start} --> {end}", f"{speaker}{entry.text}", ""])
        return "\n".join(blocks)

    def suggested_filename(self, extension: str) -> str:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_title = re.sub(r"[^A-Za-z0-9._-]+", "-", self.title).strip("-")[:60]
        safe_title = safe_title or "live-scribe-transcript"
        return f"{stamp}_{safe_title}.{extension.lstrip('.')}"

    def save_txt(self, path: Path, include_timestamps: bool = True) -> None:
        path.write_text(
            self.plain_text(include_timestamps=include_timestamps) + "\n",
            encoding="utf-8",
        )

    def save_srt(self, path: Path) -> None:
        path.write_text(self.srt_text(), encoding="utf-8")

    def save_vtt(self, path: Path) -> None:
        path.write_text(self.vtt_text(), encoding="utf-8")

    def save_markdown(self, path: Path) -> None:
        path.write_text(self.markdown_text(), encoding="utf-8")

    def save_csv(self, path: Path) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Start", "End", "Speaker", "Text", "Verified", "Markers"])
            for entry in self.entries:
                writer.writerow(
                    [
                        format_clock(entry.start),
                        format_clock(entry.end),
                        entry.speaker,
                        entry.text,
                        "Yes" if entry.verified else "No",
                        self.marker_labels_at(entry.start),
                    ]
                )

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

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "source_type": self.source_type,
            "live_entries": [asdict(entry) for entry in self.live_entries],
            "final_entries": [asdict(entry) for entry in self.final_entries],
            "review_comments": [asdict(comment) for comment in self.review_comments],
            "markers": [asdict(marker) for marker in self.markers],
            "recording_path": _serialize_path(self.recording_path),
            "enhanced_recording_path": _serialize_path(self.enhanced_recording_path),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "language": self.language,
            "topic": self.topic,
            "model": self.model,
            "audio_input": self.audio_input,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "TranscriptDocument":
        document = cls(
            session_id=str(raw.get("session_id") or uuid.uuid4().hex),
            title=str(raw.get("title") or "Recovered Session"),
            source_type=str(raw.get("source_type") or "live"),
        )
        document.live_entries = [
            TranscriptEntry(**item)
            for item in raw.get("live_entries", [])
            if isinstance(item, dict)
        ]
        document.final_entries = [
            TranscriptEntry(**item)
            for item in raw.get("final_entries", [])
            if isinstance(item, dict)
        ]
        document.review_comments = [
            ReviewComment(**item)
            for item in raw.get("review_comments", [])
            if isinstance(item, dict)
        ]
        document.markers = [
            TranscriptMarker(**item)
            for item in raw.get("markers", [])
            if isinstance(item, dict)
        ]
        recording = str(raw.get("recording_path") or "").strip()
        enhanced = str(raw.get("enhanced_recording_path") or "").strip()
        document.recording_path = _restore_path(recording)
        document.enhanced_recording_path = _restore_path(enhanced)
        document.created_at = str(raw.get("created_at") or document.created_at)
        document.updated_at = str(raw.get("updated_at") or document.updated_at)
        document.language = str(raw.get("language") or "")
        document.topic = str(raw.get("topic") or "")
        document.model = str(raw.get("model") or "")
        document.audio_input = str(raw.get("audio_input") or "")
        return document
