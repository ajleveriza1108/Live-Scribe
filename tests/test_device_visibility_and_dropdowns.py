from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_inactive_input_and_output_devices_are_filtered() -> None:
    base = (
        ROOT / "src" / "taglish_transcriber" / "ui_base.py"
    ).read_text(encoding="utf-8")
    productivity = (
        ROOT / "src" / "taglish_transcriber" / "productivity_features.py"
    ).read_text(encoding="utf-8")

    assert "if microphone.available" in base
    assert "Inactive or unusable inputs are hidden." in base
    assert "if output.available" in productivity


def test_all_main_modern_dropdowns_use_whole_click_widget() -> None:
    ui = (
        ROOT / "src" / "taglish_transcriber" / "ui.py"
    ).read_text(encoding="utf-8")

    assert "self.audio_source_combo = WholeClickableDropdown" in ui
    assert "self.microphone_combo = WholeClickableDropdown" in ui
    assert "self.topic_combo = WholeClickableDropdown" in ui
    assert "self.topic_editor_combo = WholeClickableDropdown" in ui
    assert "self.model_combo = WholeClickableDropdown" in ui
    assert "combo = WholeClickableDropdown" in ui


def test_output_device_dropdown_is_in_microphone_monitor_panel() -> None:
    productivity = (
        ROOT / "src" / "taglish_transcriber" / "productivity_features.py"
    ).read_text(encoding="utf-8")

    assert "self.microphone_monitor_output_dropdown" in productivity
    assert 'text="Output device"' in productivity
    assert "Listen to this microphone" in productivity
