from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .paths import SESSION_DATABASE_FILE, ensure_app_directories
from .transcript import TranscriptDocument


@dataclass(frozen=True, slots=True)
class SessionSummary:
    session_id: str
    title: str
    created_at: str
    updated_at: str
    source_type: str
    language: str
    topic: str
    duration_seconds: float
    recording_path: str
    finalized: bool

    @property
    def display(self) -> str:
        date = self.created_at.replace("T", " ")[:16]
        source = "File" if self.source_type == "imported" else "Live"
        return f"{date}  •  {source}  •  {self.title}"


class SessionStore:
    def __init__(self, path: Path = SESSION_DATABASE_FILE) -> None:
        ensure_app_directories()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    language TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    recording_path TEXT NOT NULL,
                    finalized INTEGER NOT NULL,
                    search_text TEXT NOT NULL,
                    document_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC)"
            )

    @staticmethod
    def _duration(document: TranscriptDocument) -> float:
        entries = document.entries
        return max((entry.end for entry in entries), default=0.0)

    @staticmethod
    def _search_text(document: TranscriptDocument) -> str:
        pieces = [
            document.title,
            document.language,
            document.topic,
            document.audio_input,
            document.plain_text(include_timestamps=False),
        ]
        pieces.extend(marker.kind + " " + marker.note for marker in document.markers)
        return "\n".join(pieces).casefold()

    def save(self, document: TranscriptDocument) -> None:
        document.touch()
        payload = json.dumps(document.to_dict(), ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id, title, created_at, updated_at, source_type,
                    language, topic, duration_seconds, recording_path,
                    finalized, search_text, document_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    title=excluded.title,
                    updated_at=excluded.updated_at,
                    source_type=excluded.source_type,
                    language=excluded.language,
                    topic=excluded.topic,
                    duration_seconds=excluded.duration_seconds,
                    recording_path=excluded.recording_path,
                    finalized=excluded.finalized,
                    search_text=excluded.search_text,
                    document_json=excluded.document_json
                """,
                (
                    document.session_id,
                    document.title,
                    document.created_at,
                    document.updated_at,
                    document.source_type,
                    document.language,
                    document.topic,
                    self._duration(document),
                    str(document.recording_path or ""),
                    1 if document.is_finalized else 0,
                    self._search_text(document),
                    payload,
                ),
            )

    def search(self, query: str = "", limit: int = 200) -> list[SessionSummary]:
        clean = query.strip().casefold()
        with self._connect() as connection:
            if clean:
                rows = connection.execute(
                    """
                    SELECT * FROM sessions
                    WHERE search_text LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (f"%{clean}%", limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [
            SessionSummary(
                session_id=row["session_id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                source_type=row["source_type"],
                language=row["language"],
                topic=row["topic"],
                duration_seconds=float(row["duration_seconds"]),
                recording_path=row["recording_path"],
                finalized=bool(row["finalized"]),
            )
            for row in rows
        ]

    def load(self, session_id: str) -> TranscriptDocument | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT document_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        raw = json.loads(row["document_json"])
        if not isinstance(raw, dict):
            return None
        return TranscriptDocument.from_dict(raw)

    def rename(self, session_id: str, title: str) -> bool:
        document = self.load(session_id)
        if document is None:
            return False
        document.title = " ".join(title.strip().split()) or document.title
        self.save(document)
        return True

    def delete(self, session_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
        return cursor.rowcount > 0
