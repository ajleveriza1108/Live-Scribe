from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_recorded_file_action_is_prominent():
    s=(ROOT/"src/taglish_transcriber/productivity_features.py").read_text()
    assert "Already have a recorded video or audio file?" in s
    assert "Choose Video or Audio File" in s

def test_vocabulary_notice():
    s=(ROOT/"src/taglish_transcriber/vocabulary_dialog.py").read_text()
    assert "Offline and private on this device" in s
