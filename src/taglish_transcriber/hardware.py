from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .config import (
    MODEL_CATALOG,
    MODEL_OPTIONS,
    model_friendly_name,
    model_size_label,
)
from .paths import HARDWARE_PROFILE_FILE, MODEL_DIR, ensure_app_directories


STATUS_RECOMMENDED = "recommended"
STATUS_CAUTION = "caution"
STATUS_UNAVAILABLE = "unavailable"

MIB = 1024**2
GIB = 1024**3
HARDWARE_CHECK_VERSION = 1

MODEL_REQUIREMENTS = {
    "small": {
        "minimum_ram_gb": 4,
        "comfortable_ram_gb": 8,
        "comfortable_threads": 4,
    },
    "medium": {
        "minimum_ram_gb": 8,
        "comfortable_ram_gb": 12,
        "comfortable_threads": 6,
    },
    "large-v3-turbo": {
        "minimum_ram_gb": 8,
        "comfortable_ram_gb": 16,
        "comfortable_threads": 8,
    },
    "large-v3": {
        "minimum_ram_gb": 12,
        "comfortable_ram_gb": 24,
        "comfortable_threads": 8,
    },
}

SUPPORTED_ARCHITECTURES = {
    "amd64",
    "x86_64",
    "x64",
    "arm64",
    "aarch64",
}


@dataclass(frozen=True, slots=True)
class HardwareSnapshot:
    os_name: str
    architecture: str
    cpu_name: str
    cpu_threads: int | None
    total_ram_bytes: int | None
    free_disk_bytes: int | None
    cuda_device_count: int
    gpu_name: str | None = None
    gpu_vram_bytes: int | None = None
    notes: tuple[str, ...] = ()

    @property
    def has_cuda_gpu(self) -> bool:
        return self.cuda_device_count > 0

    def summary(self) -> str:
        parts: list[str] = []
        if self.total_ram_bytes:
            parts.append(f"{format_gib(self.total_ram_bytes)} RAM")
        else:
            parts.append("RAM could not be confirmed")

        if self.cpu_threads:
            label = "thread" if self.cpu_threads == 1 else "threads"
            parts.append(f"{self.cpu_threads} CPU {label}")
        else:
            parts.append("CPU thread count unknown")

        if self.gpu_name:
            gpu = self.gpu_name
            if self.gpu_vram_bytes:
                gpu += f" ({format_gib(self.gpu_vram_bytes)} VRAM)"
            parts.append(gpu)
        elif self.has_cuda_gpu:
            parts.append("Compatible NVIDIA GPU detected")
        else:
            parts.append("CPU processing")

        if self.free_disk_bytes is not None:
            parts.append(f"{format_gib(self.free_disk_bytes)} free")
        else:
            parts.append("free storage unknown")
        return "  •  ".join(parts)


@dataclass(frozen=True, slots=True)
class ModelCapability:
    model_name: str
    status: str
    download_allowed: bool
    headline: str
    detail: str
    reasons: tuple[str, ...]
    required_free_bytes: int

    @property
    def status_symbol(self) -> str:
        return {
            STATUS_RECOMMENDED: "✓",
            STATUS_CAUTION: "!",
            STATUS_UNAVAILABLE: "×",
        }.get(self.status, "•")


