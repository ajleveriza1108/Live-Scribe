from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourcePolicy:
    memory_saver: bool
    audio_queue_blocks: int
    transcript_queue_items: int
    event_queue_items: int
    recorder_queue_blocks: int
    monitor_queue_blocks: int
    cpu_threads: int
    model_workers: int
    live_beam_size: int
    final_beam_size: int
    live_max_new_tokens: int
    end_silence_seconds: float
    max_phrase_seconds: float
    model_release_delay_ms: int


def resource_policy(memory_saver: bool = True) -> ResourcePolicy:
    logical = max(1, int(os.cpu_count() or 1))
    if memory_saver:
        cpu_threads = max(1, min(4, logical // 2 or 1))
        return ResourcePolicy(
            memory_saver=True,
            audio_queue_blocks=64,
            transcript_queue_items=6,
            event_queue_items=192,
            recorder_queue_blocks=120,
            monitor_queue_blocks=8,
            cpu_threads=cpu_threads,
            model_workers=1,
            live_beam_size=1,
            final_beam_size=3,
            live_max_new_tokens=128,
            end_silence_seconds=0.55,
            max_phrase_seconds=12.0,
            model_release_delay_ms=180_000,
        )

    return ResourcePolicy(
        memory_saver=False,
        audio_queue_blocks=160,
        transcript_queue_items=16,
        event_queue_items=384,
        recorder_queue_blocks=300,
        monitor_queue_blocks=16,
        cpu_threads=max(1, min(8, logical)),
        model_workers=1,
        live_beam_size=3,
        final_beam_size=5,
        live_max_new_tokens=192,
        end_silence_seconds=0.70,
        max_phrase_seconds=15.0,
        model_release_delay_ms=600_000,
    )
