from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .paths import ENGINES_DIR


WINDOWS_APP_AUDIO_HELPER = (
    ENGINES_DIR / "windows" / "LiveScribeApplicationLoopback.exe"
)
MINIMUM_PROCESS_LOOPBACK_BUILD = 20348


@dataclass(frozen=True, slots=True)
class ApplicationAudioTarget:
    pid: int
    process_name: str
    window_title: str

    @property
    def label(self) -> str:
        title = " ".join(self.window_title.split())
        process = self.process_name.removesuffix(".exe")
        visible = title or process
        return f"{visible} — {process}.exe — PID {self.pid}"


def parse_application_pid(label: str) -> int | None:
    match = re.search(r"\bPID\s+(\d+)\s*$", label)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def windows_build_number() -> int:
    if sys.platform != "win32":
        return 0
    try:
        return int(sys.getwindowsversion().build)
    except Exception:
        return 0


def application_audio_support() -> tuple[bool, str]:
    if sys.platform != "win32":
        return (
            False,
            "Selected-app audio currently requires the Windows process-loopback helper.",
        )
    build = windows_build_number()
    if build < MINIMUM_PROCESS_LOOPBACK_BUILD:
        return (
            False,
            "Selected-app audio requires Windows 10/11 build 20348 or newer.",
        )
    if not WINDOWS_APP_AUDIO_HELPER.is_file():
        return (
            False,
            "The Windows selected-app audio helper has not been built or installed yet.",
        )
    return True, "Windows selected-app audio is ready."


def list_running_application_targets() -> list[ApplicationAudioTarget]:
    """List normal visible Windows applications without adding psutil."""
    if sys.platform != "win32":
        return []

    command = (
        "Get-Process | "
        "Where-Object { $_.MainWindowTitle -and $_.Id -ne $PID } | "
        "Select-Object Id, ProcessName, MainWindowTitle | "
        "ConvertTo-Json -Compress"
    )
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=12,
            creationflags=creationflags,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0 or not completed.stdout.strip():
        return []

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []

    targets: list[ApplicationAudioTarget] = []
    seen: set[int] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            pid = int(item.get("Id", 0))
        except (TypeError, ValueError):
            continue
        if pid <= 0 or pid == os.getpid() or pid in seen:
            continue
        process_name = str(item.get("ProcessName", "")).strip()
        title = str(item.get("MainWindowTitle", "")).strip()
        if not process_name or not title:
            continue
        seen.add(pid)
        targets.append(
            ApplicationAudioTarget(
                pid=pid,
                process_name=process_name,
                window_title=title,
            )
        )
    targets.sort(key=lambda item: (item.process_name.casefold(), item.window_title.casefold()))
    return targets