@dataclass(frozen=True, slots=True)
class HardwareAssessment:
    snapshot: HardwareSnapshot
    capabilities: Mapping[str, ModelCapability]
    recommended_model: str
    checked_at: str
    check_version: int = HARDWARE_CHECK_VERSION

    def capability(self, model_name: str) -> ModelCapability:
        return self.capabilities[model_name]

    def available_model_ids(self) -> tuple[str, ...]:
        return tuple(
            model_name
            for model_name in MODEL_OPTIONS
            if self.capabilities[model_name].download_allowed
        )

    def unavailable_model_ids(self) -> tuple[str, ...]:
        return tuple(
            model_name
            for model_name in MODEL_OPTIONS
            if not self.capabilities[model_name].download_allowed
        )

    def compatibility_text(self) -> str:
        lines: list[str] = []
        for model_name in MODEL_OPTIONS:
            capability = self.capabilities[model_name]
            lines.append(
                f"{capability.status_symbol} {model_friendly_name(model_name)} "
                f"({model_size_label(model_name)}) — {capability.headline}"
            )
            if capability.detail:
                lines.append(f"   {capability.detail}")
        return "\n".join(lines)

    def buyer_notice(self) -> str:
        recommendation = model_friendly_name(self.recommended_model)
        lines = [
            "Live Scribe checked this computer before offering model downloads.",
            "",
            self.snapshot.summary(),
            "",
            f"Recommended for this computer: {recommendation}.",
        ]
        cautions = [
            model_friendly_name(model_name)
            for model_name, capability in self.capabilities.items()
            if capability.status == STATUS_CAUTION
        ]
        unavailable = [
            model_friendly_name(model_name)
            for model_name, capability in self.capabilities.items()
            if capability.status == STATUS_UNAVAILABLE
        ]
        if cautions:
            lines.extend(
                [
                    "",
                    "Use with caution: " + ", ".join(cautions) + ".",
                    "These options may work, but Live Scribe cannot confidently predict "
                    "their speed or stability on this computer.",
                ]
            )
        if unavailable:
            lines.extend(
                [
                    "",
                    "Unavailable for download: " + ", ".join(unavailable) + ".",
                    "They are hidden from the download selector because the detected RAM "
                    "or available storage is below Live Scribe's conservative minimum.",
                ]
            )
        lines.extend(
            [
                "",
                "This is a conservative estimate, not a performance guarantee. "
                "Close memory-heavy programs during long transcription sessions.",
            ]
        )
        return "\n".join(lines)


def format_gib(value: int | None) -> str:
    if value is None:
        return "unknown"
    amount = value / GIB
    if amount >= 100:
        return f"{amount:.0f} GB"
    return f"{amount:.1f} GB"


def _total_ram_windows() -> int | None:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    try:
        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
    except Exception:
        return None
    return None


def _total_ram_posix() -> int | None:
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        page_count = int(os.sysconf("SC_PHYS_PAGES"))
        value = page_size * page_count
        return value if value > 0 else None
    except (AttributeError, OSError, ValueError):
        pass

    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            value = int(result.stdout.strip())
            return value if value > 0 else None
        except Exception:
            return None
    return None


def _detect_total_ram() -> int | None:
    if sys.platform == "win32":
        return _total_ram_windows()
    return _total_ram_posix()


def _cpu_name() -> str:
    candidates = (
        platform.processor(),
        os.environ.get("PROCESSOR_IDENTIFIER", ""),
        platform.uname().processor,
        platform.uname().machine,
    )
    for candidate in candidates:
        value = " ".join(str(candidate).strip().split())
        if value:
            return value
    return "CPU details unavailable"


def _nvidia_smi_details() -> tuple[str | None, int | None, tuple[str, ...]]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None, None, ()

    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            [
                executable,
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
            creationflags=creationflags,
        )
    except Exception as exc:
        return None, None, (f"NVIDIA details could not be read: {exc}",)

    if result.returncode != 0 or not result.stdout.strip():
        return None, None, ()

    first_line = result.stdout.strip().splitlines()[0]
    parts = [part.strip() for part in first_line.split(",", 1)]
    name = parts[0] if parts else None
    vram = None
    if len(parts) > 1:
        try:
            vram = int(float(parts[1])) * MIB
        except ValueError:
            vram = None
    return name, vram, ()


def _cuda_device_count() -> tuple[int, tuple[str, ...]]:
    try:
        import ctranslate2

        return max(0, int(ctranslate2.get_cuda_device_count())), ()
    except Exception as exc:
        return 0, (f"GPU compatibility check was inconclusive: {exc}",)


