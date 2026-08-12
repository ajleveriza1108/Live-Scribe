from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from scripts.repository_preflight import run_preflight

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_PATHS = (
    "data/hardware_profile.json",
    "data/.first-run-complete",
    "data/unfinished_session.json",
    "data/interview_profiles.json",
    "data/sessions.sqlite3",
)


def test_repository_preflight_passes_clean_source() -> None:
    shutil.rmtree(ROOT / "recordings/In Progress/session", ignore_errors=True)
    shutil.rmtree(ROOT / "recordings/In Progress/recover", ignore_errors=True)
    errors, report = run_preflight()
    assert errors == []
    assert report["status"] == "ok"
    assert report["versions"]["package"] == "0.9.2"


def test_runtime_files_are_ignored_and_not_tracked() -> None:
    lines = set((ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
    assert set(RUNTIME_PATHS).issubset(lines)

    # A real installed copy may recreate runtime state such as the hardware
    # profile and first-run marker. Privacy depends on those files staying out
    # of the Git index, not on deleting useful local state.
    if (ROOT / ".git").is_dir():
        result = subprocess.run(
            ["git", "ls-files", "--", *RUNTIME_PATHS],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""


def test_source_ci_runs_preflight_and_tests() -> None:
    source = (ROOT / ".github/workflows/test-source.yml").read_text(
        encoding="utf-8"
    )
    assert "python scripts/repository_preflight.py" in source
    assert "python -m pytest -q" in source
    assert "windows-2022" in source
    assert "ubuntu-22.04" in source
    assert "macos-15" in source
