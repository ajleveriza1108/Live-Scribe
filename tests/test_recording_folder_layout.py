from src.taglish_transcriber.audio import recording_parts_dir
from src.taglish_transcriber.paths import RECORDING_FINAL_DIR, RECORDING_IN_PROGRESS_DIR, new_recording_path

def test_new_recording_uses_final_output_folder():
    assert new_recording_path("Office Meeting").parent == RECORDING_FINAL_DIR

def test_parts_use_in_progress_folder():
    parts=recording_parts_dir(RECORDING_FINAL_DIR/"sample-session.wav")
    assert parts.parent == RECORDING_IN_PROGRESS_DIR
