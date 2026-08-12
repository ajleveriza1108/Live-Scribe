from __future__ import annotations

from src.taglish_transcriber.config import (
    ENGLISH_VARIANT_LABELS,
    LANGUAGE_AMERICAN_ENGLISH,
    LANGUAGE_AUSTRALIAN_ENGLISH,
    LANGUAGE_BRITISH_ENGLISH,
    LANGUAGE_CANADIAN_ENGLISH,
    LANGUAGE_ENGLISH,
    LANGUAGE_FILIPINO_ENGLISH,
    LANGUAGE_INDIAN_ENGLISH,
    LANGUAGE_LABEL_TO_CODE,
    language_priority_terms,
    language_prompt,
)


def test_generic_english_remains_region_neutral() -> None:
    prompt = language_prompt(LANGUAGE_ENGLISH)
    assert prompt.startswith("Faithful verbatim transcript in English.")
    assert "wide range of English accents" in prompt
    assert "Do not force a regional vocabulary" in prompt
    assert language_priority_terms(LANGUAGE_ENGLISH) == ()


def test_optional_english_locale_profiles_share_the_same_asr_language() -> None:
    expected = {
        LANGUAGE_ENGLISH,
        LANGUAGE_AMERICAN_ENGLISH,
        LANGUAGE_BRITISH_ENGLISH,
        LANGUAGE_AUSTRALIAN_ENGLISH,
        LANGUAGE_CANADIAN_ENGLISH,
        LANGUAGE_INDIAN_ENGLISH,
        LANGUAGE_FILIPINO_ENGLISH,
    }
    assert set(ENGLISH_VARIANT_LABELS) == expected
    assert all(LANGUAGE_LABEL_TO_CODE[label] == "en" for label in expected)


def test_locale_prompts_do_not_force_regional_terms() -> None:
    for label in (
        LANGUAGE_AMERICAN_ENGLISH,
        LANGUAGE_BRITISH_ENGLISH,
        LANGUAGE_AUSTRALIAN_ENGLISH,
        LANGUAGE_CANADIAN_ENGLISH,
        LANGUAGE_INDIAN_ENGLISH,
    ):
        assert "Do not invent" in language_prompt(label)