def detect_hardware() -> HardwareSnapshot:
    ensure_app_directories()
    notes: list[str] = []

    try:
        free_disk = int(shutil.disk_usage(MODEL_DIR).free)
    except OSError as exc:
        free_disk = None
        notes.append(f"Available storage could not be measured: {exc}")

    cuda_count, cuda_notes = _cuda_device_count()
    notes.extend(cuda_notes)
    gpu_name, gpu_vram, gpu_notes = _nvidia_smi_details()
    notes.extend(gpu_notes)

    if gpu_name and cuda_count <= 0:
        notes.append(
            "An NVIDIA GPU was found, but CTranslate2 could not confirm CUDA access. "
            "Live Scribe will use the CPU unless the NVIDIA runtime is configured."
        )

    return HardwareSnapshot(
        os_name=f"{platform.system()} {platform.release()}".strip(),
        architecture=platform.machine().strip() or "unknown",
        cpu_name=_cpu_name(),
        cpu_threads=os.cpu_count(),
        total_ram_bytes=_detect_total_ram(),
        free_disk_bytes=free_disk,
        cuda_device_count=cuda_count,
        gpu_name=gpu_name,
        gpu_vram_bytes=gpu_vram,
        notes=tuple(notes),
    )


def _folder_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        try:
            if child.name.endswith(".lock"):
                continue
            total += child.stat().st_size
        except OSError:
            continue
    return total


def local_model_bytes() -> dict[str, int]:
    return {
        model_name: _folder_bytes(MODEL_DIR / model_name)
        for model_name in MODEL_OPTIONS
    }


def downloaded_models() -> set[str]:
    required = ("config.json", "model.bin", "tokenizer.json")
    return {
        model_name
        for model_name in MODEL_OPTIONS
        if all((MODEL_DIR / model_name / filename).is_file() for filename in required)
    }


