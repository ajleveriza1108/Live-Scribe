from src.taglish_transcriber.config import (
    LANGUAGE_DUTCH,
    LANGUAGE_ENGLISH,
    LANGUAGE_FILIPINO,
    LANGUAGE_FRENCH,
    LANGUAGE_GERMAN,
    LANGUAGE_ITALIAN,
    LANGUAGE_LABEL_TO_CODE,
    LANGUAGE_PORTUGUESE,
    LANGUAGE_SPANISH,
    LANGUAGE_TAGLISH,
    language_prompt,
)


def test_eight_languages_and_taglish_mode_are_available() -> None:
    expected_codes = {
        LANGUAGE_ENGLISH: "en",
        LANGUAGE_FILIPINO: "tl",
        LANGUAGE_SPANISH: "es",
        LANGUAGE_FRENCH: "fr",
        LANGUAGE_GERMAN: "de",
        LANGUAGE_ITALIAN: "it",
        LANGUAGE_PORTUGUESE: "pt",
        LANGUAGE_DUTCH: "nl",
    }
    for label, code in expected_codes.items():
        assert LANGUAGE_LABEL_TO_CODE[label] == code
    assert LANGUAGE_LABEL_TO_CODE[LANGUAGE_TAGLISH] is None


def test_taglish_prompt_preserves_code_switching() -> None:
    prompt = language_prompt(LANGUAGE_TAGLISH).casefold()
    assert "taglish" in prompt
    assert "do not translate" in prompt
