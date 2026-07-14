from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .paths import TOPIC_PROFILES_FILE, ensure_app_directories


DEFAULT_TOPIC_PROFILE_ID = "general-conversation"

DEFAULT_TOPIC_PROFILES: tuple[dict[str, object], ...] = (
    {
        "id": "general-conversation",
        "name": "General Conversation",
        "description": (
            "Everyday conversations, personal notes, informal discussions, and recordings "
            "without a specialized subject."
        ),
        "important_terms": [],
        "starter": True,
    },
    {
        "id": "office-business-meeting",
        "name": "Office & Business Meeting",
        "description": (
            "Office discussions, team meetings, planning sessions, reports, projects, "
            "deadlines, budgets, clients, and action items."
        ),
        "important_terms": [
            "agenda", "minutes", "action item", "follow-up", "deadline",
            "deliverable", "department", "manager", "client", "budget",
            "invoice", "purchase order", "KPI", "ROI",
        ],
        "starter": True,
    },
    {
        "id": "school-class-lecture",
        "name": "School, Class & Lecture",
        "description": (
            "Classroom lessons, lectures, student discussions, assignments, examinations, "
            "presentations, and academic recordings."
        ),
        "important_terms": [
            "assignment", "syllabus", "lesson", "module", "lecture", "quiz",
            "examination", "project", "presentation", "teacher", "professor",
            "instructor", "student", "class discussion",
        ],
        "starter": True,
    },
    {
        "id": "online-meeting",
        "name": "Zoom, Google Meet & Online Meeting",
        "description": (
            "Remote classes, office calls, online conferences, virtual meetings, and "
            "screen-sharing sessions."
        ),
        "important_terms": [
            "Zoom", "Google Meet", "Microsoft Teams", "mute", "unmute",
            "screen sharing", "breakout room", "chat", "microphone", "camera",
            "connection", "presenter", "participant", "recording",
        ],
        "starter": True,
    },
    {
        "id": "interview-research",
        "name": "Interview & Research",
        "description": (
            "Job interviews, research interviews, surveys, oral histories, focus groups, "
            "and question-and-answer recordings."
        ),
        "important_terms": [
            "interviewer", "interviewee", "respondent", "participant",
            "questionnaire", "consent", "research", "methodology", "findings",
            "follow-up question", "focus group",
        ],
        "starter": True,
    },
    {
        "id": "church-sermon-bible-study",
        "name": "Church, Sermon & Bible Study",
        "description": (
            "Sermons, Bible studies, Sunday school, church meetings, ministry training, "
            "devotions, and religious presentations."
        ),
        "important_terms": [
            "Bible", "Scripture", "sermon", "Bible study", "Sunday school",
            "pastor", "preacher", "ministry", "discipleship", "fellowship",
            "prayer", "worship", "testimony",
        ],
        "starter": True,
    },
    {
        "id": "livestream-webinar-presentation",
        "name": "Livestream, Webinar & Presentation",
        "description": (
            "Livestreams, webinars, conferences, product demonstrations, public talks, "
            "training sessions, and formal presentations."
        ),
        "important_terms": [
            "livestream", "webinar", "presentation", "speaker", "presenter",
            "audience", "question and answer", "Q&A", "demonstration", "session",
            "conference", "workshop",
        ],
        "starter": True,
    },
    {
        "id": "technology-programming",
        "name": "Technology & Programming",
        "description": (
            "Software development, computer training, technical support, coding tutorials, "
            "IT meetings, and product-development discussions."
        ),
        "important_terms": [
            "Python", "PowerShell", "GitHub", "Visual Studio Code", "API", "JSON",
            "repository", "database", "frontend", "backend", "debugging",
            "deployment", "CustomTkinter", "Faster-Whisper",
        ],
        "starter": True,
    },
    {
        "id": "ecommerce-online-selling",
        "name": "E-commerce & Online Selling",
        "description": (
            "Online-store operations, product listings, customer support, inventory, "
            "suppliers, shipping, returns, and digital-product discussions."
        ),
        "important_terms": [
            "Etsy", "eBay", "Amazon", "listing", "SKU", "inventory", "supplier",
            "fulfillment", "tracking number", "return policy", "digital product",
            "customer support", "order",
        ],
        "starter": True,
    },
    {
        "id": "news-current-events",
        "name": "News & Current Events",
        "description": (
            "News reports, public announcements, community updates, government briefings, "
            "and discussions of current events."
        ),
        "important_terms": [
            "announcement", "breaking news", "press conference", "public advisory",
            "government agency", "local government", "community update",
            "official statement", "reporter", "correspondent",
        ],
        "starter": True,
    },
)


