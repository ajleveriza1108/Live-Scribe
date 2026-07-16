from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Iterable

from .paths import INTERVIEW_PROFILES_FILE, atomic_write_text, ensure_app_directories


QUESTION_CATEGORIES = (
    "Introduction",
    "Resume and experience",
    "Motivation and company",
    "Strengths and weaknesses",
    "Behavioral — teamwork",
    "Behavioral — conflict",
    "Behavioral — leadership",
    "Behavioral — failure",
    "Behavioral — achievement",
    "Problem solving",
    "Communication",
    "Time and priorities",
    "Adaptability",
    "Ethics and integrity",
    "Remote work",
    "Role-specific",
    "Salary and availability",
    "Closing",
    "Questions for the interviewer",
)

QUESTION_STARTERS = (
    "tell me",
    "describe",
    "explain",
    "how",
    "what",
    "why",
    "when",
    "where",
    "which",
    "who",
    "can you",
    "could you",
    "would you",
    "give me",
    "walk me",
    "share an example",
)

CORE_QUESTION_TEMPLATES: tuple[tuple[str, str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "Introduction",
        "Tell me about yourself.",
        (
            "Walk me through your background.",
            "Can you introduce yourself?",
            "Give me a brief overview of your experience.",
            "Tell me about your professional journey.",
        ),
        ("background", "introduce", "experience", "career", "yourself"),
    ),
    (
        "Introduction",
        "Walk me through your resume.",
        (
            "Can you explain your work history?",
            "Take me through your previous roles.",
            "How has your career developed?",
        ),
        ("resume", "work history", "previous roles", "career"),
    ),
    (
        "Motivation and company",
        "Why do you want this job?",
        (
            "What interests you about this position?",
            "Why are you applying for this role?",
            "What attracted you to this opportunity?",
        ),
        ("want", "job", "position", "role", "interested", "opportunity"),
    ),
    (
        "Motivation and company",
        "Why do you want to work for this company?",
        (
            "What interests you about our company?",
            "Why did you choose our organization?",
            "What do you know about us?",
        ),
        ("company", "organization", "work for us", "know about us"),
    ),
    (
        "Motivation and company",
        "Why should we hire you?",
        (
            "What makes you the strongest candidate?",
            "What value would you bring to this position?",
            "Why are you a good fit for this role?",
        ),
        ("hire", "candidate", "value", "good fit", "bring"),
    ),
    (
        "Strengths and weaknesses",
        "What are your greatest strengths?",
        (
            "What are you particularly good at?",
            "Which strengths would you bring to this job?",
            "What would your colleagues say you do well?",
        ),
        ("strength", "good at", "do well", "bring"),
    ),
    (
        "Strengths and weaknesses",
        "What is one weakness you are improving?",
        (
            "What is your greatest weakness?",
            "Which area are you currently developing?",
            "What professional skill are you trying to improve?",
        ),
        ("weakness", "improve", "developing", "development area"),
    ),
    (
        "Behavioral — achievement",
        "Tell me about an achievement you are proud of.",
        (
            "What is your greatest professional accomplishment?",
            "Describe a result you are proud of.",
            "What achievement best represents your ability?",
        ),
        ("achievement", "accomplishment", "proud", "result"),
    ),
    (
        "Behavioral — failure",
        "Tell me about a mistake or failure and what you learned.",
        (
            "Describe a time something did not go as planned.",
            "Tell me about a professional mistake.",
            "What failure taught you the most?",
        ),
        ("mistake", "failure", "learned", "did not go as planned"),
    ),
    (
        "Behavioral — teamwork",
        "Describe a successful team experience.",
        (
            "Tell me about a time you worked effectively with a team.",
            "How do you contribute to a team?",
            "Give an example of good teamwork.",
        ),
        ("team", "teamwork", "worked with", "collaborate"),
    ),
    (
        "Behavioral — conflict",
        "Tell me about a conflict at work and how you handled it.",
        (
            "Describe a disagreement with a colleague.",
            "How do you resolve workplace conflict?",
            "Tell me about a difficult working relationship.",
        ),
        ("conflict", "disagreement", "colleague", "resolve"),
    ),
    (
        "Behavioral — leadership",
        "Tell me about a time you showed leadership.",
        (
            "Describe a situation where you took the lead.",
            "How have you influenced other people?",
            "Give an example of leadership without authority.",
        ),
        ("leadership", "took the lead", "influenced", "authority"),
    ),
    (
        "Problem solving",
        "Describe a difficult problem you solved.",
        (
            "Tell me about a challenging issue you resolved.",
            "How do you approach complex problems?",
            "Give an example of your problem-solving ability.",
        ),
        ("problem", "challenge", "solved", "resolved", "approach"),
    ),
    (
        "Time and priorities",
        "How do you prioritize multiple urgent tasks?",
        (
            "How do you manage competing deadlines?",
            "What do you do when everything feels urgent?",
            "How do you organize a heavy workload?",
        ),
        ("prioritize", "urgent", "deadlines", "workload", "multiple tasks"),
    ),
    (
        "Communication",
        "Tell me about a time you explained something complex clearly.",
        (
            "How do you communicate technical or difficult information?",
            "Describe a situation that required clear communication.",
            "How do you adapt your communication style?",
        ),
        ("communicate", "explained", "complex", "clearly", "communication"),
    ),
    (
        "Adaptability",
        "Tell me about a time you adapted to change.",
        (
            "How do you respond to changing priorities?",
            "Describe a major change you handled.",
            "How do you work when requirements change?",
        ),
        ("adapt", "change", "changing priorities", "requirements"),
    ),
    (
        "Ethics and integrity",
        "Tell me about a time you had to make an ethical decision.",
        (
            "How do you handle confidential information?",
            "Describe a situation that tested your integrity.",
            "What would you do if asked to do something inappropriate?",
        ),
        ("ethical", "integrity", "confidential", "inappropriate"),
    ),
    (
        "Remote work",
        "How do you stay productive when working remotely?",
        (
            "How do you communicate in a remote team?",
            "What is your approach to working from home?",
            "How do you avoid distractions while remote?",
        ),
        ("remote", "working from home", "productive", "distractions"),
    ),
    (
        "Resume and experience",
        "Why are you leaving your current job?",
        (
            "Why did you leave your previous position?",
            "What is motivating your job search?",
            "Why are you considering a career move?",
        ),
        ("leaving", "left", "job search", "career move"),
    ),
    (
        "Resume and experience",
        "Can you explain this employment gap?",
        (
            "What were you doing during this gap?",
            "Why is there a break in your work history?",
            "Tell me about the period between these jobs.",
        ),
        ("employment gap", "break", "work history", "between jobs"),
    ),
    (
        "Salary and availability",
        "What are your salary expectations?",
        (
            "What compensation are you looking for?",
            "What salary range would you accept?",
            "What are your pay expectations?",
        ),
        ("salary", "compensation", "pay", "range"),
    ),
    (
        "Salary and availability",
        "When can you start?",
        (
            "What is your availability?",
            "How soon could you begin?",
            "Do you have a notice period?",
        ),
        ("start", "availability", "begin", "notice period"),
    ),
    (
        "Closing",
        "Where do you see yourself in five years?",
        (
            "What are your long-term career goals?",
            "How does this role fit your career plan?",
            "What do you hope to achieve over the next few years?",
        ),
        ("five years", "career goals", "long term", "career plan"),
    ),
    (
        "Closing",
        "Is there anything else you would like us to know?",
        (
            "What have we not asked that you want to mention?",
            "Is there anything you would like to add?",
            "What final point should we know about you?",
        ),
        ("anything else", "add", "final point", "not asked"),
    ),
    (
        "Questions for the interviewer",
        "Do you have any questions for us?",
        (
            "What would you like to ask us?",
            "Is there anything you want to know about the role?",
            "What questions do you have?",
        ),
        ("questions for us", "ask us", "want to know"),
    ),
)