def evaluate_hardware(
    snapshot: HardwareSnapshot,
    *,
    existing_model_bytes: Mapping[str, int] | None = None,
    complete_models: set[str] | None = None,
) -> HardwareAssessment:
    existing_model_bytes = dict(existing_model_bytes or {})
    complete_models = set(complete_models or set())
    capabilities: dict[str, ModelCapability] = {}

    architecture = snapshot.architecture.casefold()
    architecture_supported = architecture in SUPPORTED_ARCHITECTURES
    total_ram_gb = (
        snapshot.total_ram_bytes / GIB
        if snapshot.total_ram_bytes is not None
        else None
    )

    for model_name in MODEL_OPTIONS:
        requirements = MODEL_REQUIREMENTS[model_name]
        model_bytes = int(MODEL_CATALOG[model_name]["bytes"])
        existing_bytes = min(model_bytes, max(0, int(existing_model_bytes.get(model_name, 0))))
        remaining_bytes = 0 if model_name in complete_models else max(0, model_bytes - existing_bytes)
        hard_reserve = 384 * MIB
        comfortable_reserve = 1536 * MIB
        required_free = remaining_bytes + hard_reserve

        hard_reasons: list[str] = []
        caution_reasons: list[str] = []

        if not architecture_supported:
            hard_reasons.append(
                f"the detected {snapshot.architecture or 'unknown'} processor architecture "
                "is not supported by this portable build"
            )

        minimum_ram = float(requirements["minimum_ram_gb"])
        comfortable_ram = float(requirements["comfortable_ram_gb"])
        if total_ram_gb is None:
            caution_reasons.append("total RAM could not be confirmed")
        elif total_ram_gb + 0.1 < minimum_ram:
            hard_reasons.append(
                f"at least {minimum_ram:.0f} GB RAM is required by Live Scribe's "
                f"conservative safety limit; {total_ram_gb:.1f} GB was detected"
            )
        elif total_ram_gb + 0.1 < comfortable_ram:
            caution_reasons.append(
                f"{comfortable_ram:.0f} GB RAM is preferred; "
                f"{total_ram_gb:.1f} GB was detected"
            )

        if model_name not in complete_models:
            if snapshot.free_disk_bytes is None:
                caution_reasons.append("available storage could not be confirmed")
            elif snapshot.free_disk_bytes < required_free:
                hard_reasons.append(
                    f"the download needs approximately {format_gib(required_free)} free "
                    f"including a safety reserve; {format_gib(snapshot.free_disk_bytes)} is available"
                )
            elif snapshot.free_disk_bytes < remaining_bytes + comfortable_reserve:
                caution_reasons.append(
                    "free storage is close to the minimum required for the download"
                )

        comfortable_threads = int(requirements["comfortable_threads"])
        if snapshot.cpu_threads is None:
            caution_reasons.append("CPU thread count could not be confirmed")
        elif snapshot.cpu_threads < comfortable_threads:
            caution_reasons.append(
                f"{comfortable_threads} CPU threads are preferred; "
                f"{snapshot.cpu_threads} were detected"
            )

        if model_name == "large-v3":
            if not snapshot.has_cuda_gpu:
                caution_reasons.append(
                    "no compatible NVIDIA GPU was confirmed; CPU processing may be very slow"
                )
            elif snapshot.gpu_vram_bytes is None:
                caution_reasons.append(
                    "NVIDIA GPU memory could not be confirmed"
                )
            elif snapshot.gpu_vram_bytes < 4 * GIB:
                caution_reasons.append(
                    f"only {format_gib(snapshot.gpu_vram_bytes)} GPU memory was detected"
                )

        if model_name == "large-v3-turbo" and not snapshot.has_cuda_gpu:
            if total_ram_gb is None or total_ram_gb < 16:
                caution_reasons.append(
                    "GPU acceleration was not confirmed, so live processing speed is uncertain"
                )

        if hard_reasons:
            status = STATUS_UNAVAILABLE
            download_allowed = False
            headline = "Unavailable on this PC"
            prefix = (
                "This model is already stored locally, but it is disabled on this PC. "
                if model_name in complete_models
                else ""
            )
            detail = prefix + " ".join(
                reason[0].upper() + reason[1:] + "."
                for reason in hard_reasons
            )
            if caution_reasons:
                detail += " " + " ".join(
                    reason[0].upper() + reason[1:] + "."
                    for reason in caution_reasons
                )
            reasons = tuple(hard_reasons + caution_reasons)
        elif caution_reasons:
            status = STATUS_CAUTION
            download_allowed = True
            headline = "May run slowly — check the note"
            detail = " ".join(reason[0].upper() + reason[1:] + "." for reason in caution_reasons)
            reasons = tuple(caution_reasons)
        else:
            status = STATUS_RECOMMENDED
            download_allowed = True
            headline = "Recommended for this PC"
            detail = (
                "The detected RAM, CPU thread count, and storage meet Live Scribe's "
                "conservative guidance."
            )
            reasons = ()

        capabilities[model_name] = ModelCapability(
            model_name=model_name,
            status=status,
            download_allowed=download_allowed,
            headline=headline,
            detail=detail,
            reasons=reasons,
            required_free_bytes=required_free,
        )

    preferred_order = ("large-v3-turbo", "medium", "small")
    recommended_model = next(
        (
            model_name
            for model_name in preferred_order
            if capabilities[model_name].status == STATUS_RECOMMENDED
        ),
        "",
    )
    if not recommended_model:
        recommended_model = next(
            (
                model_name
                for model_name in preferred_order
                if capabilities[model_name].download_allowed
            ),
            "small",
        )

    return HardwareAssessment(
        snapshot=snapshot,
        capabilities=capabilities,
        recommended_model=recommended_model,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


def assess_this_pc() -> HardwareAssessment:
    return evaluate_hardware(
        detect_hardware(),
        existing_model_bytes=local_model_bytes(),
        complete_models=downloaded_models(),
    )


def save_hardware_assessment(
    assessment: HardwareAssessment,
    path: Path = HARDWARE_PROFILE_FILE,
) -> None:
    ensure_app_directories()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "check_version": assessment.check_version,
        "checked_at": assessment.checked_at,
        "recommended_model": assessment.recommended_model,
        "snapshot": asdict(assessment.snapshot),
        "capabilities": {
            model_name: asdict(capability)
            for model_name, capability in assessment.capabilities.items()
        },
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
