from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audio import (
    AudioBlock,
    MicrophoneCapture,
    SpeechChunk,
    SpeechSegmenter,
    SystemAudioCapture,
)
from .config import AUDIO_SOURCE_SYSTEM
from .models import TranscriptSegment, TranscriptionError, WhisperEngine


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
        rms_threshold: float,
        recording_path: Path,
        hotwords: str | None = None,
        audio_source_mode: str = "Microphone",
        audio_input_label: str = "Default input",
    ) -> None:
        self.engine = engine
        self.microphone_index = microphone_index
        self.language_code = language_code
        self.rms_threshold = rms_threshold
        self.recording_path = recording_path
        self.hotwords = hotwords
        self.audio_source_mode = audio_source_mode
        self.audio_input_label = audio_input_label

        self.audio_queue: queue.Queue[AudioBlock | None] = queue.Queue(maxsize=300)
        self.chunk_queue: queue.Queue[SpeechChunk | None] = queue.Queue(maxsize=30)
        self.events: queue.Queue[SessionEvent] = queue.Queue()

        if self.audio_source_mode == AUDIO_SOURCE_SYSTEM:
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
            )

        self.segmenter = SpeechSegmenter(
            input_queue=self.audio_queue,
            output_queue=self.chunk_queue,
            rms_threshold=self.rms_threshold,
        )
        self.transcriber_thread = threading.Thread(
            target=self._transcribe_loop,
            name="transcription-worker",
            daemon=True,
        )
        self._started = False
        self._stopping = False

    def _on_audio_event(self, level: str, message: str) -> None:
        self.events.put(SessionEvent(kind=level, payload=message))

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
        self.events.put(
            SessionEvent(
                kind="listening",
                payload={
                    "audio_input": self.capture.selected_input_name,
                    "source_mode": self.audio_source_mode,
                    "recording_path": self.recording_path,
                },
            )
        )

    def stop(self) -> None:
        if not self._started or self._stopping:
            return
        self._stopping = True
        self.events.put(SessionEvent(kind="stopping"))
        self.capture.stop()

    def _transcribe_loop(self) -> None:
        while True:
            chunk = self.chunk_queue.get()
            if chunk is None:
                self.events.put(
                    SessionEvent(
                        kind="finished",
                        payload={"recording_path": self.recording_path},
                    )
                )
                return

            self.events.put(
                SessionEvent(
                    kind="processing",
                    payload={"start": chunk.start, "end": chunk.end},
                )
            )

            try:
                segments = self.engine.transcribe(
                    audio=chunk.samples,
                    chunk_start=chunk.start,
                    language_code=self.language_code,
                    hotwords=self.hotwords,
                )
            except TranscriptionError as exc:
                self.events.put(SessionEvent(kind="error", payload=str(exc)))
                continue

            for segment in segments:
                if isinstance(segment, TranscriptSegment):
                    self.events.put(SessionEvent(kind="segment", payload=segment))