ROLE_QUESTION_MAP: dict[str, tuple[str, ...]] = {
    "software": (
        "Describe a difficult software bug you diagnosed and fixed.",
        "How do you approach an unfamiliar codebase?",
        "How do you test your work before release?",
        "How do you handle changing technical requirements?",
        "Explain a technical trade-off you made.",
        "How do you review another developer's code?",
        "Describe a production incident and your response.",
        "How do you protect application and user data?",
    ),
    "developer": (
        "Describe a difficult software bug you diagnosed and fixed.",
        "How do you design maintainable code?",
        "How do you estimate development work?",
        "How do you collaborate with product and design teams?",
        "Which development tools are you strongest with?",
    ),
    "virtual assistant": (
        "How do you manage tasks for multiple clients?",
        "How do you handle unclear instructions?",
        "Which productivity and communication tools have you used?",
        "How do you protect confidential client information?",
        "Describe a time you prevented or corrected an administrative mistake.",
    ),
    "customer service": (
        "How do you handle an angry customer?",
        "Describe a time you turned a negative interaction into a positive one.",
        "How do you balance speed and accuracy?",
        "What does excellent customer service mean to you?",
        "How do you handle a request you cannot immediately solve?",
    ),
    "sales": (
        "Describe your sales process.",
        "How do you respond to objections?",
        "Tell me about a difficult target you achieved.",
        "How do you qualify a potential customer?",
        "How do you maintain customer relationships after a sale?",
    ),
    "teacher": (
        "How do you support students with different learning needs?",
        "Describe a lesson that did not work and what you changed.",
        "How do you manage classroom behavior?",
        "How do you measure student progress?",
        "How do you communicate with parents or guardians?",
    ),
    "manager": (
        "How do you set expectations for a team?",
        "Describe a difficult performance conversation.",
        "How do you delegate work?",
        "How do you develop team members?",
        "How do you make decisions with incomplete information?",
    ),
    "accounting": (
        "How do you ensure financial accuracy?",
        "Describe a discrepancy you found and corrected.",
        "How do you manage month-end deadlines?",
        "Which accounting systems have you used?",
        "How do you protect confidential financial information?",
    ),
    "data": (
        "Describe a data-quality problem you solved.",
        "How do you explain analysis to a nontechnical audience?",
        "How do you validate your results?",
        "Which tools do you use for data analysis?",
        "Tell me about a decision influenced by your analysis.",
    ),
}


