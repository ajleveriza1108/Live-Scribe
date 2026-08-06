from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audio import (
    ApplicationAudioCapture,
    AudioBlock,
    MicrophoneCapture,
    SpeechChunk,
    SpeechSegmenter,
    SystemAudioCapture,
)
from .config import AUDIO_SOURCE_APPLICATION, AUDIO_SOURCE_SYSTEM
from .models import TranscriptSegment, TranscriptionError, WhisperEngine
from .noise_reduction import reduce_live_chunk_noise
from .resource_policy import resource_policy
from .smart_vad import SmartVoiceGate


@dataclass(frozen=True, slots=True)
class SessionEvent:
    kind: str
    payload: Any = None


class LiveTranscriptionSession:
    def __init__(
        self,
        engine: WhisperEngine,
        microphone_index: int | None,
        language_code: str | None,
        language_label: str,
        rms_threshold: float,
        recording_path: Path,
        hotwords: str | None = None,
        audio_source_mode: str = "Microphone",
        audio_input_label: str = "Default input",
        context_prompt: str | None = None,
        live_noise_reduction: bool = False,
        application_audio_enabled: bool = True,
        microphone_listen_enabled: bool = False,
        microphone_monitor_output_label: str = "System default output",
        smart_vad: bool = False,
        memory_saver: bool = True,
    ) -> None:
        self.engine = engine
        self.microphone_index = microphone_index
        self.language_code = language_code
        self.language_label = language_label
        self.rms_threshold = rms_threshold
        self.recording_path = recording_path
        self.hotwords = hotwords
        self.audio_source_mode = audio_source_mode
        self.audio_input_label = audio_input_label
        self.context_prompt = context_prompt
        self.live_noise_reduction = bool(live_noise_reduction)
        self.application_audio_enabled = bool(application_audio_enabled)
        self.microphone_listen_enabled = bool(microphone_listen_enabled)
        self.microphone_monitor_output_label = microphone_monitor_output_label
        self.smart_vad = bool(smart_vad)
        self.memory_saver = bool(memory_saver)
        self.policy = resource_policy(self.memory_saver)
        self.voice_gate = SmartVoiceGate(enabled=self.smart_vad)
        self._live_noise_warning_sent = False

        self.audio_queue: queue.Queue[AudioBlock | None] = queue.Queue(
            maxsize=self.policy.audio_queue_blocks
        )
        self.chunk_queue: queue.Queue[SpeechChunk | None] = queue.Queue(
            maxsize=self.policy.transcript_queue_items
        )
        self.events: queue.Queue[SessionEvent] = queue.Queue(
            maxsize=self.policy.event_queue_items
        )

        if self.audio_source_mode == AUDIO_SOURCE_APPLICATION:
            self.capture = ApplicationAudioCapture(
                output_queue=self.audio_queue,
                target_label=self.audio_input_label,
                recording_path=self.recording_path,
                enabled=self.application_audio_enabled,
                event_callback=self._on_audio_event,
            )
        elif self.audio_source_mode == AUDIO_SOURCE_SYSTEM:
            self.capture = SystemAudioCapture(
                output_queue=self.audio_queue,
                source_label=self.audio_input_label,
                recording_path=self.recording_path,
                event_callback=self._on_audio_event,
            )
        else:
            self.capture = MicrophoneCapture(
                output_queue=self.audio_queue,
                microphone_index=self.microphone_index,
                recording_path=self.recording_path,
                event_callback=self._on_audio_event,
                monitor_enabled=self.microphone_listen_enabled,
                monitor_output_label=self.microphone_monitor_output_label,
            )

        self.segmenter = SpeechSegmenter(
            input_queue=self.audio_queue,
            output_queue=self.chunk_queue,
            rms_threshold=self.rms_threshold,
            end_silence_seconds=self.policy.end_silence_seconds,
            max_chunk_seconds=self.policy.max_phrase_seconds,
        )
        self.transcriber_thread = threading.Thread(
            target=self._transcribe_loop,
            name="transcription-worker",
            daemon=True,
        )
        self._started = False
        self._stopping = False
        self._paused = False

    def _emit_event(
        self,
        kind: str,
        payload: Any = None,
        *,
        critical: bool = False,
    ) -> None:
        event = SessionEvent(kind=kind, payload=payload)
        try:
            self.events.put_nowait(event)
            return
        except queue.Full:
            if not critical:
                return
        try:
            self.events.get_nowait()
        except queue.Empty:
            pass
        try:
            self.events.put_nowait(event)
        except queue.Full:
            pass

    def _on_audio_event(self, level: str, message: str) -> None:
        self._emit_event(level, message)

    def start(self) -> None:
        if self._started:
            return

        self.segmenter.start()
        self.transcriber_thread.start()

        try:
            self.capture.start()
        except Exception:
            self.audio_queue.put(None)
            raise

        self._started = True
        self._emit_event(
            "listening",
            {
                    "audio_input": self.capture.selected_input_name,
                    "source_mode": self.audio_source_mode,
                    "recording_path": self.recording_path,
                },
            critical=True,
        )

    @property
    def is_paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        if not self._started or self._stopping or self._paused:
            return
        self._paused = True
        self.capture.set_paused(True)
        self._emit_event("paused")

    def resume(self) -> None:
        if not self._started or self._stopping or not self._paused:
            return
        self._paused = False
        self.capture.set_paused(False)
        self._emit_event("resumed")

    def set_application_audio_enabled(self, enabled: bool) -> None:
        if isinstance(self.capture, ApplicationAudioCapture):
            self.capture.set_enabled(enabled)

    def set_application_audio_target(self, label: str) -> None:
        if isinstance(self.capture, ApplicationAudioCapture):
            self.capture.set_target(label)
            self.audio_input_label = label

    def set_microphone_monitor_enabled(self, enabled: bool) -> bool:
        if not isinstance(self.capture, MicrophoneCapture):
            return False
        result = self.capture.set_monitor_enabled(enabled)
        self.microphone_listen_enabled = bool(enabled and result)
        return result

    def set_microphone_monitor_output(self, label: str) -> bool:
        if not isinstance(self.capture, MicrophoneCapture):
            return False
        result = self.capture.set_monitor_output(label)
        if result:
            self.microphone_monitor_output_label = label
        return result

    def stop(self) -> None:
        if not self._started or self._stopping:
            return
        self._stopping = True
        self._emit_event("stopping", critical=True)
        self.capture.stop()

    def _transcribe_loop(self) -> None:
        while True:
            chunk = self.chunk_queue.get()
            if chunk is None:
                self._emit_event(
                    "finished",
                    {"recording_path": self.recording_path},
                    critical=True,
                )
                return

            gate = self.voice_gate.process(chunk.samples)
            if not gate.speech_detected or gate.samples.size == 0:
                self._emit_event(
                    "speech_skipped",
                    {
                        "start": chunk.start,
                        "end": chunk.end,
                        "backend": gate.backend,
                    },
                )
                continue

            effective_start = chunk.start + gate.start_offset_seconds
            self._emit_event(
                "processing",
                {
                    "start": effective_start,
                    "end": chunk.end,
                    "vad": gate.backend,
                },
            )

            transcription_audio = gate.samples
            if self.live_noise_reduction:
                try:
                    transcription_audio = reduce_live_chunk_noise(chunk.samples)
                except Exception as exc:
                    if not self._live_noise_warning_sent:
                        self._live_noise_warning_sent = True
                        self._emit_event(
                            "warning",
                            (
                                    "Live noise reduction could not process one phrase, "
                                    "so Live Scribe continued with the original audio. "
                                    f"Details: {str(exc).strip() or 'audio processing error'}"
                                ),
                        )
                    transcription_audio = chunk.samples

            try:
                segments = self.engine.transcribe(
                    audio=transcription_audio,
                    chunk_start=effective_start,
                    language_code=self.language_code,
                    hotwords=self.hotwords,
                    language_label=self.language_label,
                    context_prompt=self.context_prompt,
                )
            except TranscriptionError as exc:
                self._emit_event("error", str(exc), critical=True)
                continue

            for segment in segments:
                if isinstance(segment, TranscriptSegment):
                    self._emit_event("segment", segment, critical=True)
