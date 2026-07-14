from pathlib import Path


def test_notice_layout_text_is_simplified_and_responsive() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui.py"
    ).read_text(encoding="utf-8")

    assert "English, Tagalog, and Taglish transcription from a microphone or" not in source
    assert "This edition is optimized for English, Tagalog/Filipino, and Taglish." not in source
    assert "self.notice_message_label" in source
    assert "_update_notice_wraplength" in source
    assert 'notice_frame.bind("<Configure>", self._update_notice_wraplength)' in source