@dataclass(frozen=True, slots=True)
class TopicProfile:
    id: str
    name: str
    description: str
    important_terms: tuple[str, ...]
    starter: bool = False

    def context_prompt(self) -> str:
        pieces = [f"Topic profile: {self.name}."]
        if self.description:
            pieces.append(f"Recording context: {self.description}")
        return " ".join(pieces).strip()

    def terms_for_recognition(self) -> list[str]:
        values = [self.name, *self.important_terms]
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class TopicProfileManager:
    """Local, editable topic profiles used as recognition context."""

    MAX_NAME_LENGTH = 80
    MAX_DESCRIPTION_LENGTH = 500
    MAX_TERMS = 80
    MAX_TERM_LENGTH = 100

    def __init__(self, path: Path = TOPIC_PROFILES_FILE) -> None:
        self.path = path
        self._profiles: list[TopicProfile] = []
        self.reload()

    @property
    def profiles(self) -> tuple[TopicProfile, ...]:
        return tuple(self._profiles)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(profile.name for profile in self._profiles)

    @property
    def default_profile(self) -> TopicProfile:
        profile = self.get(DEFAULT_TOPIC_PROFILE_ID)
        if profile is not None:
            return profile
        if self._profiles:
            return self._profiles[0]
        self._write_profiles(self._default_profiles())
        self.reload()
        return self._profiles[0]

    @staticmethod
    def _default_profiles() -> list[TopicProfile]:
        return [
            TopicProfile(
                id=str(item["id"]),
                name=str(item["name"]),
                description=str(item["description"]),
                important_terms=tuple(str(value) for value in item["important_terms"]),
                starter=bool(item.get("starter", True)),
            )
            for item in DEFAULT_TOPIC_PROFILES
        ]

    def reload(self) -> None:
        ensure_app_directories()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_profiles(self._default_profiles())

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            profiles = self._parse_profiles(raw)
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            self._backup_invalid_file()
            profiles = self._default_profiles()
            self._write_profiles(profiles)

        if not profiles:
            profiles = self._default_profiles()
            self._write_profiles(profiles)

        self._profiles = profiles

    def _backup_invalid_file(self) -> None:
        if not self.path.exists():
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.path.with_name(f"{self.path.stem}.invalid-{stamp}{self.path.suffix}")
        try:
            shutil.copy2(self.path, backup)
        except OSError:
            pass

    def _parse_profiles(self, raw: object) -> list[TopicProfile]:
        if not isinstance(raw, list):
            raise ValueError("Topic profiles must be a JSON list.")

        output: list[TopicProfile] = []
        seen_ids: set[str] = set()
        seen_names: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            profile_id = str(item.get("id", "")).strip()
            name = self._clean_name(str(item.get("name", "")))
            description = self._clean_description(str(item.get("description", "")))
            terms = self.clean_terms(item.get("important_terms", []))
            if not profile_id or not name:
                continue
            if profile_id in seen_ids or name.casefold() in seen_names:
                continue
            seen_ids.add(profile_id)
            seen_names.add(name.casefold())
            output.append(
                TopicProfile(
                    id=profile_id,
                    name=name,
                    description=description,
                    important_terms=tuple(terms),
                    starter=bool(item.get("starter", False)),
                )
            )
        return output

    @classmethod
    def _clean_name(cls, name: str) -> str:
        value = " ".join(name.strip().split())
        if not value:
            raise ValueError("Enter a topic profile name.")
        if len(value) > cls.MAX_NAME_LENGTH:
            raise ValueError(
                f"Keep the topic name to {cls.MAX_NAME_LENGTH} characters or fewer."
            )
        return value

    @classmethod
    def _clean_description(cls, description: str) -> str:
        value = " ".join(description.strip().split())
        if len(value) > cls.MAX_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Keep the topic description to {cls.MAX_DESCRIPTION_LENGTH} characters or fewer."
            )
        return value

    @classmethod
    def clean_terms(cls, values: object) -> list[str]:
        if isinstance(values, str):
            candidates = re.split(r"[\n,;]+", values)
        elif isinstance(values, Iterable):
            candidates = [str(value) for value in values]
        else:
            candidates = []

        output: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            value = " ".join(str(candidate).strip().split())
            if not value:
                continue
            if len(value) > cls.MAX_TERM_LENGTH:
                raise ValueError(
                    f"Keep each important term to {cls.MAX_TERM_LENGTH} characters or fewer."
                )
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            output.append(value)
            if len(output) >= cls.MAX_TERMS:
                break
        return output

    def get(self, profile_id: str | None) -> TopicProfile | None:
        target = (profile_id or "").strip()
        for profile in self._profiles:
            if profile.id == target:
                return profile
        return None

    def get_by_name(self, name: str | None) -> TopicProfile | None:
        target = (name or "").strip().casefold()
        for profile in self._profiles:
            if profile.name.casefold() == target:
                return profile
        return None

    def add(
        self,
        name: str,
        description: str,
        important_terms: object,
    ) -> TopicProfile:
        clean_name = self._clean_name(name)
        if self.get_by_name(clean_name) is not None:
            raise ValueError(
                "A topic profile with that name already exists. Select it and use Save Changes."
            )

        profile = TopicProfile(
            id=self._new_id(clean_name),
            name=clean_name,
            description=self._clean_description(description),
            important_terms=tuple(self.clean_terms(important_terms)),
            starter=False,
        )
        self._write_profiles([*self._profiles, profile])
        self.reload()
        return self.get(profile.id) or profile

    def update(
        self,
        profile_id: str,
        name: str,
        description: str,
        important_terms: object,
    ) -> TopicProfile:
        existing = self.get(profile_id)
        if existing is None:
            raise ValueError("The selected topic profile no longer exists.")

        clean_name = self._clean_name(name)
        duplicate = self.get_by_name(clean_name)
        if duplicate is not None and duplicate.id != profile_id:
            raise ValueError("Another topic profile already uses that name.")

        updated = TopicProfile(
            id=existing.id,
            name=clean_name,
            description=self._clean_description(description),
            important_terms=tuple(self.clean_terms(important_terms)),
            starter=existing.starter,
        )
        profiles = [
            updated if profile.id == profile_id else profile
            for profile in self._profiles
        ]
        self._write_profiles(profiles)
        self.reload()
        return self.get(profile_id) or updated

    def remove(self, profile_id: str) -> bool:
        if len(self._profiles) <= 1:
            raise ValueError("Keep at least one topic profile.")
        if self.get(profile_id) is None:
            return False
        self._write_profiles(
            [profile for profile in self._profiles if profile.id != profile_id]
        )
        self.reload()
        return True

    @staticmethod
    def _new_id(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
        slug = slug[:48] or "topic"
        return f"{slug}-{uuid.uuid4().hex[:8]}"

    def _write_profiles(self, profiles: Iterable[TopicProfile]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = []
        for profile in profiles:
            item = asdict(profile)
            item["important_terms"] = list(profile.important_terms)
            payload.append(item)

        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
