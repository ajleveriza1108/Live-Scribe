from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .paths import DICTIONARY_DIR, ensure_app_directories


@dataclass(frozen=True, slots=True)
class DictionaryCorrection:
    original: str
    corrected: str
    source: str = "Dictionary"


@dataclass(frozen=True, slots=True)
class PronunciationEntry:
    written: str
    sounds_like: tuple[str, ...]


class VocabularyManager:
    """Local vocabulary, pronunciation hints, and controlled corrections."""

    def __init__(self, directory: Path = DICTIONARY_DIR) -> None:
        self.directory = directory
        self.custom_terms_path = directory / "custom_terms.txt"
        self.builtin_terms_path = directory / "starter_terms.txt"
        self.replacements_path = directory / "replacements.json"
        self.pronunciations_path = directory / "pronunciation_guide.json"
        self._terms: list[str] = []
        self._replacements: dict[str, str] = {}
        self._pronunciations: dict[str, tuple[str, ...]] = {}
        self.reload()

    def reload(self) -> None:
        ensure_app_directories()
        self.directory.mkdir(parents=True, exist_ok=True)
        self._terms = self._load_terms(self.builtin_terms_path)
        self._terms.extend(self._load_terms(self.custom_terms_path))
        self._replacements = self._load_replacements(self.replacements_path)
        self._pronunciations = self._load_pronunciations(self.pronunciations_path)
        self._terms.extend(self._pronunciations.keys())
        self._terms = list(dict.fromkeys(term for term in self._terms if term))

    @staticmethod
    def _load_terms(path: Path) -> list[str]:
        if not path.is_file():
            return []
        terms: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            terms.append(value)
        return terms

    @staticmethod
    def _load_replacements(path: Path) -> dict[str, str]:
        if not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        output: dict[str, str] = {}
        for source, target in raw.items():
            source_text = str(source).strip()
            target_text = str(target).strip()
            if source_text and target_text and source_text.casefold() != target_text.casefold():
                output[source_text] = target_text
        return output

    @staticmethod
    def _load_pronunciations(path: Path) -> dict[str, tuple[str, ...]]:
        if not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}

        output: dict[str, tuple[str, ...]] = {}
        for written, aliases in raw.items():
            written_text = str(written).strip()
            if not written_text:
                continue
            if isinstance(aliases, str):
                candidates = [aliases]
            elif isinstance(aliases, list):
                candidates = aliases
            else:
                continue
            cleaned = tuple(
                dict.fromkeys(
                    str(alias).strip()
                    for alias in candidates
                    if str(alias).strip()
                    and str(alias).strip().casefold() != written_text.casefold()
                )
            )
            if cleaned:
                output[written_text] = cleaned
        return output

    @property
    def terms(self) -> tuple[str, ...]:
        return tuple(self._terms)

    @property
    def pronunciation_entries(self) -> tuple[PronunciationEntry, ...]:
        return tuple(
            PronunciationEntry(written=written, sounds_like=aliases)
            for written, aliases in sorted(self._pronunciations.items(), key=lambda item: item[0].casefold())
        )

    def save_pronunciation(self, written: str, sounds_like: list[str] | tuple[str, ...]) -> None:
        written_text = " ".join(written.strip().split())
        aliases = tuple(
            dict.fromkeys(
                " ".join(alias.strip().split())
                for alias in sounds_like
                if alias.strip()
                and alias.strip().casefold() != written_text.casefold()
            )
        )
        if not written_text:
            raise ValueError("Enter the correct written spelling.")
        if not aliases:
            raise ValueError("Enter at least one pronunciation or common mistaken form.")

        data = dict(self._pronunciations)
        data[written_text] = aliases
        self._write_pronunciations(data)
        self.reload()

    def remove_pronunciation(self, written: str) -> bool:
        data = dict(self._pronunciations)
        if written not in data:
            return False
        del data[written]
        self._write_pronunciations(data)
        self.reload()
        return True

    def _write_pronunciations(self, data: dict[str, tuple[str, ...]]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        serializable = {
            written: list(aliases)
            for written, aliases in sorted(data.items(), key=lambda item: item[0].casefold())
        }
        self.pronunciations_path.write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def hotwords(self, extra_terms: list[str] | None = None, max_characters: int = 1200) -> str | None:
        values = list(self._terms)
        for written, aliases in self._pronunciations.items():
            values.append(written)
            values.extend(aliases)
        if extra_terms:
            values.extend(extra_terms)
        unique = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        chosen: list[str] = []
        length = 0
        for value in unique:
            addition = len(value) + (2 if chosen else 0)
            if length + addition > max_characters:
                break
            chosen.append(value)
            length += addition
        return ", ".join(chosen) if chosen else None

    @staticmethod
    def _apply_mapping(
        text: str,
        mapping: dict[str, tuple[str, str]],
    ) -> tuple[str, list[DictionaryCorrection]]:
        updated = text
        corrections: list[DictionaryCorrection] = []
        for source, (target, reason) in sorted(
            mapping.items(), key=lambda item: len(item[0]), reverse=True
        ):
            pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", re.IGNORECASE)
            matches = list(pattern.finditer(updated))
            if not matches:
                continue
            originals = list(dict.fromkeys(match.group(0) for match in matches))
            updated = pattern.sub(target, updated)
            for original in originals:
                corrections.append(
                    DictionaryCorrection(
                        original=original,
                        corrected=target,
                        source=reason,
                    )
                )
        return updated, corrections

    def apply_replacements(self, text: str) -> tuple[str, list[DictionaryCorrection]]:
        mapping: dict[str, tuple[str, str]] = {
            source: (target, "Dictionary replacement")
            for source, target in self._replacements.items()
        }
        for written, aliases in self._pronunciations.items():
            for alias in aliases:
                mapping.setdefault(alias, (written, "Pronunciation guide"))
        return self._apply_mapping(text, mapping)
