from __future__ import annotations

import os
from pathlib import Path

from src.taglish_transcriber.paths import (
    APP_ROOT,
    CACHE_DIR,
    HF_HOME_DIR,
    TEMP_DIR,
    atomic_write_text,
)


def test_runtime_cache_environment_stays_under_portable_root() -> None:
    for name in (
        "HF_HOME",
        "HF_HUB_CACHE",
        "HF_XET_CACHE",
        "HF_ASSETS_CACHE",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "TMP",
        "TEMP",
        "TMPDIR",
    ):
        configured = Path(os.environ[name]).resolve()
        assert configured == APP_ROOT.resolve() or APP_ROOT.resolve() in configured.parents

    assert HF_HOME_DIR == CACHE_DIR / "huggingface"
    assert TEMP_DIR == CACHE_DIR / "temp"


def test_atomic_write_replaces_complete_file(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    atomic_write_text(target, '{"version": 1}\n')
    atomic_write_text(target, '{"version": 2}\n')
    assert target.read_text(encoding="utf-8") == '{"version": 2}\n'
    assert not target.with_suffix(".json.tmp").exists()
