from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .paths import KNOWLEDGE_DIR, SKILLS_DIR


@dataclass(frozen=True, slots=True)
class SkillFile:
    path: Path
    title: str
    content: str


class SkillLibrary:
    """Discover tiny Markdown skills and knowledge without loading another model."""

    def __init__(
        self,
        skills_dir: Path = SKILLS_DIR,
        knowledge_dir: Path = KNOWLEDGE_DIR,
    ) -> None:
        self.skills_dir = skills_dir
        self.knowledge_dir = knowledge_dir
        self.skills: list[SkillFile] = []
        self.knowledge: list[SkillFile] = []
        self.reload()

    def reload(self) -> None:
        self.skills = self._load_files(self.skills_dir, "*.skill.md")
        self.knowledge = self._load_files(self.knowledge_dir, "*.md")

    @staticmethod
    def _load_files(root: Path, pattern: str) -> list[SkillFile]:
        if not root.exists():
            return []
        output: list[SkillFile] = []
        for path in sorted(root.rglob(pattern)):
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            heading = next(
                (
                    line.lstrip("#").strip()
                    for line in content.splitlines()
                    if line.startswith("#")
                ),
                path.stem,
            )
            output.append(SkillFile(path=path, title=heading, content=content))
        return output

    def asr_hotwords(self) -> list[str]:
        """Read compact hints from `ASR hotwords` sections in Markdown files."""
        output: list[str] = []
        for item in [*self.skills, *self.knowledge]:
            in_section = False
            for line in item.content.splitlines():
                stripped = line.strip()
                if re.match(r"^#{1,6}\s+ASR hotwords\s*$", stripped, re.IGNORECASE):
                    in_section = True
                    continue
                if in_section and stripped.startswith("#"):
                    break
                if in_section and stripped.startswith("-"):
                    term = stripped[1:].strip()
                    if term:
                        output.append(term)
        return list(dict.fromkeys(output))

    def prompt_context(self, max_characters: int = 8_000) -> str:
        """Return a bounded context block for a future optional local post-editor."""
        parts: list[str] = []
        total = 0
        for item in [*self.skills, *self.knowledge]:
            block = f"\n\n## {item.title}\n{item.content.strip()}"
            if total + len(block) > max_characters:
                break
            parts.append(block)
            total += len(block)
        return "".join(parts).strip()
