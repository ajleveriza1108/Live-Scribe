from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .audio import (
    ApplicationAudioCapture,
    AudioBlock,
    MicrophoneCapture,
    SpeechChunk,
    SpeechSegmenter,
    SystemAudioCapture,
    mix_conversation_wavs,
)
from .config import (
    AUDIO_SOURCE_APPLICATION,
    AUDIO_SOURCE_CONVERSATION,
    AUDIO_SOURCE_SYSTEM,
)
from .models import TranscriptSegment, TranscriptionError, WhisperEngine
from .noise_reduction import reduce_live_chunk_noise
from .resource_policy import resource_policy
from .smart_vad import SmartVoiceGate


@dataclass(frozen=True, slots=True)
class SessionEvent:
    kind: str
    payload: Any = None


class LiveTranscriptionSession:
    """One low-RAM live session.

    Normal sources use one capture/segmenter pipeline. Windows Call / Conversation
    Mode uses two independent capture/segmenter pipelines (selected application +
    microphone) feeding one transcription worker. Sharing one WhisperEngine keeps
    the dual-source feature from loading a second speech model into RAM.
    """

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
        application_audio_label: str = "",
        context_prompt: str | None = None,
        live_noise_reduction: bool = False,
        application_audio_enabled: bool = True,
        microphone_listen_enabled: bool = False,
        microphone_monitor_output_label: str = "System default output",
        smart_vad: bool = False,
        memory_saver: bool = True,
        conversation_caller_label: str = "Caller",
        conversation_me_label: str = "Me",
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
        self.application_audio_label = application_audio_label or audio_input_label
        self.context_prompt = context_prompt
        self.live_noise_reduction = bool(live_noise_reduction)
        self.application_audio_enabled = bool(application_audio_enabled)
        self.microphone_listen_enabled = bool(microphone_listen_enabled)
        self.microphone_monitor_output_label = microphone_monitor_output_label
        self.smart_vad = bool(smart_vad)
        self.memory_saver = bool(memory_saver)
        self.conversation_caller_label = (
            " ".join(conversation_caller_label.strip().split()) or "Caller"
        )
        self.conversation_me_label = (
            " ".join(conversation_me_label.strip().split()) or "Me"
        )
        self.policy = resource_policy(self.memory_saver)
        self.voice_gate = SmartVoiceGate(enabled=self.smart_vad)
        self._live_noise_warning_sent = False
        self._engine_lock = threading.Lock()

        self.events: queue.Queue[SessionEvent] = queue.Queue(
            maxsize=self.policy.event_queue_items
        )
        self._started = False
        self._stopping = False
        self._paused = False
        self._conversation = self.audio_source_mode == AUDIO_SOURCE_CONVERSATION
        self.source_recordings: dict[str, Path] = {}
        self.source_offsets: dict[str, float] = {}

        if self._conversation:
            self._build_conversation_pipeline()
        else:
            self._build_single_source_pipeline()

    @staticmethod
    def _sidecar_path(path: Path, suffix: str) -> Path:
        return path.with_name(f"{path.stem}_{suffix}{path.suffix}")

    def _new_audio_queue(self) -> queue.Queue[AudioBlock | None]:
        maxsize = self.policy.audio_queue_blocks
        if self._conversation:
            maxsize = max(24, maxsize // 2)
        return queue.Queue(maxsize=maxsize)

    def _new_chunk_queue(self) -> queue.Queue[SpeechChunk | None]:
        maxsize = self.policy.transcript_queue_items
        if self._conversation:
            maxsize = max(3, maxsize // 2)
        return queue.Queue(maxsize=maxsize)

    def _build_single_source_pipeline(self) -> None:
        self.audio_queue = self._new_audio_queue()
        self.chunk_queue = self._new_chunk_queue()

        if self.audio_source_mode == AUDIO_SOURCE_APPLICATION:
            self.capture = ApplicationAudioCapture(
                output_queue=self.audio_queue,
                target_label=self.application_audio_label,
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
        self.segmenters = [self.segmenter]
        self.transcriber_thread = threading.Thread(
            target=self._transcribe_loop,
            name="transcription-worker",
            daemon=True,
        )

    def _build_conversation_pipeline(self) -> None:
        self.caller_audio_queue = self._new_audio_queue()
        self.me_audio_queue = self._new_audio_queue()
        self.caller_chunk_queue = self._new_chunk_queue()
        self.me_chunk_queue = self._new_chunk_queue()

        caller_path = self._sidecar_path(self.recording_path, "Caller")
        me_path = self._sidecar_path(self.recording_path, "Me")
        self.source_recordings = {
            "caller": caller_path,
            "me": me_path,
        }
        self.source_offsets = {"caller": 0.0, "me": 0.0}

        self.application_capture = ApplicationAudioCapture(
            output_queue=self.caller_audio_queue,
            target_label=self.application_audio_label,
            recording_path=caller_path,
            enabled=self.application_audio_enabled,
            event_callback=(
                lambda kind, payload: self._on_conversation_audio_event(
                    "caller",
                    self.conversation_caller_label,
                    kind,
                    payload,
                )
            ),
        )
        self.microphone_capture = MicrophoneCapture(
            output_queue=self.me_audio_queue,
            microphone_index=self.microphone_index,
            recording_path=me_path,
            event_callback=(
                lambda kind, payload: self._on_conversation_audio_event(
                    "me",
                    self.conversation_me_label,
                    kind,
                    payload,
                )
            ),
            monitor_enabled=self.microphone_listen_enabled,
            monitor_output_label=self.microphone_monitor_output_label,
        )
        # Compatibility: callers that expect .capture still get an object with
        # the selected-app identity while conversation-specific methods use the
        # explicit capture attributes above.
        self.capture = self.application_capture

        self.caller_segmenter = SpeechSegmenter(
            input_queue=self.caller_audio_queue,
            output_queue=self.caller_chunk_queue,
            rms_threshold=self.rms_threshold,
            end_silence_seconds=self.policy.end_silence_seconds,
            max_chunk_seconds=self.policy.max_phrase_seconds,
        )
        self.me_segmenter = SpeechSegmenter(
            input_queue=self.me_audio_queue,
            output_queue=self.me_chunk_queue,
            rms_threshold=self.rms_threshold,
            end_silence_seconds=self.policy.end_silence_seconds,
            max_chunk_seconds=self.policy.max_phrase_seconds,
        )
        self.segmenters = [self.caller_segmenter, self.me_segmenter]
        self.transcriber_thread = threading.Thread(
            target=self._conversation_transcribe_loop,
            name="conversation-transcription-worker",
            daemon=True,
        )

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

    def _on_audio_event(self, level: str, message: Any) -> None:
        self._emit_event(level, message)

    def _on_conversation_audio_event(
        self,
        source: str,
        speaker: str,
        kind: str,
        payload: Any,
    ) -> None:
        if isinstance(payload, dict):
            tagged = dict(payload)
            tagged["source"] = source
            tagged["speaker"] = speaker
            payload = tagged
        elif kind in {"warning", "error", "status"}:
            payload = f"{speaker}: {payload}"
        self._emit_event(kind, payload, critical=kind == "error")

    def start(self) -> None:
        if self._started:
            return

        for segmenter in self.segmenters:
            segmenter.start()
        self.transcriber_thread.start()

        if self._conversation:
            started_app = False
            started_mic = False
            base_time = time.monotonic()
            try:
                self.source_offsets["caller"] = max(0.0, time.monotonic() - base_time)
                self.application_capture.start()
                started_app = True
                self.source_offsets["me"] = max(0.0, time.monotonic() - base_time)
                self.microphone_capture.start()
                started_mic = True
            except Exception:
                if started_mic:
                    try:
                        self.microphone_capture.stop()
                    except Exception:
                        pass
                else:
                    self._signal_queue_end(self.me_audio_queue)
                if started_app:
                    try:
                        self.application_capture.stop()
                    except Exception:
                        pass
                else:
                    self._signal_queue_end(self.caller_audio_queue)
                raise

            self._started = True
            self._emit_event(
                "listening",
                {
                    "audio_input": (
                        f"{self.conversation_caller_label}: "
                        f"{self.application_capture.selected_input_name} | "
                        f"{self.conversation_me_label}: "
                        f"{self.microphone_capture.selected_input_name}"
                    ),
                    "source_mode": self.audio_source_mode,
                    "recording_path": self.recording_path,
                    "source_recordings": dict(self.source_recordings),
                    "source_offsets": dict(self.source_offsets),
                },
                critical=True,
            )
            return

        try:
            self.capture.start()
        except Exception:
            self._signal_queue_end(self.audio_queue)
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

    @staticmethod
    def _signal_queue_end(target: queue.Queue[AudioBlock | None]) -> None:
        try:
            target.put_nowait(None)
        except queue.Full:
            try:
                target.get_nowait()
            except queue.Empty:
                pass
            try:
                target.put_nowait(None)
            except queue.Full:
                pass

    @property
    def is_paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        if not self._started or self._stopping or self._paused:
            return
        self._paused = True
        if self._conversation:
            self.application_capture.set_paused(True)
            self.microphone_capture.set_paused(True)
        else:
            self.capture.set_paused(True)
        self._emit_event("paused")

    def resume(self) -> None:
        if not self._started or self._stopping or not self._paused:
            return
        self._paused = False
        if self._conversation:
            self.application_capture.set_paused(False)
            self.microphone_capture.set_paused(False)
        else:
            self.capture.set_paused(False)
        self._emit_event("resumed")

    def set_application_audio_enabled(self, enabled: bool) -> None:
        capture = (
            self.application_capture
            if self._conversation
            else self.capture
        )
        if isinstance(capture, ApplicationAudioCapture):
            capture.set_enabled(enabled)
            self.application_audio_enabled = bool(enabled)

    def set_application_audio_target(self, label: str) -> None:
        capture = (
            self.application_capture
            if self._conversation
            else self.capture
        )
        if isinstance(capture, ApplicationAudioCapture):
            capture.set_target(label)
            self.application_audio_label = label
            if not self._conversation:
                self.audio_input_label = label

    def set_microphone_monitor_enabled(self, enabled: bool) -> bool:
        capture = (
            self.microphone_capture
            if self._conversation
            else self.capture
        )
        if not isinstance(capture, MicrophoneCapture):
            return False
        result = capture.set_monitor_enabled(enabled)
        self.microphone_listen_enabled = bool(enabled and result)
        return result

    def set_microphone_monitor_output(self, label: str) -> bool:
        capture = (
            self.microphone_capture
            if self._conversation
            else self.capture
        )
        if not isinstance(capture, MicrophoneCapture):
            return False
        result = capture.set_monitor_output(label)
        if result:
            self.microphone_monitor_output_label = label
        return result

    def stop(self) -> None:
        if not self._started or self._stopping:
            return
        self._stopping = True
        self._emit_event("stopping", critical=True)
        if self._conversation:
            # Stop both sources. Each capture closes its sidecar WAV before it
            # signals the corresponding segmenter end marker.
            try:
                self.application_capture.stop()
            finally:
                self.microphone_capture.stop()
        else:
            self.capture.stop()

    def _prepare_transcription_audio(self, chunk: SpeechChunk) -> tuple[Any, float] | None:
        gate = self.voice_gate.process(chunk.samples)
        if not gate.speech_detected or gate.samples.size == 0:
            return None

        effective_start = chunk.start + gate.start_offset_seconds
        transcription_audio = gate.samples
        if self.live_noise_reduction:
            try:
                transcription_audio = reduce_live_chunk_noise(gate.samples)
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
                transcription_audio = gate.samples
        return transcription_audio, effective_start

    def _transcribe_chunk(
        self,
        chunk: SpeechChunk,
        *,
        source: str = "",
        speaker: str = "",
        source_offset: float = 0.0,
    ) -> None:
        prepared = self._prepare_transcription_audio(chunk)
        if prepared is None:
            self._emit_event(
                "speech_skipped",
                {
                    "start": chunk.start + source_offset,
                    "end": chunk.end + source_offset,
                    "source": source,
                    "speaker": speaker,
                },
            )
            return

        transcription_audio, effective_start = prepared
        effective_start += source_offset
        self._emit_event(
            "processing",
            {
                "start": effective_start,
                "end": chunk.end + source_offset,
                "source": source,
                "speaker": speaker,
            },
        )

        try:
            # One worker/one model copy. The lock also protects callers that may
            # invoke the session's engine from another helper thread later.
            with self._engine_lock:
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
            return

        for segment in segments:
            if not isinstance(segment, TranscriptSegment):
                continue
            if speaker:
                segment = replace(segment, speaker=speaker)
            self._emit_event("segment", segment, critical=True)

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
            self._transcribe_chunk(chunk)

    def _conversation_transcribe_loop(self) -> None:
        sources = (
            (
                "caller",
                self.conversation_caller_label,
                self.caller_chunk_queue,
            ),
            (
                "me",
                self.conversation_me_label,
                self.me_chunk_queue,
            ),
        )
        finished: set[str] = set()

        while len(finished) < len(sources):
            processed = False
            for source, speaker, source_queue in sources:
                if source in finished:
                    continue
                try:
                    chunk = source_queue.get_nowait()
                except queue.Empty:
                    continue

                processed = True
                if chunk is None:
                    finished.add(source)
                    continue

                self._transcribe_chunk(
                    chunk,
                    source=source,
                    speaker=speaker,
                    source_offset=self.source_offsets.get(source, 0.0),
                )

            if not processed:
                time.sleep(0.02)

        try:
            mix_conversation_wavs(
                self.source_recordings.get("caller"),
                self.source_recordings.get("me"),
                self.recording_path,
                offsets=self.source_offsets,
            )
        except Exception as exc:
            self._emit_event(
                "warning",
                (
                    "The separate Caller and Me WAV files were saved, but the combined "
                    "conversation WAV could not be created. "
                    f"Details: {str(exc).strip() or 'WAV mixing error'}"
                ),
            )

        self._emit_event(
            "finished",
            {
                "recording_path": self.recording_path,
                "source_recordings": dict(self.source_recordings),
                "source_offsets": dict(self.source_offsets),
                "speaker_labels": {
                    "caller": self.conversation_caller_label,
                    "me": self.conversation_me_label,
                },
            },
            critical=True,
        )
