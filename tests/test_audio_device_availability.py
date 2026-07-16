from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_microphone_info_has_availability_state() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "audio.py"
    ).read_text(encoding="utf-8")
    assert "available: bool = True" in source
    assert "sd.check_input_settings" in source
    assert "— Unavailable" in source


def test_whole_dropdown_supports_disabled_items() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "ui_widgets.py"
    ).read_text(encoding="utf-8")
    assert "class WholeClickableDropdown" in source
    assert "disabled_values" in source
    assert "tk_popup" in source



def test_dropdown_sync_calls_base_configure_directly() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "ui_widgets.py"
    ).read_text(encoding="utf-8")
    assert 'self._dropdown_ready = False' in source
    assert 'ctk.CTkButton.configure(self, text=' in source
    assert 'getattr(self, "_dropdown_ready", False)' in source
