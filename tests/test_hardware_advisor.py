from __future__ import annotations

from src.taglish_transcriber.hardware import (
    GIB,
    STATUS_CAUTION,
    STATUS_RECOMMENDED,
    STATUS_UNAVAILABLE,
    HardwareSnapshot,
    evaluate_hardware,
)


def snapshot(
    *,
    ram_gb: float | None,
    threads: int | None,
    free_gb: float | None,
    cuda: int = 0,
    vram_gb: float | None = None,
) -> HardwareSnapshot:
    return HardwareSnapshot(
        os_name="Test OS",
        architecture="AMD64",
        cpu_name="Test CPU",
        cpu_threads=threads,
        total_ram_bytes=None if ram_gb is None else int(ram_gb * GIB),
        free_disk_bytes=None if free_gb is None else int(free_gb * GIB),
        cuda_device_count=cuda,
        gpu_name="Test NVIDIA GPU" if cuda else None,
        gpu_vram_bytes=None if vram_gb is None else int(vram_gb * GIB),
    )


def test_low_ram_disables_models_that_clearly_exceed_limit() -> None:
    assessment = evaluate_hardware(snapshot(ram_gb=4, threads=4, free_gb=20))
    assert assessment.capability("small").download_allowed
    assert assessment.capability("medium").status == STATUS_UNAVAILABLE
    assert assessment.capability("large-v3-turbo").status == STATUS_UNAVAILABLE
    assert assessment.capability("large-v3").status == STATUS_UNAVAILABLE


def test_capable_cpu_keeps_largest_model_available_with_caution() -> None:
    assessment = evaluate_hardware(snapshot(ram_gb=24, threads=12, free_gb=50))
    assert assessment.capability("large-v3-turbo").status == STATUS_RECOMMENDED
    assert assessment.capability("large-v3").status == STATUS_CAUTION
    assert assessment.capability("large-v3").download_allowed


def test_capable_nvidia_system_recommends_all_models() -> None:
    assessment = evaluate_hardware(
        snapshot(ram_gb=32, threads=16, free_gb=80, cuda=1, vram_gb=8)
    )
    assert all(
        assessment.capability(model_name).status == STATUS_RECOMMENDED
        for model_name in assessment.capabilities
    )
    assert assessment.recommended_model == "large-v3-turbo"


def test_insufficient_storage_disables_only_unfinished_downloads() -> None:
    low_disk = snapshot(ram_gb=32, threads=16, free_gb=0.2, cuda=1, vram_gb=8)
    assessment = evaluate_hardware(low_disk)
    assert all(
        capability.status == STATUS_UNAVAILABLE
        for capability in assessment.capabilities.values()
    )

    assessment_with_complete = evaluate_hardware(
        low_disk,
        complete_models={"large-v3"},
    )
    assert assessment_with_complete.capability("large-v3").download_allowed


def test_downloaded_model_does_not_bypass_clear_ram_failure() -> None:
    assessment = evaluate_hardware(
        snapshot(ram_gb=4, threads=8, free_gb=50),
        complete_models={"large-v3"},
    )
    capability = assessment.capability("large-v3")
    assert capability.status == STATUS_UNAVAILABLE
    assert not capability.download_allowed
    assert "already stored locally" in capability.detail


def test_slow_portable_drive_warns_without_hard_blocking() -> None:
    base = snapshot(ram_gb=32, threads=16, free_gb=80, cuda=1, vram_gb=8)
    slow = HardwareSnapshot(
        os_name=base.os_name,
        architecture=base.architecture,
        cpu_name=base.cpu_name,
        cpu_threads=base.cpu_threads,
        total_ram_bytes=base.total_ram_bytes,
        free_disk_bytes=base.free_disk_bytes,
        cuda_device_count=base.cuda_device_count,
        gpu_name=base.gpu_name,
        gpu_vram_bytes=base.gpu_vram_bytes,
        portable_drive_kind="Removable drive",
        portable_likely_removable=True,
        portable_write_mbps=5.0,
        portable_storage_status="slow",
        portable_storage_note="Slow portable storage.",
    )
    assessment = evaluate_hardware(slow)
    assert assessment.capability("small").download_allowed
    assert assessment.capability("large-v3").download_allowed
    assert assessment.capability("large-v3").status == STATUS_CAUTION
    assert assessment.recommended_model == "small"
