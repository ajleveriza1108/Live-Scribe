from src.taglish_transcriber.ui import TaglishTranscriberApp


def test_required_ui_handlers_exist() -> None:
    required = (
        "_start_requested",
        "_stop_requested",
        "_verify_wav_requested",
        "_download_model_requested",
        "_save_docx",
        "_save_txt",
        "_save_srt",
    )

    missing = [
        name for name in required
        if not hasattr(TaglishTranscriberApp, name)
    ]

    assert not missing, f"Missing UI handlers: {missing}"