@dataclass(slots=True)
class InterviewQuestion:
    id: str
    category: str
    question: str
    alternatives: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    prepared_answer: str = ""
    answer_points: list[str] = field(default_factory=list)
    source: str = "template"
    used_count: int = 0


@dataclass(slots=True)
class InterviewProfile:
    id: str
    name: str
    applicant_name: str = ""
    target_job: str = ""
    company: str = ""
    interview_type: str = "General interview"
    preferred_answer_style: str = "Concise"
    preferred_answer_length: str = "30–45 seconds"
    resume_text: str = ""
    job_description: str = ""
    experience: str = ""
    skills: str = ""
    projects: str = ""
    strengths: str = ""
    weaknesses: str = ""
    salary_preference: str = ""
    availability: str = ""
    company_notes: str = ""
    questions: list[InterviewQuestion] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class QuestionMatch:
    question: InterviewQuestion | None
    confidence: float
    reason: str
    live_question: str


@dataclass(frozen=True, slots=True)
class AssistantSuggestion:
    question: str
    answer: str
    points: tuple[str, ...]
    source: str
    confidence: float = 0.0
    matched_question: str = ""


def _normalise(text: str) -> str:
    clean = re.sub(r"[^\w\s]", " ", text.casefold(), flags=re.UNICODE)
    return " ".join(clean.split())


def _tokens(text: str) -> set[str]:
    stop = {
        "a", "an", "and", "are", "as", "at", "be", "can", "could", "do",
        "for", "from", "how", "i", "in", "is", "it", "me", "my", "of",
        "on", "or", "our", "please", "tell", "that", "the", "this", "to",
        "us", "what", "when", "where", "which", "who", "why", "with",
        "would", "you", "your",
    }
    return {token for token in _normalise(text).split() if len(token) > 2 and token not in stop}


def looks_like_question(text: str) -> bool:
    clean = _normalise(text)
    if not clean or len(clean.split()) < 3:
        return False
    if text.strip().endswith("?"):
        return True
    return any(clean.startswith(starter) for starter in QUESTION_STARTERS)


def _answer_points(profile: InterviewProfile, category: str) -> list[str]:
    candidates: list[str] = []
    if category in {"Introduction", "Resume and experience"}:
        candidates.extend([profile.experience, profile.skills, profile.projects])
    elif category in {"Motivation and company", "Closing"}:
        candidates.extend([profile.target_job, profile.company_notes, profile.strengths])
    elif category.startswith("Behavioral") or category in {
        "Problem solving", "Communication", "Time and priorities", "Adaptability"
    }:
        candidates.extend([profile.projects, profile.experience, profile.strengths])
    elif category == "Strengths and weaknesses":
        candidates.extend([profile.strengths, profile.weaknesses, profile.skills])
    elif category == "Salary and availability":
        candidates.extend([profile.salary_preference, profile.availability])
    else:
        candidates.extend([profile.skills, profile.experience, profile.projects])

    points: list[str] = []
    for candidate in candidates:
        for part in re.split(r"[\n;•]+", candidate):
            value = " ".join(part.strip().split())
            if value and value not in points:
                points.append(value[:180])
            if len(points) >= 4:
                return points
    return points


