from src.taglish_transcriber.transcript import TranscriptEntry
from src.taglish_transcriber.transcript_summary import summarize_entries


def test_summary_formats_speakers_and_extracts_actions() -> None:
    entries = [
        TranscriptEntry(0, 2, "we reviewed the launch plan", speaker="Alex"),
        TranscriptEntry(2, 4, "the team agreed to release on Friday", speaker="Alex"),
        TranscriptEntry(4, 7, "Maria will send the final files by Thursday", speaker="Maria"),
        TranscriptEntry(7, 10, "the customer requested a shorter onboarding guide", speaker="Alex"),
    ]
    result = summarize_entries(entries)
    rendered = result.render()

    assert "QUICK SUMMARY" in rendered
    assert "FORMATTED TRANSCRIPT" in rendered
    assert "Alex:" in result.formatted_transcript
    assert "Maria:" in result.formatted_transcript
    assert any("agreed" in item.casefold() for item in result.decisions)
    assert any("will send" in item.casefold() for item in result.action_items)


def test_summary_does_not_modify_source_entries() -> None:
    entries = [TranscriptEntry(0, 1, "hello everyone", speaker="Speaker")]
    summarize_entries(entries)
    assert entries[0].text == "hello everyone"
