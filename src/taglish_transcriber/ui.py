from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .audio import detect_default_microphone_label, list_microphones, parse_microphone_index
from .config import (
    AppSettings,
    LANGUAGE_LABEL_TO_CODE,
    MODEL_OPTIONS,
    MODEL_PLACEHOLDER,
    MODEL_SELECTION_OPTIONS,
    SENSITIVITY_THRESHOLDS,
)
from .dictionary_engine import VocabularyManager
from .models import (
    ModelLoadError,
    TranscriptSegment,
    WhisperEngine,
    download_model_once,
    is_model_downloaded,
    model_status,
)
from .paths import EXPORT_DIR, RECORDING_DIR, ensure_app_directories, new_recording_path
from .postprocess import PostSessionProcessor, PostSessionResult
from .session import LiveTranscriptionSession, SessionEvent
from .skill_library import SkillLibrary
from .transcript import TranscriptDocument, TranscriptEntry, format_clock
from .vocabulary_dialog import VocabularyPronunciationDialog


class TaglishTranscriberApp:
    POLL_INTERVAL_MS = 100

    def __init__(self) -> None:
        ensure_app_directories()
        self.root = tk.Tk()
        self.root.title("Live Scribe")
        self.root.geometry("1220x790")
        self.root.minsize(980, 650)

        self.settings = AppSettings.load()
        self.document = TranscriptDocument()
        self.engine: WhisperEngine | None = None
        self.session: LiveTranscriptionSession | None = None
        self.model_loading = False
        self.model_downloading = False
        self.finalizing = False
        self.last_error_message = ""
        self.selected_microphone_name = self.settings.microphone_label

        self.model_var = tk.StringVar(value=self.settings.model_name or MODEL_PLACEHOLDER)
        self.language_var = tk.StringVar(value=self.settings.language_label)
        self.microphone_var = tk.StringVar(value=self.settings.microphone_label)
        self.device_var = tk.StringVar(value=self.settings.device_mode)
        self.sensitivity_var = tk.StringVar(value=self.settings.sensitivity_label)
        self.timestamps_var = tk.BooleanVar(value=self.settings.include_timestamps)
        self.final_pass_var = tk.BooleanVar(value=self.settings.final_accuracy_pass)
        self.noise_reduction_var = tk.BooleanVar(value=self.settings.noise_reduction)
        self.review_var = tk.BooleanVar(value=self.settings.grammar_diction_comments)
        self.live_appendix_var = tk.BooleanVar(value=self.settings.include_live_appendix)
        self.status_var = tk.StringVar(value="Ready.")
        self.activity_var = tk.StringVar(value="Select and download a speech model inside the app before the first session.")
        self.model_status_var = tk.StringVar(value=model_status(self.settings.model_name))
        self.recording_var = tk.StringVar(value="WAV recording: not started")

        self._configure_style()
        self._build_ui()
        self._refresh_microphones(auto_select=True)
        self._update_model_status()
        self._set_controls_for_idle()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(self.POLL_INTERVAL_MS, self._poll_session_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        available = style.theme_names()
        for candidate in ("vista", "aqua", "clam", "alt"):
            if candidate in available:
                style.theme_use(candidate)
                break
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 9))
        style.configure("ModelStatus.TLabel", font=("Segoe UI", 9, "italic"))

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(6, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Live Scribe", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="English, Tagalog, and Taglish dictation with WAV recording and post-session accuracy review.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        notice_frame = ttk.LabelFrame(container, text="Important accuracy notice", padding=9)
        notice_frame.grid(row=1, column=0, sticky="ew", pady=(0, 9))
        notice_frame.columnconfigure(0, weight=1)
        ttk.Label(
            notice_frame,
            text=(
                "AI-assisted transcription can make mistakes, especially with names, numbers, accents, "
                "uncommon words, and noisy audio. Always review the final transcript and replay the saved WAV "
                "before relying on important information."
            ),
            wraplength=1120,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            notice_frame,
            text=(
                "This edition is optimized for English, Tagalog/Filipino, and Taglish. "
                "Additional languages are planned for future versions."
            ),
            wraplength=1120,
            foreground="#555555",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        settings_frame = ttk.LabelFrame(container, text="Listening settings", padding=12, style="Section.TLabelframe")
        settings_frame.grid(row=2, column=0, sticky="ew")
        for column in range(5):
            settings_frame.columnconfigure(column, weight=1)

        mic_holder = ttk.Frame(settings_frame)
        mic_holder.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        mic_holder.columnconfigure(0, weight=1)
        ttk.Label(mic_holder, text="Microphone").grid(row=0, column=0, sticky="w")
        self.microphone_combo = ttk.Combobox(
            mic_holder, textvariable=self.microphone_var, values=("Default input",), state="readonly", width=30
        )
        self.microphone_combo.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(mic_holder, text="Detect", command=lambda: self._refresh_microphones(auto_select=True)).grid(
            row=1, column=1, padx=(5, 0), pady=(4, 0)
        )

        self.language_combo = self._label_and_combo(
            settings_frame, 1, "Language", self.language_var, tuple(LANGUAGE_LABEL_TO_CODE), 25
        )
        self.model_combo = self._label_and_combo(
            settings_frame, 2, "Speech model", self.model_var, MODEL_SELECTION_OPTIONS, 18
        )
        self.device_combo = self._label_and_combo(
            settings_frame, 3, "Processor", self.device_var, ("Auto", "CPU", "NVIDIA GPU"), 16
        )
        self.sensitivity_combo = self._label_and_combo(
            settings_frame, 4, "Mic sensitivity", self.sensitivity_var, tuple(SENSITIVITY_THRESHOLDS), 20
        )
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        options_frame = ttk.LabelFrame(container, text="After the speaker stops", padding=10)
        options_frame.grid(row=3, column=0, sticky="ew", pady=(9, 0))
        ttk.Label(options_frame, text="Original WAV recording is always saved.").grid(row=0, column=0, padx=(0, 16), sticky="w")
        ttk.Checkbutton(options_frame, text="Run final accuracy pass", variable=self.final_pass_var).grid(row=0, column=1, padx=(0, 14))
        ttk.Checkbutton(options_frame, text="Reduce steady background noise", variable=self.noise_reduction_var).grid(row=0, column=2, padx=(0, 14))
        ttk.Checkbutton(options_frame, text="Add grammar and diction comments", variable=self.review_var).grid(row=0, column=3, padx=(0, 14))
        ttk.Checkbutton(options_frame, text="Include live transcript appendix", variable=self.live_appendix_var).grid(row=0, column=4)

        status_line = ttk.Frame(container)
        status_line.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        status_line.columnconfigure(0, weight=1)
        ttk.Label(status_line, textvariable=self.model_status_var, style="ModelStatus.TLabel").grid(row=0, column=0, sticky="w")
        self.download_model_button = ttk.Button(
            status_line, text="Download Selected Model", command=self._download_model_requested
        )
        self.download_model_button.grid(row=0, column=1, padx=(10, 14))
        ttk.Label(status_line, textvariable=self.recording_var, style="ModelStatus.TLabel").grid(row=0, column=2, sticky="e")

        controls = ttk.Frame(container)
        controls.grid(row=5, column=0, sticky="ew", pady=11)
        controls.columnconfigure(12, weight=1)
        self.start_button = ttk.Button(
            controls, text="●  Start Listening", command=self._start_requested, style="Primary.TButton"
        )
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(controls, text="■  Stop", command=self._stop_requested, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=(0, 8))
        self.clear_button = ttk.Button(controls, text="New Session", command=self._clear_transcript)
        self.clear_button.grid(row=0, column=2, padx=(0, 14))
        ttk.Label(controls, text="Export:").grid(row=0, column=3, padx=(0, 6))
        self.save_docx_button = ttk.Button(controls, text="Word DOCX", command=self._save_docx)
        self.save_docx_button.grid(row=0, column=4, padx=(0, 6))
        self.save_txt_button = ttk.Button(controls, text="TXT", command=self._save_txt)
        self.save_txt_button.grid(row=0, column=5, padx=(0, 6))
        self.save_srt_button = ttk.Button(controls, text="SRT", command=self._save_srt)
        self.save_srt_button.grid(row=0, column=6, padx=(0, 10))
        ttk.Button(controls, text="Recording Folder", command=self._open_recording_folder).grid(row=0, column=7, padx=(0, 8))
        ttk.Button(
            controls, text="Vocabulary & Pronunciation", command=self._open_vocabulary_dialog
        ).grid(row=0, column=8, padx=(0, 12))
        ttk.Checkbutton(
            controls, text="Show timestamps", variable=self.timestamps_var, command=self._redraw_all
        ).grid(row=0, column=9, sticky="w")

        self.notebook = ttk.Notebook(container)
        self.notebook.grid(row=6, column=0, sticky="nsew")
        self.live_text = self._create_text_tab("Live transcript")
        self.final_text = self._create_text_tab("Final transcript")
        self.review_text = self._create_text_tab("Review comments")

        footer = ttk.Frame(container)
        footer.grid(row=7, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.activity_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=1, sticky="e")

    def _create_text_tab(self, title: str) -> tk.Text:
        frame = ttk.Frame(self.notebook, padding=8)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        text = tk.Text(frame, wrap="word", font=("Segoe UI", 12), padx=14, pady=12, relief="flat", borderwidth=0)
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scrollbar.set)
        text.tag_configure("timestamp", foreground="#666666")
        text.tag_configure("heading", font=("Segoe UI", 11, "bold"), spacing1=8, spacing3=3)
        text.tag_configure("body", spacing1=3, spacing3=7)
        text.tag_configure("note", foreground="#555555", spacing3=8)
        self.notebook.add(frame, text=title)
        return text

    def _label_and_combo(
        self,
        parent: ttk.Widget,
        column: int,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
        width: int,
    ) -> ttk.Combobox:
        holder = ttk.Frame(parent)
        holder.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        holder.columnconfigure(0, weight=1)
        ttk.Label(holder, text=label).grid(row=0, column=0, sticky="w")
        combo = ttk.Combobox(holder, textvariable=variable, values=values, state="readonly", width=width)
        combo.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        return combo

    def _refresh_microphones(self, *, auto_select: bool) -> None:
        microphones = list_microphones()
        labels = [microphone.label for microphone in microphones]
        if not labels:
            labels = ["Default input"]
        self.microphone_combo.configure(values=labels)
        current = self.microphone_var.get()
        if auto_select or current not in labels:
            selected = detect_default_microphone_label()
            if selected not in labels:
                selected = labels[0]
            self.microphone_var.set(selected)
            self.activity_var.set(f"Detected microphone: {selected}")

    def _selected_model_name(self) -> str:
        value = self.model_var.get().strip()
        return value if value in MODEL_OPTIONS else ""

    def _on_model_selected(self, _event=None) -> None:
        self.settings.model_name = self._selected_model_name()
        self.settings.save()
        self._update_model_status()
        if not (self.model_loading or self.model_downloading or self.finalizing or self.session is not None):
            self._set_controls_for_idle()

    def _update_model_status(self) -> None:
        self.model_status_var.set(model_status(self._selected_model_name()))

    def _collect_settings(self) -> AppSettings:
        return AppSettings(
            model_name=self._selected_model_name(),
            language_label=self.language_var.get(),
            microphone_label=self.microphone_var.get(),
            device_mode=self.device_var.get(),
            sensitivity_label=self.sensitivity_var.get(),
            include_timestamps=self.timestamps_var.get(),
            final_accuracy_pass=self.final_pass_var.get(),
            noise_reduction=self.noise_reduction_var.get(),
            grammar_diction_comments=self.review_var.get(),
            include_live_appendix=self.live_appendix_var.get(),
        )

    def _set_settings_state(self, state: str) -> None:
        for combo in (
            self.microphone_combo,
            self.language_combo,
            self.model_combo,
            self.device_combo,
            self.sensitivity_combo,
        ):
            combo.configure(state=state)

    def _set_controls_for_loading(self) -> None:
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.download_model_button.configure(state="disabled")
        self._set_settings_state("disabled")

    def _set_controls_for_listening(self) -> None:
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.download_model_button.configure(state="disabled")
        self._set_settings_state("disabled")

    def _set_controls_for_idle(self) -> None:
        model_name = self._selected_model_name()
        ready = bool(model_name and is_model_downloaded(model_name))
        self.start_button.configure(state="normal" if ready else "disabled")
        self.stop_button.configure(state="disabled")
        self.download_model_button.configure(
            state="normal" if model_name and not ready else "disabled"
        )
        self._set_settings_state("readonly")

    def _download_model_requested(self) -> None:
        if self.model_loading or self.model_downloading or self.finalizing or self.session is not None:
            return
        model_name = self._selected_model_name()
        if not model_name:
            messagebox.showinfo(
                "Select a model",
                "Choose a speech model from the list first, then click Download Selected Model.",
            )
            return
        if is_model_downloaded(model_name):
            messagebox.showinfo(
                "Model already downloaded",
                f"{model_name} is already stored in the portable models folder and can be used offline.",
            )
            self._set_controls_for_idle()
            return
        approved = messagebox.askokcancel(
            "Download speech model",
            f"Download the {model_name} speech model now?\n\n"
            "The portable application and its dependencies are already installed. "
            "Only the selected AI speech model will be downloaded. Keep the app open "
            "and stay connected to the internet until it finishes. Future sessions can "
            "reuse this model offline.",
        )
        if not approved:
            return
        self.settings.model_name = model_name
        self.settings.save()
        self.model_downloading = True
        self._set_controls_for_loading()
        self.status_var.set("Downloading model…")
        self.activity_var.set("Downloading the selected model into the portable models folder.")
        threading.Thread(
            target=self._download_model_worker,
            args=(model_name,),
            name="model-downloader",
            daemon=True,
        ).start()

    def _download_model_worker(self, model_name: str) -> None:
        try:
            download_model_once(model_name, progress_callback=self._threadsafe_status)
        except ModelLoadError as exc:
            self.root.after(0, self._model_download_failed, str(exc))
            return
        except Exception as exc:
            self.root.after(
                0,
                self._model_download_failed,
                "The model download did not finish. "
                f"Details: {str(exc).strip() or 'unknown download error'}",
            )
            return
        self.root.after(0, self._model_download_finished, model_name)

    def _model_download_finished(self, model_name: str) -> None:
        self.model_downloading = False
        self.settings.model_name = model_name
        self.settings.save()
        self._update_model_status()
        self._set_controls_for_idle()
        self.status_var.set("Ready.")
        self.activity_var.set(f"{model_name} is downloaded. You can now start listening offline.")
        messagebox.showinfo(
            "Model ready",
            f"{model_name} finished downloading and is ready for offline transcription.",
        )

    def _model_download_failed(self, message: str) -> None:
        self.model_downloading = False
        self._update_model_status()
        self._set_controls_for_idle()
        self.status_var.set("Ready.")
        self.activity_var.set("The model download did not finish.")
        messagebox.showerror("Could not download model", message)

    def _start_requested(self) -> None:
        if self.model_loading or self.model_downloading or self.finalizing or self.session is not None:
            return
        model_name = self._selected_model_name()
        if not model_name:
            messagebox.showinfo(
                "Select and download a model",
                "Choose a speech model and click Download Selected Model before starting a session.",
            )
            return
        if not is_model_downloaded(model_name):
            messagebox.showinfo(
                "Download required",
                "The selected model is not downloaded yet. Click Download Selected Model first.",
            )
            return
        if self.document.live_entries or self.document.final_entries:
            if not messagebox.askyesno(
                "Start a new session",
                "Starting again will clear the current on-screen transcript. Saved files will not be deleted. Continue?",
            ):
                return
            self._reset_document()

        self.settings = self._collect_settings()

        self.last_error_message = ""
        self.settings.save()
        self._set_controls_for_loading()
        self.status_var.set("Preparing model…")
        self.activity_var.set("Preparing local transcription and vocabulary engines.")
        self.model_loading = True
        threading.Thread(target=self._prepare_session, name="model-loader", daemon=True).start()

    def _prepare_session(self) -> None:
        try:
            engine = WhisperEngine(
                model_name=self.settings.model_name,
                device_mode=self.settings.device_mode,
                progress_callback=self._threadsafe_status,
            )
            engine.load()
            vocabulary = VocabularyManager()
            skills = SkillLibrary()
            hotwords = vocabulary.hotwords(skills.asr_hotwords())
            recording_path = new_recording_path()
            session = LiveTranscriptionSession(
                engine=engine,
                microphone_index=parse_microphone_index(self.settings.microphone_label),
                language_code=LANGUAGE_LABEL_TO_CODE[self.settings.language_label],
                rms_threshold=SENSITIVITY_THRESHOLDS[self.settings.sensitivity_label],
                recording_path=recording_path,
                hotwords=hotwords,
            )
            session.start()
        except (ModelLoadError, RuntimeError, KeyError) as exc:
            self.root.after(0, self._start_failed, str(exc))
            return
        except Exception as exc:
            self.root.after(
                0,
                self._start_failed,
                "The listening session could not start. "
                f"Details: {str(exc).strip() or 'unknown error'}",
            )
            return
        self.root.after(0, self._session_started, engine, session)

    def _threadsafe_status(self, message: str) -> None:
        self.root.after(0, self.status_var.set, message)

    def _session_started(self, engine: WhisperEngine, session: LiveTranscriptionSession) -> None:
        self.model_loading = False
        self.engine = engine
        self.session = session
        self._set_controls_for_listening()
        self._update_model_status()
        self.status_var.set("Listening")
        self.activity_var.set("Speak naturally. The live text is intentionally left unpolished until Stop.")
        self.recording_var.set(f"Recording WAV: {session.recording_path.name}")
        self.notebook.select(0)

    def _start_failed(self, message: str) -> None:
        self.model_loading = False
        self.engine = None
        self.session = None
        self._set_controls_for_idle()
        self._update_model_status()
        self.status_var.set("Ready.")
        self.activity_var.set("Listening did not start.")
        messagebox.showerror("Could not start listening", message)

    def _stop_requested(self) -> None:
        if self.session is None:
            return
        self.stop_button.configure(state="disabled")
        self.status_var.set("Finishing the WAV…")
        self.activity_var.set("Completing the last phrase and safely closing the recording.")
        self.session.stop()

    def _poll_session_events(self) -> None:
        session = self.session
        if session is not None:
            while True:
                try:
                    event = session.events.get_nowait()
                except queue.Empty:
                    break
                self._handle_session_event(event)
        self.root.after(self.POLL_INTERVAL_MS, self._poll_session_events)

    def _handle_session_event(self, event: SessionEvent) -> None:
        if event.kind == "listening":
            payload = event.payload or {}
            self.selected_microphone_name = str(payload.get("microphone", self.microphone_var.get()))
            self.status_var.set("Listening")
            return
        if event.kind == "processing":
            self.status_var.set("Writing the latest phrase…")
            return
        if event.kind == "segment" and isinstance(event.payload, TranscriptSegment):
            entry = self.document.add_live(event.payload)
            if entry is not None:
                self._append_entry(self.live_text, entry)
            self.status_var.set("Listening")
            return
        if event.kind == "warning":
            self.activity_var.set(str(event.payload))
            return
        if event.kind == "error":
            message = str(event.payload)
            self.activity_var.set(message)
            self.last_error_message = message
            self.status_var.set("Listening")
            return
        if event.kind == "stopping":
            self.status_var.set("Finishing…")
            return
        if event.kind == "finished":
            payload = event.payload or {}
            recording_path = Path(payload["recording_path"])
            self.document.recording_path = recording_path
            self.session = None
            if self.settings.final_accuracy_pass and self.engine is not None:
                self._start_finalization(recording_path)
            else:
                self._set_controls_for_idle()
                self.status_var.set("Ready.")
                self.activity_var.set("Listening stopped. Original WAV and live transcript are ready.")

    def _start_finalization(self, recording_path: Path) -> None:
        self.finalizing = True
        self._set_controls_for_loading()
        self.status_var.set("Checking the full recording…")
        self.activity_var.set("Reducing noise when enabled, then transcribing the complete WAV again.")
        threading.Thread(
            target=self._run_finalization,
            args=(recording_path,),
            name="post-session-review",
            daemon=True,
        ).start()

    def _run_finalization(self, recording_path: Path) -> None:
        try:
            if self.engine is None:
                raise RuntimeError("The speech engine is not available for the final pass.")
            processor = PostSessionProcessor(
                self.engine,
                language_code=LANGUAGE_LABEL_TO_CODE[self.settings.language_label],
                noise_reduction=self.settings.noise_reduction,
                grammar_diction_comments=self.settings.grammar_diction_comments,
            )
            result = processor.process(
                recording_path,
                live_entries=tuple(self.document.live_entries),
            )
        except Exception as exc:
            self.root.after(0, self._finalization_failed, str(exc))
            return
        self.root.after(0, self._finalization_done, result)

    def _finalization_done(self, result: PostSessionResult) -> None:
        self.finalizing = False
        self.document.set_final(
            result.segments,
            result.comments,
            recording_path=result.recording_path,
            enhanced_recording_path=result.enhanced_recording_path,
        )
        self._redraw_final()
        self._redraw_review()
        self._set_controls_for_idle()
        self.status_var.set("Review complete")
        warning_text = " ".join(result.warnings)
        self.activity_var.set(
            warning_text
            or "Final transcript, WAV recording, and grammar/diction comments are ready."
        )
        self.notebook.select(1)

    def _finalization_failed(self, message: str) -> None:
        self.finalizing = False
        self._set_controls_for_idle()
        self.status_var.set("Ready.")
        self.activity_var.set("The final pass did not finish. The original WAV and live transcript are still safe.")
        messagebox.showwarning(
            "Final accuracy pass did not finish",
            "The live transcript and original WAV were saved, but the second pass could not finish.\n\n"
            + (message or "Unknown processing error"),
        )

    def _append_entry(self, widget: tk.Text, entry: TranscriptEntry) -> None:
        if self.timestamps_var.get():
            widget.insert("end", f"[{format_clock(entry.start)}] ", "timestamp")
        widget.insert("end", entry.text + "\n", "body")
        widget.see("end")

    def _redraw_all(self) -> None:
        self.live_text.delete("1.0", "end")
        for entry in self.document.live_entries:
            self._append_entry(self.live_text, entry)
        self._redraw_final()
        self._redraw_review()
        self.settings.include_timestamps = self.timestamps_var.get()
        self.settings.save()

    def _redraw_final(self) -> None:
        self.final_text.delete("1.0", "end")
        if not self.document.final_entries:
            self.final_text.insert(
                "end",
                "The final transcript appears here after the speaker presses Stop and the complete WAV is checked.\n",
                "note",
            )
            return
        for entry in self.document.final_entries:
            self._append_entry(self.final_text, entry)

    def _redraw_review(self) -> None:
        self.review_text.delete("1.0", "end")
        if not self.document.review_comments:
            self.review_text.insert(
                "end",
                "No review comments are available yet. Comments are suggestions and do not replace the verbatim transcript.\n",
                "note",
            )
            return
        for comment in self.document.review_comments:
            self.review_text.insert(
                "end",
                f"[{format_clock(comment.timestamp)}] {comment.category} — {comment.severity}\n",
                "heading",
            )
            self.review_text.insert("end", f"Original: {comment.original}\n", "body")
            self.review_text.insert("end", f"Suggestion: {comment.suggestion}\n", "body")
            self.review_text.insert("end", f"Comment: {comment.explanation}\n\n", "note")

    def _clear_transcript(self) -> None:
        if self.session is not None or self.model_loading or self.model_downloading or self.finalizing:
            messagebox.showinfo("Session is active", "Stop the current session before starting a new one.")
            return
        if (self.document.live_entries or self.document.final_entries) and not messagebox.askyesno(
            "New session",
            "Clear the current on-screen transcript? Saved DOCX, TXT, SRT, and WAV files will not be deleted.",
        ):
            return
        self._reset_document()
        self.activity_var.set("New session ready.")

    def _reset_document(self) -> None:
        self.document = TranscriptDocument()
        for widget in (self.live_text, self.final_text, self.review_text):
            widget.delete("1.0", "end")
        self._redraw_final()
        self._redraw_review()
        self.recording_var.set("WAV recording: not started")

    def _ensure_content(self) -> bool:
        if self.document.entries:
            return True
        messagebox.showinfo("Nothing to save", "Start listening and create a transcript first.")
        return False

    def _save_docx(self) -> None:
        if not self._ensure_content():
            return
        title = simpledialog.askstring(
            "Document title",
            "Enter the title for the Word document:",
            initialvalue="Live Transcription Report",
            parent=self.root,
        )
        if title is None:
            return
        title = title.strip() or "Live Transcription Report"
        path = filedialog.asksaveasfilename(
            title="Save formatted Word transcript",
            initialdir=str(EXPORT_DIR),
            initialfile=self.document.suggested_filename("docx"),
            defaultextension=".docx",
            filetypes=(("Microsoft Word document", "*.docx"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            self.document.save_docx(
                Path(path),
                include_timestamps=self.timestamps_var.get(),
                title=title,
                language=self.language_var.get(),
                model=self.model_var.get(),
                microphone=self.selected_microphone_name,
                include_live_appendix=self.live_appendix_var.get(),
            )
        except Exception as exc:
            messagebox.showerror(
                "Could not save Word document",
                "The formatted Word document could not be saved. "
                f"Details: {str(exc).strip() or 'unknown file error'}",
            )
            return
        self.activity_var.set(f"Saved formatted DOCX: {path}")

    def _save_txt(self) -> None:
        if not self._ensure_content():
            return
        path = filedialog.asksaveasfilename(
            title="Save transcript as text",
            initialdir=str(EXPORT_DIR),
            initialfile=self.document.suggested_filename("txt"),
            defaultextension=".txt",
            filetypes=(("Text file", "*.txt"), ("All files", "*.*")),
        )
        if path:
            try:
                self.document.save_txt(Path(path), include_timestamps=self.timestamps_var.get())
            except OSError as exc:
                messagebox.showerror("Could not save transcript", f"The file could not be saved.\n\n{exc}")
                return
            self.activity_var.set(f"Saved TXT: {path}")

    def _save_srt(self) -> None:
        if not self._ensure_content():
            return
        path = filedialog.asksaveasfilename(
            title="Save transcript as subtitles",
            initialdir=str(EXPORT_DIR),
            initialfile=self.document.suggested_filename("srt"),
            defaultextension=".srt",
            filetypes=(("Subtitle file", "*.srt"), ("All files", "*.*")),
        )
        if path:
            try:
                self.document.save_srt(Path(path))
            except OSError as exc:
                messagebox.showerror("Could not save subtitles", f"The file could not be saved.\n\n{exc}")
                return
            self.activity_var.set(f"Saved SRT: {path}")

    def _open_vocabulary_dialog(self) -> None:
        if self.session is not None or self.model_loading or self.model_downloading or self.finalizing:
            messagebox.showinfo(
                "Session is active",
                "Finish the current operation before editing the vocabulary and pronunciation guide.",
            )
            return
        VocabularyPronunciationDialog(self.root)

    def _open_recording_folder(self) -> None:
        RECORDING_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(RECORDING_DIR))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(RECORDING_DIR)])
            else:
                subprocess.Popen(["xdg-open", str(RECORDING_DIR)])
        except Exception as exc:
            messagebox.showinfo(
                "Recording folder",
                f"Recordings are saved here:\n{RECORDING_DIR}\n\nThe folder could not be opened automatically: {exc}",
            )

    def _on_close(self) -> None:
        if (self.model_loading or self.model_downloading or self.finalizing) and not messagebox.askyesno(
            "Close application",
            "The app is still downloading or processing. Close anyway? An incomplete model download may need to be resumed.",
        ):
            return
        if self.session is not None:
            self.session.stop()
        self.settings = self._collect_settings()
        self.settings.save()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
