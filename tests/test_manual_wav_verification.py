from pathlib import Path


def test_wav_verification_is_manual() -> None:
    ui_source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "taglish_transcriber"
        / "ui.py"
    ).read_text(encoding="utf-8")

    assert "Verify from WAV" in ui_source
    assert "Stop & Save WAV" in ui_source
    assert "self._verify_wav_requested" in ui_source
    assert "if self.settings.final_accuracy_pass" not in ui_source