def _prepared_answer(profile: InterviewProfile, question: str, category: str) -> str:
    points = _answer_points(profile, category)
    if not points:
        return (
            "Use a truthful example from your own experience. Start with the situation, "
            "explain your responsibility and action, then end with the result or lesson."
        )
    if category == "Introduction":
        return (
            f"I am pursuing {profile.target_job or 'this opportunity'} and my background includes "
            + "; ".join(points[:3])
            + ". I am especially interested in applying these strengths in this position."
        )
    if category == "Salary and availability":
        return " ".join(points[:2])
    if category == "Questions for the interviewer":
        return (
            "Ask about the team's priorities, how success is measured in the first 90 days, "
            "the working style of the team, and the next step in the hiring process."
        )
    return (
        "A strong answer can focus on: "
        + "; ".join(points)
        + ". Keep the answer truthful and connect the example directly to the role."
    )


def prepare_question_bank(profile: InterviewProfile) -> list[InterviewQuestion]:
    questions: list[InterviewQuestion] = []
    seen: set[str] = set()

    for category, question, alternatives, keywords in CORE_QUESTION_TEMPLATES:
        key = _normalise(question)
        if key in seen:
            continue
        seen.add(key)
        points = _answer_points(profile, category)
        questions.append(
            InterviewQuestion(
                id=uuid.uuid4().hex,
                category=category,
                question=question,
                alternatives=list(alternatives),
                keywords=list(keywords),
                prepared_answer=_prepared_answer(profile, question, category),
                answer_points=points,
            )
        )

    haystack = " ".join(
        (
            profile.target_job,
            profile.job_description,
            profile.skills,
            profile.experience,
        )
    ).casefold()
    role_questions: list[str] = []
    for marker, values in ROLE_QUESTION_MAP.items():
        if marker in haystack:
            role_questions.extend(values)

    # General role-specific prompts based on the actual job title and description.
    role = profile.target_job.strip() or "this role"
    role_questions.extend(
        (
            f"What experience do you have that is most relevant to {role}?",
            f"Which skills are most important for success as {role}?",
            f"Describe a realistic challenge you expect in {role}.",
            f"How would you measure your success during the first 90 days as {role}?",
            f"Which part of {role} would require the most learning for you?",
        )
    )

    for question in role_questions:
        key = _normalise(question)
        if not key or key in seen:
            continue
        seen.add(key)
        category = "Role-specific"
        words = sorted(_tokens(question))
        questions.append(
            InterviewQuestion(
                id=uuid.uuid4().hex,
                category=category,
                question=question,
                alternatives=[],
                keywords=words[:10],
                prepared_answer=_prepared_answer(profile, question, category),
                answer_points=_answer_points(profile, category),
                source="role template",
            )
        )

    return questions


class PreparedQuestionMatcher:
    def __init__(self, questions: Iterable[InterviewQuestion]) -> None:
        self.questions = list(questions)

    @staticmethod
    def _score(live: str, candidate: str, keywords: Iterable[str]) -> float:
        live_n = _normalise(live)
        cand_n = _normalise(candidate)
        sequence = SequenceMatcher(None, live_n, cand_n).ratio()

        live_tokens = _tokens(live)
        candidate_tokens = _tokens(candidate)
        union = live_tokens | candidate_tokens
        token_score = (len(live_tokens & candidate_tokens) / len(union)) if union else 0.0

        keyword_set = {_normalise(item) for item in keywords if _normalise(item)}
        keyword_hits = sum(1 for item in keyword_set if item in live_n)
        keyword_score = keyword_hits / max(1, len(keyword_set))

        containment = 1.0 if cand_n in live_n or live_n in cand_n else 0.0
        return min(
            1.0,
            sequence * 0.45
            + token_score * 0.30
            + keyword_score * 0.20
            + containment * 0.05,
        )

    def match(self, live_question: str) -> QuestionMatch:
        best_question: InterviewQuestion | None = None
        best_score = 0.0
        best_variant = ""

        for question in self.questions:
            variants = [question.question, *question.alternatives]
            for variant in variants:
                score = self._score(live_question, variant, question.keywords)
                if score > best_score:
                    best_score = score
                    best_question = question
                    best_variant = variant

        confidence = round(best_score * 100.0, 1)
        if best_question is None:
            reason = "No prepared question was close enough."
        elif confidence >= 85:
            reason = f"Strong prepared match through: {best_variant}"
        elif confidence >= 65:
            reason = f"Possible prepared match through: {best_variant}"
        else:
            reason = "No reliable prepared answer match."
        return QuestionMatch(best_question, confidence, reason, live_question)


