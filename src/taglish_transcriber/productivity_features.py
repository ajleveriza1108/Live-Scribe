from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import customtkinter as ctk

from .audio import recover_rolling_recording
from .caption_window import FloatingCaptionWindow
from .config import (
    AUDIO_SOURCE_SYSTEM,
    GRAMMAR_REVIEW_LANGUAGE_LABELS,
    LANGUAGE_LABEL_TO_CODE,
    MODEL_OPTIONS,
    MODEL_PLACEHOLDER,
    SENSITIVITY_THRESHOLDS,
    model_friendly_name,
)
from .dictionary_engine import VocabularyManager
from .media import MEDIA_FILE_TYPES, MediaInfo, inspect_media, play_audio_segment
from .models import ModelLoadError, WhisperEngine, is_model_downloaded
from .paths import EXPORT_DIR, RECORDING_DIR
from .postprocess import PostSessionProcessor, PostSessionResult
from .recovery import RecoveryManager
from .session import SessionEvent
from .session_store import SessionStore
from .skill_library import SkillLibrary
from .storage_manager import (
    clean_all_recording_parts,
    clean_completed_recording_parts,
    clean_partial_downloads,
    clean_temporary_files,
    format_size,
    remove_model,
    storage_items,
)
from .transcript import TranscriptDocument, TranscriptEntry, format_clock


