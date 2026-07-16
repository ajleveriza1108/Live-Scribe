from __future__ import annotations

from pathlib import Path

from src.taglish_transcriber.interview import (
    InterviewProfile,
    InterviewProfileStore,
    PreparedQuestionMatcher,
    looks_like_question,
    prepare_question_bank,
    prepared_suggestion,
)


def sample_profile() -> InterviewProfile:
    return InterviewProfile(
        id="profile-1",
        name="Software Developer Interview",
        applicant_name="Applicant",
        target_job="Software Developer",
        company="Example Company",
        experience="Built Python automation tools; maintained inventory workflows",
        skills="Python; debugging; Git; communication",
        projects="Created a supplier stock checker that reduced manual checking",
        strengths="Problem solving; careful testing",
        weaknesses="I am improving public speaking through regular practice",
        job_description="Develop, test, debug, and maintain Python applications.",
    )


def test_question_bank_is_broad_and_role_specific() -> None:
    profile = sample_profile()
    questions = prepare_question_bank(profile)
    assert len(questions) >= 30
    assert any(item.category == "Role-specific" for item in questions)
    assert any("software bug" in item.question.casefold() for item in questions)
    assert all(item.prepared_answer for item in questions)


def test_paraphrased_question_matches_prepared_answer() -> None:
    profile = sample_profile()
    matcher = PreparedQuestionMatcher(prepare_question_bank(profile))
    match = matcher.match("What makes you the strongest candidate for this position?")
    assert match.question is not None
    assert match.question.question == "Why should we hire you?"
    assert match.confidence >= 65
    suggestion = prepared_suggestion(match)
    assert suggestion is not None
    assert suggestion.source == "Prepared answer"


def test_question_detection() -> None:
    assert looks_like_question("Can you walk me through your background")
    assert looks_like_question("Why should we hire you?")
    assert not looks_like_question("Thank you for joining us today.")


def test_profile_store_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "interviews.json"
    store = InterviewProfileStore(path)
    profile = sample_profile()
    profile.questions = prepare_question_bank(profile)
    store.save([profile])
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].target_job == "Software Developer"
    assert len(loaded[0].questions) == len(profile.questions)