class InterviewProfileStore:
    def __init__(self, path: Path = INTERVIEW_PROFILES_FILE) -> None:
        self.path = path

    def load(self) -> list[InterviewProfile]:
        ensure_app_directories()
        if not self.path.is_file():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []

        profiles: list[InterviewProfile] = []
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            raw_questions = raw.pop("questions", [])
            allowed = InterviewProfile.__dataclass_fields__
            values = {key: value for key, value in raw.items() if key in allowed}
            try:
                profile = InterviewProfile(**values)
            except TypeError:
                continue
            for item in raw_questions if isinstance(raw_questions, list) else []:
                if not isinstance(item, dict):
                    continue
                q_allowed = InterviewQuestion.__dataclass_fields__
                q_values = {key: value for key, value in item.items() if key in q_allowed}
                try:
                    profile.questions.append(InterviewQuestion(**q_values))
                except TypeError:
                    continue
            profiles.append(profile)
        return profiles

    def save(self, profiles: Iterable[InterviewProfile]) -> None:
        ensure_app_directories()
        atomic_write_text(
            self.path,
            json.dumps([asdict(profile) for profile in profiles], indent=2, ensure_ascii=False) + "\n",
        )


class LocalInterviewAI:
    """Small OpenAI-compatible client for a local llama.cpp server."""

    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:8080/v1/chat/completions",
        model_name: str = "local-interview-model",
        timeout: float = 45.0,
    ) -> None:
        self.endpoint = endpoint.strip()
        self.model_name = model_name.strip() or "local-interview-model"
        self.timeout = timeout

    def generate(
        self,
        *,
        profile: InterviewProfile,
        question: str,
        recent_context: str = "",
        on_token: Callable[[str], None] | None = None,
    ) -> AssistantSuggestion:
        prompt = (
            "You are a fast private interview assistant. Use only the applicant "
            "information provided. Never invent employment, qualifications, dates, "
            "certifications, achievements, or tools. Return concise speaking points "
            "first, then a natural answer of no more than 90 words. Do not show reasoning.\n\n"
            f"Target job: {profile.target_job}\n"
            f"Company: {profile.company}\n"
            f"Preferred style: {profile.preferred_answer_style}\n"
            f"Experience: {profile.experience}\n"
            f"Skills: {profile.skills}\n"
            f"Projects: {profile.projects}\n"
            f"Strengths: {profile.strengths}\n"
            f"Job description: {profile.job_description[:3500]}\n"
            f"Recent interview context: {recent_context[-1800:]}\n"
            f"Interviewer question: {question}\n"
        )
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "Reply immediately and truthfully. No hidden reasoning."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.25,
            "max_tokens": 180,
            "stream": False,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "The local Interview Assistant is not ready. Start the configured "
                "llama.cpp server or use Prepared Answers Only."
            ) from exc

        try:
            answer = str(result["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("The local Interview Assistant returned an unreadable response.")

        if on_token is not None:
            # The endpoint may not stream. Reveal the answer in short chunks so the
            # UI still begins updating immediately after the local response arrives.
            for word in answer.split():
                on_token(word + " ")

        lines = [line.strip(" •-\t") for line in answer.splitlines() if line.strip()]
        points = tuple(lines[:4])
        return AssistantSuggestion(
            question=question,
            answer=answer,
            points=points,
            source="Local AI",
        )


def prepared_suggestion(match: QuestionMatch) -> AssistantSuggestion | None:
    question = match.question
    if question is None or match.confidence < 65:
        return None
    question.used_count += 1
    return AssistantSuggestion(
        question=match.live_question,
        answer=question.prepared_answer,
        points=tuple(question.answer_points),
        source="Prepared answer",
        confidence=match.confidence,
        matched_question=question.question,
    )


def create_profile(name: str = "New Interview") -> InterviewProfile:
    return InterviewProfile(id=uuid.uuid4().hex, name=name)