class ProductivityFeaturesMixin:
    """Feature layer that adds no additional LLM or large AI model."""

    def __init__(self) -> None:
        self.session_store = SessionStore()
        self.recovery_manager = RecoveryManager()
        self.pending_session_title = ""
        self.caption_window: FloatingCaptionWindow | None = None
        self.no_audio_warned = False
        self.session_search_var: tk.StringVar | None = None
        self.session_title_var: tk.StringVar | None = None
        self.audio_level_var: tk.DoubleVar | None = None
        self.audio_level_text_var: tk.StringVar | None = None
        self.storage_window = None
        super().__init__()

        self.caption_window = FloatingCaptionWindow(
            self.root,
            font_family=self.font_family,
            theme_name=self.theme_var.get(),
        )
        self._configure_productivity_shortcuts()
        self._refresh_session_library()
        self.root.after(900, self._offer_session_recovery)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        super()._build_ui()
        self._build_sessions_page()

    def _build_live_page(self) -> None:
        super()._build_live_page()

        self.session_title_var = tk.StringVar(value="")
        ctk.CTkLabel(
            self.input_card,
            text="Session title",
            text_color=self._color("text_secondary"),
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=5, column=0, sticky="w", padx=16, pady=(0, 6))
        self.session_title_entry = ctk.CTkEntry(
            self.input_card,
            textvariable=self.session_title_var,
            height=38,
            corner_radius=8,
            fg_color=self._color("surface_alt"),
            border_color=self._color("border"),
            text_color=self._color("text"),
            placeholder_text="Example: Weekly Sales Meeting",
        )
        self.session_title_entry.grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=16,
            pady=(0, 12),
        )

        recorded_file_panel = ctk.CTkFrame(self.input_card, corner_radius=10, fg_color=self._color("surface_raised"), border_color=self._color("border"), border_width=1)
        recorded_file_panel.grid(row=7, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 14))
        recorded_file_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(recorded_file_panel, text="Already have a recorded video or audio file?", text_color=self._color("text"), font=ctk.CTkFont(family=self.font_family, size=13, weight="bold")).grid(row=0,column=0,sticky="w",padx=14,pady=(12,3))
        ctk.CTkLabel(recorded_file_panel, text="Choose an MP4, MKV, MP3, WAV, or another supported recording. Live Scribe reads its audio track and keeps the original file unchanged.", text_color=self._color("text_secondary"), justify="left", anchor="w", wraplength=700, font=ctk.CTkFont(family=self.font_family,size=11)).grid(row=1,column=0,sticky="ew",padx=14,pady=(0,12))
        self.import_media_primary_button = ctk.CTkButton(recorded_file_panel, text="Choose Video or Audio File", command=self._transcribe_file_requested, width=200, height=38, corner_radius=8, fg_color=self._color("success"), hover_color=self._color("success"), text_color="#FFFFFF")
        self.import_media_primary_button.grid(row=0,column=1,rowspan=2,sticky="e",padx=14,pady=12)

        self.audio_level_var = tk.DoubleVar(value=0.0)
        self.audio_level_text_var = tk.StringVar(value="Waiting for audio")
        ctk.CTkLabel(
            self.status_row,
            text="Input",
            text_color=self._color("muted"),
            font=ctk.CTkFont(family=self.font_family, size=10, weight="bold"),
        ).grid(row=0, column=2, padx=(12, 6))
        self.audio_level_bar = ctk.CTkProgressBar(
            self.status_row,
            variable=self.audio_level_var,
            width=150,
            height=9,
            corner_radius=5,
            progress_color=self._color("success"),
            fg_color=self._color("surface_raised"),
        )
        self.audio_level_bar.grid(row=0, column=3, padx=6)
        ctk.CTkLabel(
            self.status_row,
            textvariable=self.audio_level_text_var,
            text_color=self._color("muted"),
            font=ctk.CTkFont(family=self.font_family, size=10),
        ).grid(row=0, column=4, padx=(6, 0), sticky="e")

        # Reflow the action buttons into two compact rows.
        self.action_bar.grid_columnconfigure(9, weight=1)
        self.start_button.grid_configure(row=0, column=0)
        self.pause_button = ctk.CTkButton(
            self.action_bar,
            text="Pause",
            command=self._pause_resume_requested,
            state="disabled",
            height=42,
            corner_radius=9,
            fg_color=self._color("warning"),
            hover_color=self._color("warning"),
            text_color="#FFFFFF",
        )
        self.pause_button.grid(row=0, column=1, padx=6, pady=(10, 5))
        self.stop_button.grid_configure(row=0, column=2, pady=(10, 5))
        self.verify_wav_button.grid_configure(row=0, column=3, pady=(10, 5))

        self.import_media_button = ctk.CTkButton(
            self.action_bar,
            text="Transcribe Video / Audio",
            command=self._transcribe_file_requested,
            height=42,
            corner_radius=9,
            fg_color=self._color("success"),
            hover_color=self._color("success"),
            text_color="#FFFFFF",
        )
        self.import_media_button.grid(row=0, column=4, padx=6, pady=(10, 5))

        self.caption_button = ctk.CTkButton(
            self.action_bar,
            text="Floating Captions",
            command=self._toggle_caption_window,
            height=38,
            corner_radius=9,
            fg_color="transparent",
            hover_color=self._color("surface_raised"),
            border_color=self._color("border"),
            border_width=1,
            text_color=self._color("text"),
        )
        self.caption_button.grid(row=1, column=0, padx=(12, 6), pady=(5, 10))
        self.clear_button.grid_configure(row=1, column=1, pady=(5, 10))
        self.export_button.grid_configure(row=1, column=2, pady=(5, 10))
        self.recording_folder_button.grid_configure(row=1, column=3, pady=(5, 10))

        self._build_transcript_editor()

    def _color(self, key: str):
        # Resolve the same palette stored by the modern UI without importing it,
        # which avoids a circular import.
        palette = {
            "surface_alt": ("#FFFFFF", "#11151A"),
            "surface_raised": ("#F5F2EB", "#171C22"),
            "border": ("#D5D0C5", "#252B33"),
            "text": ("#171717", "#F5F7FA"),
            "text_secondary": ("#625D55", "#A7B0BA"),
            "muted": ("#898278", "#6F7A86"),
            "success": ("#2E8B57", "#4DD17A"),
            "warning": ("#A76C00", "#F2B94B"),
            "danger": ("#C43D4B", "#FF5C66"),
        }
        return palette[key]

    def _build_transcript_editor(self) -> None:
        editor = self.notebook.add("Transcript editor")
        editor.grid_rowconfigure(0, weight=1)
        editor.grid_columnconfigure(0, weight=1)

        style = ttk.Style(self.root)
        style.configure(
            "LiveScribe.Treeview",
            rowheight=28,
            font=(self.font_family, 10),
        )
        style.configure(
            "LiveScribe.Treeview.Heading",
            font=(self.font_family, 10, "bold"),
        )

        columns = ("time", "speaker", "text", "status", "markers")
        self.editor_tree = ttk.Treeview(
            editor,
            columns=columns,
            show="headings",
            style="LiveScribe.Treeview",
            selectmode="browse",
        )
        headings = {
            "time": "Time",
            "speaker": "Speaker",
            "text": "Transcript",
            "status": "Checked",
            "markers": "Markers",
        }
        widths = {
            "time": 90,
            "speaker": 130,
            "text": 640,
            "status": 70,
            "markers": 140,
        }
        for name in columns:
            self.editor_tree.heading(name, text=headings[name])
            self.editor_tree.column(
                name,
                width=widths[name],
                minwidth=60,
                stretch=name == "text",
                anchor="w",
            )
        self.editor_tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        self.editor_tree.bind("<Double-1>", lambda _event: self._edit_selected_entry())

        scroll = ttk.Scrollbar(editor, orient="vertical", command=self.editor_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns", pady=(8, 4))
        self.editor_tree.configure(yscrollcommand=scroll.set)

        controls = ctk.CTkFrame(editor, fg_color="transparent")
        controls.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
        actions = (
            ("Edit Text", self._edit_selected_entry),
            ("Set Speaker", self._set_selected_speaker),
            ("Play 8 Seconds", self._play_selected_entry),
            ("Important", lambda: self._mark_selected_entry("Important")),
            ("Action Item", lambda: self._mark_selected_entry("Action Item")),
            ("Question", lambda: self._mark_selected_entry("Question")),
            ("Toggle Checked", self._toggle_selected_verified),
        )
        for index, (label, command) in enumerate(actions):
            ctk.CTkButton(
                controls,
                text=label,
                command=command,
                height=34,
                corner_radius=8,
                fg_color="transparent",
                hover_color=self._color("surface_raised"),
                border_color=self._color("border"),
                border_width=1,
                text_color=self._color("text"),
            ).grid(row=0, column=index, padx=3, pady=2)

    def _build_sessions_page(self) -> None:
        page = self._page_frame("Sessions")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 18))
        self._page_header(
            header,
            "Saved Sessions",
            "Search live sessions and imported recordings without using a cloud account.",
        )

        search_card = self._card(page, row=1, column=0, sticky="ew", padx=28, pady=(0, 14))
        search_card.grid_columnconfigure(0, weight=1)
        self.session_search_var = tk.StringVar(value="")
        search_entry = ctk.CTkEntry(
            search_card,
            textvariable=self.session_search_var,
            placeholder_text="Search title, transcript, speaker, topic, marker, or language",
            height=40,
            corner_radius=8,
            fg_color=self._color("surface_alt"),
            border_color=self._color("border"),
            text_color=self._color("text"),
        )
        search_entry.grid(row=0, column=0, sticky="ew", padx=(18, 8), pady=16)
        ctk.CTkButton(
            search_card,
            text="Search",
            command=self._refresh_session_library,
            width=90,
            height=40,
            corner_radius=8,
        ).grid(row=0, column=1, padx=(8, 18), pady=16)
        self.session_search_var.trace_add(
            "write",
            lambda *_args: self.root.after(120, self._refresh_session_library),
        )

        card = self._card(page, row=2, column=0, sticky="nsew", padx=28, pady=(0, 24))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        columns = ("created", "type", "title", "language", "duration", "status")
        self.session_tree = ttk.Treeview(
            card,
            columns=columns,
            show="headings",
            style="LiveScribe.Treeview",
            selectmode="browse",
        )
        labels = {
            "created": "Created",
            "type": "Source",
            "title": "Title",
            "language": "Language",
            "duration": "Duration",
            "status": "Status",
        }
        widths = {
            "created": 145,
            "type": 75,
            "title": 410,
            "language": 170,
            "duration": 90,
            "status": 90,
        }
        for name in columns:
            self.session_tree.heading(name, text=labels[name])
            self.session_tree.column(
                name,
                width=widths[name],
                minwidth=60,
                stretch=name == "title",
                anchor="w",
            )
        self.session_tree.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 4))
        self.session_tree.bind("<Double-1>", lambda _event: self._open_selected_session())

        scrollbar = ttk.Scrollbar(card, orient="vertical", command=self.session_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=(12, 4))
        self.session_tree.configure(yscrollcommand=scrollbar.set)

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(6, 12))
        for index, (label, command) in enumerate(
            (
                ("Open Session", self._open_selected_session),
                ("Rename", self._rename_selected_session),
                ("Open Source File", self._open_selected_session_source),
                ("Delete from Library", self._delete_selected_session),
            )
        ):
            ctk.CTkButton(
                buttons,
                text=label,
                command=command,
                height=36,
                corner_radius=8,
                fg_color="transparent" if index else self._color("success"),
                hover_color=self._color("surface_raised"),
                border_color=self._color("border"),
                border_width=0 if index == 0 else 1,
                text_color="#FFFFFF" if index == 0 else self._color("text"),
            ).grid(row=0, column=index, padx=4)

    def _build_models_page(self) -> None:
        super()._build_models_page()
        self.storage_button = ctk.CTkButton(
            self.hardware_card,
            text="Storage Manager",
            command=self._open_storage_manager,
            width=160,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            hover_color=self._color("surface_raised"),
            border_color=self._color("border"),
            border_width=1,
            text_color=self._color("text"),
        )
        self.storage_button.grid(row=3, column=1, sticky="e", padx=20, pady=(0, 18))

    # ------------------------------------------------------------------
    # Shortcuts and state
    # ------------------------------------------------------------------
    def _configure_productivity_shortcuts(self) -> None:
        self.root.bind("<Control-p>", lambda _event: self._pause_resume_requested())
        self.root.bind("<Control-o>", lambda _event: self._transcribe_file_requested())
        self.root.bind("<F11>", lambda _event: self._toggle_caption_window())
        self.root.bind("<Control-m>", lambda _event: self._mark_selected_entry("Important"))
        self.root.bind("<Control-Key-1>", lambda _event: self._quick_speaker("Speaker 1"))
        self.root.bind("<Control-Key-2>", lambda _event: self._quick_speaker("Speaker 2"))
        self.root.bind("<Control-Key-3>", lambda _event: self._quick_speaker("Speaker 3"))

    def _set_controls_for_loading(self) -> None:
        super()._set_controls_for_loading()
        if hasattr(self, "pause_button"):
            self.pause_button.configure(state="disabled")
        if hasattr(self, "import_media_button"):
            self.import_media_button.configure(state="disabled")
        if hasattr(self, "import_media_primary_button"):
            self.import_media_primary_button.configure(state="disabled")
        if hasattr(self, "session_title_entry"):
            self.session_title_entry.configure(state="disabled")

    def _set_controls_for_listening(self) -> None:
        super()._set_controls_for_listening()
        self.pause_button.configure(state="normal", text="Pause")
        self.import_media_button.configure(state="disabled")
        if hasattr(self, "import_media_primary_button"):
            self.import_media_primary_button.configure(state="disabled")
        self.session_title_entry.configure(state="disabled")

    def _set_controls_for_idle(self) -> None:
        super()._set_controls_for_idle()
        if hasattr(self, "pause_button"):
            self.pause_button.configure(state="disabled", text="Pause")
        if hasattr(self, "session_title_entry"):
            self.session_title_entry.configure(state="normal")
        if hasattr(self, "import_media_button"):
            model_name = self._selected_model_name()
            allowed = bool(
                model_name
                and is_model_downloaded(model_name)
                and not (self.model_loading or self.model_downloading or self.finalizing)
            )
            state = "normal" if allowed else "disabled"
            self.import_media_button.configure(state=state)
            if hasattr(self, "import_media_primary_button"):
                self.import_media_primary_button.configure(state=state)
        if hasattr(self, "verify_wav_button") and self.document.recording_path:
            if self.document.source_type == "imported":
                self.verify_wav_button.configure(
                    text="Re-transcribe Source",
                    state="normal" if self.engine is not None else "disabled",
                )
            else:
                self.verify_wav_button.configure(
                    text=(
                        "Re-verify from WAV"
                        if self.document.is_finalized
                        else "Verify from WAV"
                    )
                )

    # ------------------------------------------------------------------
    # Live session, pause, audio meter, recovery
    # ------------------------------------------------------------------
    def _start_requested(self) -> None:
        if self.session_title_var is not None:
            title = " ".join(self.session_title_var.get().strip().split())
        else:
            title = ""
        if not title:
            title = datetime.now().strftime("Live Session %Y-%m-%d %H-%M")
            if self.session_title_var is not None:
                self.session_title_var.set(title)
        self.pending_session_title = title
        if not self.document.entries:
            self.document.title = title
            self.document.source_type = "live"
        super()._start_requested()

    def _session_started(self, engine, session) -> None:
        super()._session_started(engine, session)
        self.document.title = self.pending_session_title or self.document.title
        self.document.source_type = "live"
        self.document.recording_path = session.recording_path
        self.document.language = self.language_var.get()
        self.document.topic = self.topic_var.get()
        self.document.model = self.model_var.get()
        self.document.audio_input = session.audio_input_label
        self.recovery_manager.save(self.document, state="recording", force=True)
        self.no_audio_warned = False
        self._refresh_editor()

    def _pause_resume_requested(self) -> None:
        session = self.session
        if session is None:
            return
        if session.is_paused:
            session.resume()
        else:
            session.pause()

    def _handle_session_event(self, event: SessionEvent) -> None:
        super()._handle_session_event(event)

        if event.kind == "audio_level":
            self._apply_audio_level(event.payload or {})
            return
        if event.kind == "paused":
            self.pause_button.configure(text="Resume")
            self.status_var.set("Paused")
            self.recording_var.set("Paused — WAV and transcript are not advancing")
            self.audio_level_text_var.set("Paused")
            self.recovery_manager.save(self.document, state="paused", force=True)
            return
        if event.kind == "resumed":
            self.pause_button.configure(text="Pause")
            self.status_var.set("Listening")
            self.recording_var.set(
                f"Recording WAV: {self.document.recording_path.name}"
                if self.document.recording_path
                else "Recording WAV"
            )
            self.no_audio_warned = False
            self.recovery_manager.save(self.document, state="recording", force=True)
            return
        if event.kind == "segment":
            entry = self.document.live_entries[-1] if self.document.live_entries else None
            if entry is not None:
                if self.caption_window is not None:
                    self.caption_window.update(entry.text, entry.speaker)
                self._refresh_editor(select_last=True)
            self.recovery_manager.save(self.document, state="recording")
            return
        if event.kind == "finished":
            self.pause_button.configure(state="disabled", text="Pause")
            self.audio_level_var.set(0.0)
            self.audio_level_text_var.set("Stopped")
            self._persist_current_document()
            self.recovery_manager.clear()
            self._refresh_editor()
            self._refresh_session_library()

    def _apply_audio_level(self, payload: dict) -> None:
        if self.audio_level_var is None or self.audio_level_text_var is None:
            return
        if payload.get("paused"):
            self.audio_level_var.set(0.0)
            self.audio_level_text_var.set("Paused")
            return

        rms = max(0.0, float(payload.get("rms", 0.0)))
        peak = max(0.0, float(payload.get("peak", 0.0)))
        quiet_seconds = max(0.0, float(payload.get("quiet_seconds", 0.0)))
        clipping = bool(payload.get("clipping"))
        level = min(1.0, rms * 18.0)
        self.audio_level_var.set(level)

        if clipping:
            self.audio_level_text_var.set("Too loud / clipping")
        elif quiet_seconds >= 8:
            self.audio_level_text_var.set("No audio detected")
            if not self.no_audio_warned:
                self.no_audio_warned = True
                self.activity_var.set(
                    "No usable audio has been detected for several seconds. "
                    "Check the selected input, meeting output, microphone mute, and volume."
                )
        elif rms < 0.003:
            self.audio_level_text_var.set("Very quiet")
        elif peak > 0.75:
            self.audio_level_text_var.set("Strong signal")
            self.no_audio_warned = False
        else:
            self.audio_level_text_var.set("Good signal")
            self.no_audio_warned = False

    def _reset_document(self) -> None:
        title = self.pending_session_title
        if not title and self.session_title_var is not None:
            title = self.session_title_var.get().strip()
        super()._reset_document()
        self.document.title = title or "Untitled Session"
        self.document.source_type = "live"
        self._refresh_editor()
        if self.caption_window is not None:
            self.caption_window.update("Captions will appear here when speech is detected.")

    def _finalization_done(self, result: PostSessionResult) -> None:
        super()._finalization_done(result)
        self._persist_current_document()
        self.recovery_manager.clear()
        self._refresh_editor()
        self._refresh_session_library()

    def _persist_current_document(self) -> None:
        if self.document.entries:
            try:
                self.session_store.save(self.document)
            except Exception as exc:
                self.activity_var.set(
                    "The transcript is on screen, but the local session library could not update. "
                    f"Details: {str(exc).strip() or 'database error'}"
                )

    def _offer_session_recovery(self) -> None:
        recovered = self.recovery_manager.load()
        if recovered is None:
            return
        state, document = recovered
        choice = messagebox.askyesnocancel(
            "Recover unfinished session",
            "Live Scribe found an unfinished session from an earlier interruption.\n\n"
            f"Title: {document.title}\n"
            f"Saved transcript lines: {len(document.live_entries)}\n"
            f"Last state: {state}\n\n"
            "Yes — recover the transcript and available WAV parts\n"
            "No — discard this recovery record\n"
            "Cancel — keep it for later and open the recordings folder",
        )
        if choice is None:
            self._open_recording_folder()
            return
        if choice is False:
            self.recovery_manager.clear()
            return

        if document.recording_path and not document.recording_path.exists():
            recover_rolling_recording(document.recording_path)
        self.document = document
        if self.session_title_var is not None:
            self.session_title_var.set(document.title)
        self._redraw_all()
        self._refresh_editor()
        self._set_controls_for_idle()
        self._persist_current_document()
        self.recovery_manager.clear()
        self._show_page("Live Session")
        self.activity_var.set(
            "Recovered the unfinished transcript. Verify the available recording before relying on it."
        )

    # ------------------------------------------------------------------
    # Recorded media import
    # ------------------------------------------------------------------
    def _transcribe_file_requested(self) -> None:
        if self.session is not None or self.model_loading or self.model_downloading or self.finalizing:
            return
        model_name = self._selected_model_name()
        if not model_name or not is_model_downloaded(model_name):
            messagebox.showinfo(
                "Speech quality required",
                "Download and select a speech quality before transcribing a recorded file.",
            )
            return

        filename = filedialog.askopenfilename(
            title="Choose a recorded video or audio file",
            initialdir=str(RECORDING_DIR),
            filetypes=MEDIA_FILE_TYPES,
        )
        if not filename:
            return
        path = Path(filename)
        try:
            info = inspect_media(path)
        except Exception as exc:
            messagebox.showerror("Could not open recording", str(exc))
            return

        title = simpledialog.askstring(
            "Session title",
            "Enter a title for this recorded-file transcription:",
            initialvalue=path.stem,
            parent=self.root,
        )
        if title is None:
            return
        title = " ".join(title.strip().split()) or path.stem

        self.pending_session_title = title
        self.document = TranscriptDocument(title=title, source_type="imported")
        self.document.recording_path = path
        self.document.language = self.language_var.get()
        self.document.topic = self.topic_var.get()
        self.document.model = self.model_var.get()
        self.document.audio_input = f"Imported {info.source_type}: {path.name}"
        if self.session_title_var is not None:
            self.session_title_var.set(title)
        self._redraw_all()
        self._refresh_editor()

        self.finalizing = True
        self._set_controls_for_loading()
        self.status_var.set("Transcribing recorded file")
        duration = (
            f" ({format_clock(info.duration_seconds)})"
            if info.duration_seconds is not None
            else ""
        )
        self.activity_var.set(
            f"Reading {path.name}{duration}. Video images are ignored; only the audio track is transcribed."
        )
        threading.Thread(
            target=self._run_recorded_file_transcription,
            args=(path, info),
            name="recorded-media-transcriber",
            daemon=True,
        ).start()

    def _run_recorded_file_transcription(self, path: Path, info: MediaInfo) -> None:
        try:
            model_name = self._selected_model_name()
            engine = self.engine
            if (
                engine is None
                or engine.model_name != model_name
                or engine.device_mode != self.device_var.get()
            ):
                engine = WhisperEngine(
                    model_name=model_name,
                    device_mode=self.device_var.get(),
                    progress_callback=self._threadsafe_status,
                )
                engine.load()

            vocabulary = VocabularyManager()
            skills = SkillLibrary()
            topic_context, topic_terms = self._topic_context_for_session()
            self.active_topic_context = topic_context
            self.active_topic_terms = list(topic_terms)
            processor = PostSessionProcessor(
                engine,
                language_code=LANGUAGE_LABEL_TO_CODE[self.language_var.get()],
                language_label=self.language_var.get(),
                noise_reduction=False,
                grammar_diction_comments=self.review_var.get(),
                topic_context=topic_context,
                topic_terms=topic_terms,
            )
            result = processor.process(path, live_entries=())
        except Exception as exc:
            self.root.after(
                0,
                self._recorded_file_failed,
                str(exc).strip() or "unknown transcription error",
            )
            return
        self.root.after(0, self._recorded_file_done, engine, result, info)

    def _recorded_file_done(
        self,
        engine: WhisperEngine,
        result: PostSessionResult,
        info: MediaInfo,
    ) -> None:
        self.engine = engine
        self.document.source_type = "imported"
        self._finalization_done(result)
        self.status_var.set("Recorded file complete")
        self.activity_var.set(
            f"Transcribed {info.source_type} file: {info.path.name}. "
            "Use Transcript editor to correct text, add speakers, play timestamps, and mark important moments."
        )
        self.notebook.select("Transcript editor")

    def _recorded_file_failed(self, message: str) -> None:
        self.finalizing = False
        self._set_controls_for_idle()
        self.status_var.set("Ready")
        self.activity_var.set("The recorded file was not changed.")
        messagebox.showerror(
            "Recorded file could not be transcribed",
            "Live Scribe could not complete the selected recording.\n\n" + message,
        )

    # ------------------------------------------------------------------
    # Transcript editor, speakers, markers, playback
    # ------------------------------------------------------------------
    def _refresh_editor(self, *, select_last: bool = False) -> None:
        if not hasattr(self, "editor_tree"):
            return
        selected = self.editor_tree.selection()
        selected_index = self._selected_editor_index()
        self.editor_tree.delete(*self.editor_tree.get_children())
        for index, entry in enumerate(self.document.entries):
            self.editor_tree.insert(
                "",
                "end",
                iid=f"entry-{index}",
                values=(
                    format_clock(entry.start),
                    entry.speaker,
                    entry.text,
                    "Yes" if entry.verified else "",
                    self.document.marker_labels_at(entry.start),
                ),
            )
        if select_last and self.document.entries:
            target = f"entry-{len(self.document.entries) - 1}"
            self.editor_tree.selection_set(target)
            self.editor_tree.see(target)
        elif selected_index is not None and selected_index < len(self.document.entries):
            target = f"entry-{selected_index}"
            self.editor_tree.selection_set(target)
            self.editor_tree.see(target)

    def _selected_editor_index(self) -> int | None:
        if not hasattr(self, "editor_tree"):
            return None
        selection = self.editor_tree.selection()
        if not selection:
            return None
        value = selection[0]
        if not value.startswith("entry-"):
            return None
        try:
            return int(value.split("-", 1)[1])
        except ValueError:
            return None

    def _require_editor_selection(self) -> int | None:
        index = self._selected_editor_index()
        if index is None:
            messagebox.showinfo(
                "Choose a transcript line",
                "Select a line in Transcript editor first.",
            )
        return index

    def _edit_selected_entry(self) -> None:
        index = self._require_editor_selection()
        if index is None:
            return
        entry = self.document.entries[index]
        value = simpledialog.askstring(
            "Edit transcript text",
            f"Timestamp: {format_clock(entry.start)}",
            initialvalue=entry.text,
            parent=self.root,
        )
        if value is None or not value.strip():
            return
        self.document.update_entry(index, text=value)
        self._after_editor_change()

    def _set_selected_speaker(self) -> None:
        index = self._require_editor_selection()
        if index is None:
            return
        entry = self.document.entries[index]
        value = simpledialog.askstring(
            "Set speaker",
            "Enter a speaker name. Leave it blank to remove the label.",
            initialvalue=entry.speaker,
            parent=self.root,
        )
        if value is None:
            return
        self.document.update_entry(index, speaker=value)
        self._after_editor_change()

    def _quick_speaker(self, speaker: str) -> None:
        index = self._selected_editor_index()
        if index is None:
            return
        self.document.update_entry(index, speaker=speaker)
        self._after_editor_change()

    def _toggle_selected_verified(self) -> None:
        index = self._require_editor_selection()
        if index is None:
            return
        entry = self.document.entries[index]
        self.document.update_entry(index, verified=not entry.verified)
        self._after_editor_change()

    def _mark_selected_entry(self, kind: str) -> None:
        index = self._require_editor_selection()
        if index is None:
            return
        entry = self.document.entries[index]
        note = simpledialog.askstring(
            kind,
            "Optional note:",
            initialvalue="",
            parent=self.root,
        )
        if note is None:
            return
        self.document.add_marker(entry.start, kind, note)
        self._after_editor_change()
        self.activity_var.set(f"Added {kind} marker at {format_clock(entry.start)}.")

    def _play_selected_entry(self) -> None:
        if self.session is not None:
            messagebox.showinfo(
                "Live recording is active",
                "Pause or stop the live session before playing audio from the recording.",
            )
            return
        index = self._require_editor_selection()
        if index is None:
            return
        media_path = self.document.enhanced_recording_path or self.document.recording_path
        if media_path is None or not media_path.is_file():
            messagebox.showinfo(
                "Source recording unavailable",
                "The WAV, video, or audio source for this session could not be found.",
            )
            return
        entry = self.document.entries[index]
        self.activity_var.set(
            f"Playing from {format_clock(entry.start)}: {media_path.name}"
        )
        play_audio_segment(
            media_path,
            start_seconds=max(0.0, entry.start - 1.0),
            duration_seconds=8.0,
            on_error=lambda message: self.root.after(
                0,
                messagebox.showerror,
                "Could not play audio",
                message,
            ),
        )

    def _after_editor_change(self) -> None:
        self._redraw_all()
        self._refresh_editor()
        self._persist_current_document()
        if self.session is not None:
            self.recovery_manager.save(self.document, state="recording", force=True)

    # ------------------------------------------------------------------
    # Floating captions
    # ------------------------------------------------------------------
    def _toggle_caption_window(self) -> None:
        if self.caption_window is not None:
            self.caption_window.toggle()

    # ------------------------------------------------------------------
    # Session library
    # ------------------------------------------------------------------
    def _refresh_session_library(self) -> None:
        if not hasattr(self, "session_tree"):
            return
        query = self.session_search_var.get() if self.session_search_var is not None else ""
        try:
            summaries = self.session_store.search(query)
        except Exception as exc:
            self.activity_var.set(f"Session library could not be read: {exc}")
            return
        self.session_tree.delete(*self.session_tree.get_children())
        for summary in summaries:
            source = "File" if summary.source_type == "imported" else "Live"
            self.session_tree.insert(
                "",
                "end",
                iid=summary.session_id,
                values=(
                    summary.created_at.replace("T", " ")[:16],
                    source,
                    summary.title,
                    summary.language,
                    format_clock(summary.duration_seconds),
                    "Verified" if summary.finalized else "Live draft",
                ),
            )

    def _selected_session_id(self) -> str | None:
        if not hasattr(self, "session_tree"):
            return None
        selection = self.session_tree.selection()
        return selection[0] if selection else None

    def _open_selected_session(self) -> None:
        session_id = self._selected_session_id()
        if not session_id:
            messagebox.showinfo("Choose a session", "Select a saved session first.")
            return
        document = self.session_store.load(session_id)
        if document is None:
            messagebox.showwarning("Session unavailable", "That saved session could not be opened.")
            return
        self.document = document
        if self.session_title_var is not None:
            self.session_title_var.set(document.title)
        self._redraw_all()
        self._refresh_editor()
        self._set_controls_for_idle()
        self._show_page("Live Session")
        self.notebook.select("Transcript editor")
        self.activity_var.set(f"Opened saved session: {document.title}")

    def _rename_selected_session(self) -> None:
        session_id = self._selected_session_id()
        if not session_id:
            messagebox.showinfo("Choose a session", "Select a saved session first.")
            return
        document = self.session_store.load(session_id)
        if document is None:
            return
        value = simpledialog.askstring(
            "Rename session",
            "Enter a new session title:",
            initialvalue=document.title,
            parent=self.root,
        )
        if value is None or not value.strip():
            return
        self.session_store.rename(session_id, value)
        if self.document.session_id == session_id:
            self.document.title = " ".join(value.strip().split())
            if self.session_title_var is not None:
                self.session_title_var.set(self.document.title)
        self._refresh_session_library()

    def _open_selected_session_source(self) -> None:
        session_id = self._selected_session_id()
        document = self.session_store.load(session_id) if session_id else None
        path = document.recording_path if document else None
        if path is None or not path.exists():
            messagebox.showinfo("Source unavailable", "The source recording could not be found.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showinfo("Source recording", f"{path}\n\nCould not open automatically: {exc}")

    def _delete_selected_session(self) -> None:
        session_id = self._selected_session_id()
        if not session_id:
            messagebox.showinfo("Choose a session", "Select a saved session first.")
            return
        document = self.session_store.load(session_id)
        title = document.title if document else "this session"
        if not messagebox.askyesno(
            "Delete from session library",
            f"Remove “{title}” from the local session library?\n\n"
            "The original recording and exported files will not be deleted.",
        ):
            return
        self.session_store.delete(session_id)
        self._refresh_session_library()

    # ------------------------------------------------------------------
    # Export additions
    # ------------------------------------------------------------------
    def _show_export_menu(self) -> None:
        menu = tk.Menu(self.root, tearoff=False)
        menu.add_command(label="Word document (.docx)", command=self._save_docx)
        menu.add_command(label="Plain text (.txt)", command=self._save_txt)
        menu.add_command(label="Subtitles (.srt)", command=self._save_srt)
        menu.add_command(label="Web captions (.vtt)", command=self._save_vtt)
        menu.add_command(label="Spreadsheet data (.csv)", command=self._save_csv)
        menu.add_command(label="Markdown (.md)", command=self._save_markdown)
        menu.add_separator()
        menu.add_command(label="Copy transcript", command=self._copy_transcript)
        menu.add_command(label="Open recordings folder", command=self._open_recording_folder)
        x = self.export_button.winfo_rootx()
        y = self.export_button.winfo_rooty() + self.export_button.winfo_height() + 4
        menu.tk_popup(x, y)

    def _save_additional_format(self, extension: str, label: str, saver) -> None:
        if not self._ensure_content():
            return
        path = filedialog.asksaveasfilename(
            title=f"Save {label}",
            initialdir=str(EXPORT_DIR),
            initialfile=self.document.suggested_filename(extension),
            defaultextension=f".{extension}",
            filetypes=((label, f"*.{extension}"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            saver(Path(path))
        except OSError as exc:
            messagebox.showerror("Could not save transcript", str(exc))
            return
        self.activity_var.set(f"Saved {extension.upper()}: {path}")

    def _save_vtt(self) -> None:
        self._save_additional_format("vtt", "WebVTT captions", self.document.save_vtt)

    def _save_csv(self) -> None:
        self._save_additional_format("csv", "CSV file", self.document.save_csv)

    def _save_markdown(self) -> None:
        self._save_additional_format("md", "Markdown file", self.document.save_markdown)

    def _copy_transcript(self) -> None:
        if not self._ensure_content():
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(
            self.document.plain_text(include_timestamps=self.timestamps_var.get())
        )
        self.activity_var.set("Transcript copied to the clipboard.")

    # ------------------------------------------------------------------
    # Storage manager
    # ------------------------------------------------------------------
    def _open_storage_manager(self) -> None:
        if self.session is not None or self.model_loading or self.model_downloading or self.finalizing:
            messagebox.showinfo(
                "Finish the current operation",
                "Storage cleanup is available when Live Scribe is idle.",
            )
            return
        if self.storage_window is not None:
            try:
                if self.storage_window.winfo_exists():
                    self.storage_window.lift()
                    return
            except tk.TclError:
                pass

        window = ctk.CTkToplevel(self.root)
        self.storage_window = window
        window.title("Live Scribe Storage Manager")
        window.geometry("760x520")
        window.minsize(650, 430)
        window.transient(self.root)
        window.grab_set()

        ctk.CTkLabel(
            window,
            text="Portable Storage Manager",
            font=ctk.CTkFont(family=self.font_family, size=22, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(
            window,
            text=(
                "Remove unused speech models or clean stopped downloads and temporary files. "
                "Live recording parts are kept in Recordings/In Progress, while the merged WAV is saved in Recordings/Final Output. Keeping both copies uses additional space."
            ),
            justify="left",
            wraplength=700,
        ).pack(anchor="w", padx=20, pady=(0, 12))

        tree = ttk.Treeview(
            window,
            columns=("item", "size", "status"),
            show="headings",
            style="LiveScribe.Treeview",
            selectmode="browse",
        )
        tree.heading("item", text="Item")
        tree.heading("size", text="Used space")
        tree.heading("status", text="Status")
        tree.column("item", width=390, stretch=True)
        tree.column("size", width=120, anchor="e")
        tree.column("status", width=160)
        tree.pack(fill="both", expand=True, padx=20, pady=8)
        self.storage_tree = tree

        buttons = ctk.CTkFrame(window, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(4, 20))
        ctk.CTkButton(
            buttons,
            text="Remove Selected Model",
            command=self._remove_selected_model_storage,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            buttons,
            text="Clean Partial Downloads",
            command=self._clean_partial_storage,
        ).pack(side="left", padx=6)
        ctk.CTkButton(buttons, text="Clean Temporary Files", command=self._clean_temp_storage).pack(side="left", padx=6)
        ctk.CTkButton(buttons, text="Delete Completed Parts", command=self._clean_completed_recording_parts).pack(side="left", padx=6)
        ctk.CTkButton(buttons, text="Delete All In-Progress", command=self._clean_all_recording_parts, fg_color=self._color("danger"), hover_color=self._color("danger"), text_color="#FFFFFF").pack(side="left", padx=6)
        ctk.CTkButton(
            buttons,
            text="Close",
            command=window.destroy,
            fg_color="transparent",
            border_width=1,
        ).pack(side="right")

        self._refresh_storage_tree()

    def _refresh_storage_tree(self) -> None:
        if not hasattr(self, "storage_tree"):
            return
        self.storage_tree.delete(*self.storage_tree.get_children())
        for item in storage_items():
            self.storage_tree.insert(
                "",
                "end",
                iid=item.key,
                values=(item.label, format_size(item.size_bytes), item.status),
            )

    def _remove_selected_model_storage(self) -> None:
        selection = self.storage_tree.selection()
        if not selection or not selection[0].startswith("model:"):
            messagebox.showinfo("Choose a model", "Select a speech model row first.")
            return
        model_name = selection[0].split(":", 1)[1]
        if model_name not in MODEL_OPTIONS:
            return
        if not messagebox.askyesno(
            "Remove speech model",
            f"Remove {model_friendly_name(model_name)} from this portable copy?\n\n"
            "It can be downloaded again later.",
        ):
            return
        removed = remove_model(model_name)
        if self._selected_model_name() == model_name:
            self.engine = None
            self.settings.model_name = ""
            self.model_var.set(MODEL_PLACEHOLDER)
            self.settings.save()
        self._refresh_storage_tree()
        self._update_model_status()
        self._set_controls_for_idle()
        self.activity_var.set(f"Removed {format_size(removed)} of model data.")

    def _clean_partial_storage(self) -> None:
        removed = clean_partial_downloads()
        self._refresh_storage_tree()
        self.activity_var.set(
            f"Cleaned {format_size(removed)} of stopped model downloads. Recovery recording parts were preserved."
        )

    def _clean_temp_storage(self) -> None:
        removed = clean_temporary_files()
        self._refresh_storage_tree()
        self.activity_var.set(f"Cleaned {format_size(removed)} of temporary files.")

    def _clean_completed_recording_parts(self) -> None:
        if not messagebox.askyesno("Delete completed recording parts", "Delete unmerged safety parts only when a matching merged WAV already exists in Recordings/Final Output?\n\nThis frees storage without deleting the final WAV.", parent=self.storage_window):
            return
        removed = clean_completed_recording_parts()
        self._refresh_storage_tree()
        self.activity_var.set(f"Deleted {format_size(removed)} of completed in-progress audio parts.")

    def _clean_all_recording_parts(self) -> None:
        if not messagebox.askyesno("Delete all in-progress audio", "This permanently deletes every unmerged WAV part in Recordings/In Progress.\n\nUnfinished sessions that do not yet have a merged final WAV may no longer be recoverable. Final Output WAV files are not deleted.\n\nContinue?", parent=self.storage_window):
            return
        removed = clean_all_recording_parts()
        self._refresh_storage_tree()
        self.activity_var.set(f"Deleted {format_size(removed)} of in-progress recording parts.")

    # ------------------------------------------------------------------
    # Safe close
    # ------------------------------------------------------------------
    def _on_close(self) -> None:
        if not (self.model_downloading or self.model_loading or self.finalizing or self.session is not None):
            self._persist_current_document()
            if self.caption_window is not None:
                self.caption_window.destroy()
        super()._on_close()
