from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .config import MODEL_OPTIONS, model_friendly_name, model_size_label
from .models import is_model_downloaded, local_model_path
from .paths import CACHE_DIR, MODEL_DIR, RECORDING_DIR, TEMP_DIR


@dataclass(frozen=True, slots=True)
class StorageItem:
    key: str
    label: str
    size_bytes: int
    status: str


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        try:
            total += child.stat().st_size
        except OSError:
            continue
    return total


def format_size(value: int) -> str:
    size = float(max(0, value))
    units = ("B", "KB", "MB", "GB", "TB")
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    decimals = 0 if index == 0 else 1 if size >= 10 else 2
    return f"{size:.{decimals}f} {units[index]}"


def storage_items() -> list[StorageItem]:
    items: list[StorageItem] = []
    for model_name in MODEL_OPTIONS:
        folder = local_model_path(model_name)
        size = directory_size(folder)
        status = "Ready" if is_model_downloaded(model_name) else ("Partial" if size else "Not downloaded")
        items.append(
            StorageItem(
                key=f"model:{model_name}",
                label=f"{model_friendly_name(model_name)} ({model_size_label(model_name)})",
                size_bytes=size,
                status=status,
            )
        )

    partial_size = 0
    for child in MODEL_DIR.rglob("*"):
        if child.is_file() and (
            child.name.endswith(".incomplete")
            or child.name.endswith(".lock")
            or ".cache" in child.parts
        ):
            try:
                partial_size += child.stat().st_size
            except OSError:
                pass

    items.extend(
        [
            StorageItem("partial", "Partial model downloads", partial_size, "Resumable data"),
            StorageItem("temp", "Temporary files", directory_size(TEMP_DIR), "Safe to clean when idle"),
            StorageItem("cache", "Supporting cache", directory_size(CACHE_DIR), "Used by portable runtime"),
            StorageItem("recordings", "Recordings", directory_size(RECORDING_DIR), "User files"),
        ]
    )
    return items


def remove_model(model_name: str) -> int:
    folder = local_model_path(model_name)
    size = directory_size(folder)
    if folder.exists():
        shutil.rmtree(folder)
    return size


def clean_partial_downloads() -> int:
    removed = 0
    for model_name in MODEL_OPTIONS:
        folder = local_model_path(model_name)
        if is_model_downloaded(model_name):
            continue
        removed += directory_size(folder)
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
    return removed


def clean_temporary_files() -> int:
    removed = directory_size(TEMP_DIR)
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return removed


def clean_orphan_recording_parts(*, older_than_hours: int = 24) -> int:
    cutoff = time.time() - max(1, older_than_hours) * 3600
    removed = 0
    for folder in RECORDING_DIR.glob("*.parts"):
        try:
            if folder.stat().st_mtime >= cutoff:
                continue
        except OSError:
            continue
        removed += directory_size(folder)
        shutil.rmtree(folder, ignore_errors=True)
    return removed
