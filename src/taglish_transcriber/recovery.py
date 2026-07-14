from __future__ import annotations

import json
import time
from pathlib import Path

from .paths import RECOVERY_FILE, atomic_write_text, ensure_app_directories
from .transcript import TranscriptDocument


class RecoveryManager:
    def __init__(self, path: Path = RECOVERY_FILE) -> None:
        self.path = path
        self._last_write = 0.0

    def save(
        self,
        document: TranscriptDocument,
        *,
        state: str,
        force: bool = False,
    ) -> None:
        now = time.monotonic()
        if not force and now - self._last_write < 5.0:
            return
        ensure_app_directories()
        payload = {
            "state": state,
            "document": document.to_dict(),
        }
        atomic_write_text(
            self.path,
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        )
        self._last_write = now

    def load(self) -> tuple[str, TranscriptDocument] | None:
        if not self.path.is_file():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict) or not isinstance(raw.get("document"), dict):
            return None
        return (
            str(raw.get("state") or "unfinished"),
            TranscriptDocument.from_dict(raw["document"]),
        )

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
