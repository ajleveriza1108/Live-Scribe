from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_productivity_features_imports_microphone_audio_source_constant() -> None:
    source_path = ROOT / "src/taglish_transcriber/productivity_features.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "config":
            imported.update(alias.name for alias in node.names)
    assert "AUDIO_SOURCE_MICROPHONE" in imported


def test_windows_launcher_persists_startup_crash_log() -> None:
    source = (ROOT / "launchers/start_windows.bat").read_text(encoding="utf-8")
    assert 'set "STARTUP_LOG=%LOG_DIR%\\startup.log"' in source
    assert '-X faulthandler "%SOURCE_APP%"' in source
    assert '>>"%STARTUP_LOG%" 2>&1' in source
    assert "Last log lines:" in source
