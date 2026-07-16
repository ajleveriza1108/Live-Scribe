from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_modern_ui_explains_optional_live_noise_reduction() -> None:
    source = (ROOT / "src/taglish_transcriber/ui.py").read_text(encoding="utf-8")
    assert "Light live noise reduction for transcription (optional)" in source
    assert "the original WAV stays unchanged" in source
    assert "Reduce steady background noise during WAV verification" in source
    assert "self.live_noise_switch" in source

def test_session_receives_saved_live_noise_setting() -> None:
    source = (ROOT / "src/taglish_transcriber/ui_base.py").read_text(encoding="utf-8")
    assert "live_noise_reduction=self.live_noise_reduction_var.get()" in source
    assert "live_noise_reduction=self.settings.live_noise_reduction" in source
