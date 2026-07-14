from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.taglish_transcriber import __version__
from src.taglish_transcriber.config import model_friendly_name
from src.taglish_transcriber.dictionary_engine import VocabularyManager
from src.taglish_transcriber.hardware import assess_this_pc
from src.taglish_transcriber.paths import APP_ROOT, TEMP_DIR, ensure_app_directories
from src.taglish_transcriber.portable import cleanup_stale_temp_files
from src.taglish_transcriber.skill_library import SkillLibrary
from src.taglish_transcriber.topic_profiles import TopicProfileManager


def run_self_test() -> int:
    """Check packaged imports without opening the desktop interface."""
    checks: dict[str, str] = {}
    modules = {
        "numpy": "numpy",
        "python-docx": "docx",
        "sounddevice": "sounddevice",
        "SoundCard system audio": "soundcard",
        "CustomTkinter GUI": "customtkinter",
        "faster-whisper": "faster_whisper",
        "CTranslate2": "ctranslate2",
        "PyAV": "av",
    }

    for label, module_name in modules.items():
        try:
            module = __import__(module_name)
            checks[label] = str(getattr(module, "__version__", "available"))
        except Exception as exc:  # pragma: no cover - used by packaged smoke tests
            print(json.dumps({"status": "failed", "module": label, "error": str(exc)}))
            return 1

    try:
        ensure_app_directories()
        write_test = APP_ROOT / "data" / ".portable-write-test"
        write_test.write_text("ok", encoding="utf-8")
        write_test.unlink(missing_ok=True)
        vocabulary = VocabularyManager()
        skills = SkillLibrary()
        topics = TopicProfileManager()
        hardware = assess_this_pc(run_storage_test=False)
        checks["dictionary terms"] = str(len(vocabulary.terms))
        checks["Markdown skills"] = str(len(skills.skills))
        checks["Markdown knowledge"] = str(len(skills.knowledge))
        checks["topic profiles"] = str(len(topics.profiles))
        checks["PC check"] = hardware.snapshot.summary()
        checks["recommended speech quality"] = model_friendly_name(hardware.recommended_model)
        checks["portable storage"] = hardware.snapshot.portable_drive_kind
        checks["portable temp"] = str(TEMP_DIR)
    except Exception as exc:  # pragma: no cover - used by packaged smoke tests
        print(json.dumps({"status": "failed", "portable_home": str(APP_ROOT), "error": str(exc)}))
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "version": __version__,
                "portable_home": str(APP_ROOT),
                "modules": checks,
            },
            indent=2,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--version", action="store_true")
    return parser.parse_args()


def main() -> int:
    ensure_app_directories()
    cleanup_stale_temp_files()
    args = parse_args()
    if args.version:
        print(__version__)
        return 0
    if args.self_test:
        return run_self_test()

    from src.taglish_transcriber.ui import TaglishTranscriberApp

    app = TaglishTranscriberApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
