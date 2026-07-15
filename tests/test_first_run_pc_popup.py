from pathlib import Path

def test_pc_popup_depends_only_on_first_run_completion():
    source=(Path(__file__).resolve().parents[1]/"src"/"taglish_transcriber"/"ui.py").read_text()
    assert "self.first_run_hardware_notice = not self.settings.hardware_check_completed" in source
    block=source.split("self.first_run_hardware_notice =",1)[1].split("self.hardware_assessment =",1)[0]
    assert "hardware_check_version <" not in block
