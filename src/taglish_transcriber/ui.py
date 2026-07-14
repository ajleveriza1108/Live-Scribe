from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from .audio import (
    detect_default_microphone_label,
    detect_default_system_audio_label,
    list_microphones,
    list_system_audio_sources,
    parse_microphone_index,
    system_audio_setup_help,
)
from .config import (
    AUDIO_SOURCE_MICROPHONE,
    AUDIO_SOURCE_OPTIONS,
    AUDIO_SOURCE_SYSTEM,
    AppSettings,
    LANGUAGE_LABEL_TO_CODE,
    MODEL_OPTIONS,
    MODEL_PLACEHOLDER,
    MODEL_SELECTION_OPTIONS,
    SENSITIVITY_THRESHOLDS,
    THEME_LIGHT,
    THEME_OLED,
    THEME_OPTIONS,
    DEFAULT_TOPIC_PROFILE_ID,
    model_display_label,
    model_friendly_name,
    model_id_from_display,
    model_long_description,
    model_short_description,
    model_size_label,
)
from .dictionary_engine import VocabularyManager
from .hardware import (
    HARDWARE_CHECK_VERSION,
    STATUS_CAUTION,
    STATUS_UNAVAILABLE,
    HardwareAssessment,
    assess_this_pc,
    save_hardware_assessment,
)
from .models import (
    ModelDownloadCancelled,
    ModelDownloadProgress,
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
from .topic_profiles import TopicProfile, TopicProfileManager
from .transcript import TranscriptDocument, TranscriptEntry, format_clock
from .ui_base import TaglishTranscriberApp as _Controller
from .vocabulary_dialog import VocabularyPronunciationDialog


COLORS = {
    "window": ("#F1EFE9", "#000000"),
    "sidebar": ("#E9E5DC", "#07090B"),
    "surface": ("#FAF8F3", "#0B0E11"),
    "surface_alt": ("#FFFFFF", "#11151A"),
    "surface_raised": ("#F5F2EB", "#171C22"),
    "border": ("#D5D0C5", "#252B33"),
    "text": ("#171717", "#F5F7FA"),
    "text_secondary": ("#625D55", "#A7B0BA"),
    "muted": ("#898278", "#6F7A86"),
    "accent": ("#147EA8", "#4CC2FF"),
    "accent_hover": ("#106B90", "#35AADB"),
    "success": ("#2E8B57", "#4DD17A"),
    "warning": ("#A76C00", "#F2B94B"),
    "danger": ("#C43D4B", "#FF5C66"),
    "disabled": ("#C9C5BC", "#30363D"),
}


class ModernTabView(ctk.CTkTabview):
    """CTk tab view with the select(index) compatibility used by the controller."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ordered_tabs: list[str] = []

    def add(self, name: str):
        if name not in self._ordered_tabs:
            self._ordered_tabs.append(name)
        return super().add(name)

    def select(self, value: int | str) -> None:
        if isinstance(value, int):
            if 0 <= value < len(self._ordered_tabs):
                self.set(self._ordered_tabs[value])
            return
        self.set(value)


class TaglishTranscriberApp(_Controller):
    """Modern minimal interface over the proven Live Scribe controller."""

    def __init__(self) -> None:
        ensure_app_directories()
        self.settings = AppSettings.load()
        self.first_run_hardware_notice = (
            not self.settings.hardware_check_completed
            or self.settings.hardware_check_version < HARDWARE_CHECK_VERSION
        )
        self.hardware_assessment = assess_this_pc()
        save_hardware_assessment(self.hardware_assessment)

        selected_hardware_model = self.settings.model_name
        if (
            selected_hardware_model
            and not is_model_downloaded(selected_hardware_model)
            and not self.hardware_assessment.capability(selected_hardware_model).download_allowed
        ):
            selected_hardware_model = ""
            self.settings.model_name = ""

        ctk.set_default_color_theme("blue")
        ctk.set_appearance_mode("Dark" if self.settings.theme_name == THEME_OLED else "Light")

        self.root = ctk.CTk(fg_color=COLORS["window"])
        self.root.title("Live Scribe")
        self.root.geometry("1280x820")
        self.root.minsize(1020, 680)

        self.document = TranscriptDocument()
        self.engine: WhisperEngine | None = None
        self.session: LiveTranscriptionSession | None = None
        self.model_loading = False
        self.model_downloading = False
        self.model_download_cancel_event = threading.Event()
        self.finalizing = False
        self.last_error_message = ""
        self.selected_microphone_name = self.settings.microphone_label
        self.selected_audio_input_name = self.settings.microphone_label
        self.topic_manager = TopicProfileManager()
        selected_topic = self.topic_manager.get(self.settings.topic_profile_id)
        if selected_topic is None:
            selected_topic = self.topic_manager.default_profile
            self.settings.topic_profile_id = selected_topic.id

        self.audio_source_var = tk.StringVar(value=self.settings.audio_source_mode)
        self.audio_input_label_var = tk.StringVar(value="Microphone")
        self.model_var = tk.StringVar(
            value=(
                model_display_label(selected_hardware_model)
                if selected_hardware_model in MODEL_OPTIONS
                else MODEL_PLACEHOLDER
            )
        )
        self.language_var = tk.StringVar(value=self.settings.language_label)
        self.microphone_var = tk.StringVar(value=self.settings.microphone_label)
        self.device_var = tk.StringVar(value=self.settings.device_mode)
        self.sensitivity_var = tk.StringVar(value=self.settings.sensitivity_label)
        self.timestamps_var = tk.BooleanVar(value=self.settings.include_timestamps)
        self.noise_reduction_var = tk.BooleanVar(value=self.settings.noise_reduction)
        self.review_var = tk.BooleanVar(value=self.settings.grammar_diction_comments)
        self.live_appendix_var = tk.BooleanVar(value=self.settings.include_live_appendix)
        self.theme_var = tk.StringVar(value=self.settings.theme_name)
        self.topic_var = tk.StringVar(value=selected_topic.name)
        self.topic_summary_var = tk.StringVar(value="")
        self.topic_editor_profile_var = tk.StringVar(value=selected_topic.name)
        self.topic_name_var = tk.StringVar(value=selected_topic.name)
        self.topic_editor_selected_id: str | None = selected_topic.id
        self.status_var = tk.StringVar(value="Ready")
        self.activity_var = tk.StringVar(
            value="Choose and download one speech quality option before the first session."
        )
        self.model_status_var = tk.StringVar(value=model_status(self.settings.model_name))
        self.recording_var = tk.StringVar(value="WAV not started")
        self.download_progress_value = tk.DoubleVar(value=0.0)
        self.download_progress_text_var = tk.StringVar(value="")
        self.model_summary_var = tk.StringVar(value="Choose a speech quality option.")
        self.hardware_summary_var = tk.StringVar(value=self.hardware_assessment.snapshot.summary())
        self.hardware_recommendation_var = tk.StringVar(value="")
        self.hardware_compatibility_var = tk.StringVar(value="")

        self.font_family = self._system_font_family()
        self.pages: dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.text_widgets: list[tk.Text] = []
        self.current_page = "Live Session"

        self._configure_style()
        self._build_ui()
        self._refresh_audio_inputs(auto_select=True)
        self._refresh_topic_options(select_id=selected_topic.id, load_editor=True)
        self._refresh_hardware_advice(update_selector=True)
        self._update_model_summary()
        self._update_model_status()
        self._set_controls_for_idle()
        self._apply_text_theme()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(self.POLL_INTERVAL_MS, self._poll_session_events)
        if self.first_run_hardware_notice:
            self.root.after(500, self._show_first_run_hardware_notice)

        selected_model = self._selected_model_name()
        selected_unavailable = bool(
            selected_model
            and self.hardware_assessment.capability(selected_model).status == STATUS_UNAVAILABLE
        )
        if not self.settings.model_name or selected_unavailable:
            self._show_page("Models")
        else:
            self._show_page("Live Session")

    @staticmethod
    def _system_font_family() -> str:
        if sys.platform == "win32":
            return "Segoe UI"
        if sys.platform == "darwin":
            return "Helvetica Neue"
        return "DejaVu Sans"

    def _configure_style(self) -> None:
        self.root.option_add("*Font", (self.font_family, 10))

    def _build_ui(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(
            self.root,
            width=218,
            corner_radius=0,
            fg_color=COLORS["sidebar"],
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="Live Scribe",
            font=ctk.CTkFont(family=self.font_family, size=24, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(26, 4))
        ctk.CTkLabel(
            self.sidebar,
            text="Offline AI transcription",
            font=ctk.CTkFont(family=self.font_family, size=12),
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 24))

        nav_items = (
            ("Live Session", "●"),
            ("Vocabulary", "Aa"),
            ("Topics", "◎"),
            ("Models", "↓"),
            ("Settings", "⚙"),
        )
        for index, (name, icon) in enumerate(nav_items, start=2):
            button = ctk.CTkButton(
                self.sidebar,
                text=f"{icon}   {name}",
                command=lambda page=name: self._show_page(page),
                height=42,
                corner_radius=9,
                anchor="w",
                fg_color="transparent",
                hover_color=COLORS["surface_raised"],
                text_color=COLORS["text_secondary"],
                font=ctk.CTkFont(family=self.font_family, size=14, weight="bold"),
            )
            button.grid(row=index, column=0, sticky="ew", padx=14, pady=3)
            self.nav_buttons[name] = button

        theme_holder = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        theme_holder.grid(row=8, column=0, sticky="sew", padx=16, pady=(12, 10))
        theme_holder.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            theme_holder,
            text="Appearance",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(0, 6))
        self.theme_menu = ctk.CTkOptionMenu(
            theme_holder,
            variable=self.theme_var,
            values=list(THEME_OPTIONS),
            command=self._change_theme,
            height=36,
            corner_radius=8,
            fg_color=COLORS["surface_raised"],
            button_color=COLORS["surface_raised"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
        )
        self.theme_menu.grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(
            self.sidebar,
            text="Version 0.6.1",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(family=self.font_family, size=10),
        ).grid(row=9, column=0, sticky="w", padx=22, pady=(0, 18))

        self.main_shell = ctk.CTkFrame(
            self.root,
            corner_radius=0,
            fg_color=COLORS["window"],
        )
        self.main_shell.grid(row=0, column=1, sticky="nsew")
        self.main_shell.grid_rowconfigure(0, weight=1)
        self.main_shell.grid_columnconfigure(0, weight=1)

        self._build_live_page()
        self._build_vocabulary_page()
        self._build_topics_page()
        self._build_models_page()
        self._build_settings_page()

    def _page_frame(self, name: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_shell, fg_color=COLORS["window"], corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        self.pages[name] = frame
        return frame

    def _page_header(self, parent, title: str, subtitle: str) -> None:
        ctk.CTkLabel(
            parent,
            text=title,
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=26, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            parent,
            text=subtitle,
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=12),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

    def _card(self, parent, **grid_options):
        frame = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=12,
        )
        frame.grid(**grid_options)
        return frame

    def _build_live_page(self) -> None:
        page = self._page_frame("Live Session")
        page.grid_rowconfigure(3, weight=1)
        page.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 14))
        header.grid_columnconfigure(0, weight=1)
        self._page_header(
            header,
            "Live Session",
            "Transcribe a microphone or computer livestream and keep the original WAV.",
        )
        self.status_chip = ctk.CTkLabel(
            header,
            textvariable=self.status_var,
            fg_color=COLORS["surface_raised"],
            text_color=COLORS["text_secondary"],
            corner_radius=16,
            height=32,
            padx=14,
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        )
        self.status_chip.grid(row=0, column=1, rowspan=2, sticky="e")

        self.notice_frame = ctk.CTkFrame(
            page,
            fg_color=COLORS["surface_raised"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=10,
        )
        self.notice_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        self.notice_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            self.notice_frame,
            text="i",
            width=28,
            height=28,
            corner_radius=14,
            fg_color=COLORS["accent"],
            text_color=("#FFFFFF", "#001219"),
            font=ctk.CTkFont(family=self.font_family, size=14, weight="bold"),
        ).grid(row=0, column=0, padx=(12, 10), pady=10)
        self.notice_message_label = ctk.CTkLabel(
            self.notice_frame,
            text=(
                "AI transcription may contain errors. Verify important names, numbers, dates, "
                "quotations, and uncommon words against the saved WAV recording."
            ),
            justify="left",
            anchor="w",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=12),
        )
        self.notice_message_label.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=10)
        self.notice_frame.bind("<Configure>", self._update_notice_wraplength)

        input_card = self._card(page, row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        input_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            input_card,
            text="Input",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(14, 10))
        self.audio_source_combo = ctk.CTkComboBox(
            input_card,
            variable=self.audio_source_var,
            values=list(AUDIO_SOURCE_OPTIONS),
            command=self._on_audio_source_selected,
            state="readonly",
            height=38,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            button_color=COLORS["surface_raised"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
        )
        self.audio_source_combo.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=(0, 16))
        self.microphone_combo = ctk.CTkComboBox(
            input_card,
            variable=self.microphone_var,
            values=["Default input"],
            state="readonly",
            height=38,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            button_color=COLORS["surface_raised"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
        )
        self.microphone_combo.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 16))
        self.detect_button = ctk.CTkButton(
            input_card,
            text="Detect",
            command=lambda: self._refresh_audio_inputs(auto_select=True),
            width=88,
            height=38,
            corner_radius=8,
            fg_color=COLORS["surface_raised"],
            hover_color=COLORS["border"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
        )
        self.detect_button.grid(row=1, column=2, padx=(8, 16), pady=(0, 10))

        ctk.CTkLabel(
            input_card,
            text="Topic profile",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(0, 6))
        self.topic_combo = ctk.CTkComboBox(
            input_card,
            variable=self.topic_var,
            values=list(self.topic_manager.names),
            command=self._on_topic_selected,
            state="readonly",
            height=38,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            button_color=COLORS["surface_raised"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
        )
        self.topic_combo.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(16, 8), pady=(0, 6))
        self.manage_topics_button = ctk.CTkButton(
            input_card,
            text="Manage Topics",
            command=lambda: self._show_page("Topics"),
            width=126,
            height=38,
            corner_radius=8,
            fg_color=COLORS["surface_raised"],
            hover_color=COLORS["border"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
        )
        self.manage_topics_button.grid(row=3, column=2, padx=(8, 16), pady=(0, 6))
        ctk.CTkLabel(
            input_card,
            textvariable=self.topic_summary_var,
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
            wraplength=900,
            font=ctk.CTkFont(family=self.font_family, size=11),
        ).grid(row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 14))

        transcript_card = self._card(page, row=3, column=0, sticky="nsew", padx=24, pady=(0, 12))
        transcript_card.grid_rowconfigure(1, weight=1)
        transcript_card.grid_columnconfigure(0, weight=1)
        status_row = ctk.CTkFrame(transcript_card, fg_color="transparent")
        status_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        status_row.grid_columnconfigure(1, weight=1)
        self.recording_dot = ctk.CTkLabel(
            status_row,
            text="●",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(family=self.font_family, size=13),
        )
        self.recording_dot.grid(row=0, column=0, padx=(0, 8))
        ctk.CTkLabel(
            status_row,
            textvariable=self.recording_var,
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=0, column=1, sticky="w")

        self.notebook = ModernTabView(
            transcript_card,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["surface_raised"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["surface_raised"],
            segmented_button_unselected_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=8,
        )
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.live_text = self._create_text_tab("Live transcript")
        self.final_text = self._create_text_tab("Final transcript")
        self.review_text = self._create_text_tab("Review comments")

        action_bar = self._card(page, row=4, column=0, sticky="ew", padx=24, pady=(0, 12))
        action_bar.grid_columnconfigure(7, weight=1)
        self.start_button = ctk.CTkButton(
            action_bar,
            text="Start Listening",
            command=self._start_requested,
            height=42,
            corner_radius=9,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=("#FFFFFF", "#001219"),
            font=ctk.CTkFont(family=self.font_family, size=13, weight="bold"),
        )
        self.start_button.grid(row=0, column=0, padx=(12, 6), pady=12)
        self.stop_button = ctk.CTkButton(
            action_bar,
            text="Stop & Save WAV",
            command=self._stop_requested,
            state="disabled",
            height=42,
            corner_radius=9,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger"],
            text_color="#FFFFFF",
        )
        self.stop_button.grid(row=0, column=1, padx=6, pady=12)
        self.verify_wav_button = ctk.CTkButton(
            action_bar,
            text="Verify from WAV",
            command=self._verify_wav_requested,
            state="disabled",
            height=42,
            corner_radius=9,
            fg_color=COLORS["success"],
            hover_color=COLORS["success"],
            text_color="#FFFFFF",
        )
        self.verify_wav_button.grid(row=0, column=2, padx=6, pady=12)
        self.clear_button = ctk.CTkButton(
            action_bar,
            text="New Session",
            command=self._clear_transcript,
            height=42,
            corner_radius=9,
            fg_color="transparent",
            hover_color=COLORS["surface_raised"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
        )
        self.clear_button.grid(row=0, column=3, padx=6, pady=12)
        self.export_button = ctk.CTkButton(
            action_bar,
            text="Export ▾",
            command=self._show_export_menu,
            height=42,
            corner_radius=9,
            fg_color="transparent",
            hover_color=COLORS["surface_raised"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
        )
        self.export_button.grid(row=0, column=4, padx=6, pady=12)
        self.recording_folder_button = ctk.CTkButton(
            action_bar,
            text="Recordings",
            command=self._open_recording_folder,
            height=42,
            corner_radius=9,
            fg_color="transparent",
            hover_color=COLORS["surface_raised"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
        )
        self.recording_folder_button.grid(row=0, column=5, padx=6, pady=12)

        footer = ctk.CTkFrame(page, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=28, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            textvariable=self.activity_var,
            text_color=COLORS["text_secondary"],
            anchor="w",
            justify="left",
            font=ctk.CTkFont(family=self.font_family, size=11),
        ).grid(row=0, column=0, sticky="ew")

    def _build_vocabulary_page(self) -> None:
        page = self._page_frame("Vocabulary")
        page.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 18))
        self._page_header(
            header,
            "Vocabulary Manager",
            "Add, edit, or remove difficult names, places, acronyms, and technical terms.",
        )

        card = self._card(page, row=1, column=0, sticky="ew", padx=28, pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text="Improve difficult words without installing another AI model",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=17, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 8))
        ctk.CTkLabel(
            card,
            text=(
                "Add a correct spelling and the ways a term may sound. Select a saved entry to edit or remove it. "
                "Entries become local recognition hints and controlled final-pass corrections. The original WAV remains the evidence."
            ),
            wraplength=760,
            justify="left",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=13),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))
        ctk.CTkButton(
            card,
            text="Open Vocabulary Manager",
            command=self._open_vocabulary_dialog,
            height=42,
            corner_radius=9,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=("#FFFFFF", "#001219"),
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(0, 20))

        tips = self._card(page, row=2, column=0, sticky="ew", padx=28, pady=(0, 14))
        tips.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            tips,
            text="Best entries",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 8))
        ctk.CTkLabel(
            tips,
            text=(
                "• Personal and organization names\n"
                "• Barangays, cities, and local place names\n"
                "• Acronyms and product names\n"
                "• Church, legal, medical, and technical terminology\n\n"
                "Avoid very short aliases such as ‘a’, ‘in’, ‘no’, and ‘to’."
            ),
            justify="left",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=13),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))


    def _build_topics_page(self) -> None:
        page = self._page_frame("Topics")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 18))
        self._page_header(
            header,
            "Topic Profiles",
            "Give the current speech model helpful context—no extra LLM or model download required.",
        )

        info = self._card(page, row=1, column=0, sticky="ew", padx=28, pady=(0, 14))
        info.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            info,
            text="Select a starter topic or create your own",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 6))
        ctk.CTkLabel(
            info,
            text=(
                "A topic profile supplies a short description and important terms to Faster-Whisper. "
                "It can improve recognition of expected names and terminology, but it does not replace WAV verification. "
                "All profiles are stored locally and may be added, edited, or removed."
            ),
            wraplength=920,
            justify="left",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=12),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))

        editor = self._card(page, row=2, column=0, sticky="nsew", padx=28, pady=(0, 24))
        editor.grid_columnconfigure(0, weight=1)
        editor.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(
            editor,
            text="Saved topic profile",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 6))
        self.topic_editor_combo = ctk.CTkComboBox(
            editor,
            variable=self.topic_editor_profile_var,
            values=list(self.topic_manager.names),
            command=self._on_topic_editor_selected,
            state="readonly",
            height=40,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            button_color=COLORS["surface_raised"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
        )
        self.topic_editor_combo.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 14))

        ctk.CTkLabel(
            editor,
            text="Profile name",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(0, 6))
        self.topic_name_entry = ctk.CTkEntry(
            editor,
            textvariable=self.topic_name_var,
            height=40,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            placeholder_text="Example: Weekly Inventory Meeting",
        )
        self.topic_name_entry.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 14))

        fields = ctk.CTkFrame(editor, fg_color="transparent")
        fields.grid(row=4, column=0, sticky="nsew", padx=20, pady=(0, 14))
        fields.grid_columnconfigure((0, 1), weight=1)
        fields.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            fields,
            text="What is this recording about?",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ctk.CTkLabel(
            fields,
            text="Important names and words",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 6))

        self.topic_description_text = ctk.CTkTextbox(
            fields,
            height=150,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
            wrap="word",
        )
        self.topic_description_text.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self.topic_terms_text = ctk.CTkTextbox(
            fields,
            height=150,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
            wrap="word",
        )
        self.topic_terms_text.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(
            fields,
            text="Use a short description. Do not paste the full speech or manuscript.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(family=self.font_family, size=10),
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))
        ctk.CTkLabel(
            fields,
            text="Enter one term per line, or separate terms with commas.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(family=self.font_family, size=10),
        ).grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(6, 0))

        buttons = ctk.CTkFrame(editor, fg_color="transparent")
        buttons.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.topic_add_button = ctk.CTkButton(
            buttons,
            text="Add New",
            command=self._add_topic_profile,
            height=40,
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=("#FFFFFF", "#001219"),
        )
        self.topic_add_button.grid(row=0, column=0, padx=(0, 6))
        self.topic_save_button = ctk.CTkButton(
            buttons,
            text="Save Changes",
            command=self._save_topic_profile,
            height=40,
            corner_radius=8,
            fg_color=COLORS["success"],
            hover_color=COLORS["success"],
            text_color="#FFFFFF",
        )
        self.topic_save_button.grid(row=0, column=1, padx=6)
        self.topic_remove_button = ctk.CTkButton(
            buttons,
            text="Remove Selected",
            command=self._remove_topic_profile,
            height=40,
            corner_radius=8,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger"],
            text_color="#FFFFFF",
        )
        self.topic_remove_button.grid(row=0, column=2, padx=6)
        self.topic_clear_button = ctk.CTkButton(
            buttons,
            text="Clear Form",
            command=self._clear_topic_form,
            height=40,
            corner_radius=8,
            fg_color="transparent",
            hover_color=COLORS["surface_raised"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
        )
        self.topic_clear_button.grid(row=0, column=3, padx=6)
    def _build_models_page(self) -> None:
        page = self._page_frame("Models")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 18))
        self._page_header(
            header,
            "Speech Quality",
            "Live Scribe checks this computer before offering model downloads.",
        )

        hardware_card = self._card(page, row=1, column=0, sticky="ew", padx=28, pady=(0, 14))
        hardware_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            hardware_card,
            text="This PC",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 5))
        ctk.CTkLabel(
            hardware_card,
            textvariable=self.hardware_summary_var,
            text_color=COLORS["text_secondary"],
            justify="left",
            anchor="w",
            wraplength=860,
            font=ctk.CTkFont(family=self.font_family, size=12),
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 5))
        ctk.CTkLabel(
            hardware_card,
            textvariable=self.hardware_recommendation_var,
            text_color=COLORS["text"],
            justify="left",
            anchor="w",
            wraplength=860,
            font=ctk.CTkFont(family=self.font_family, size=12, weight="bold"),
        ).grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 18))
        self.recheck_pc_button = ctk.CTkButton(
            hardware_card,
            text="Check This PC Again",
            command=self._recheck_this_pc,
            width=160,
            height=38,
            corner_radius=8,
            fg_color=COLORS["surface_raised"],
            hover_color=COLORS["border"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
        )
        self.recheck_pc_button.grid(row=0, column=1, rowspan=3, sticky="e", padx=20, pady=18)

        choose_card = self._card(page, row=2, column=0, sticky="ew", padx=28, pady=(0, 14))
        choose_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            choose_card,
            text="Choose speech quality",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 8))
        self.model_combo = ctk.CTkComboBox(
            choose_card,
            variable=self.model_var,
            values=list(self._hardware_model_selection_options()),
            command=self._on_model_selected,
            state="readonly",
            height=42,
            corner_radius=9,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            button_color=COLORS["surface_raised"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=13),
        )
        self.model_combo.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            choose_card,
            textvariable=self.model_summary_var,
            wraplength=880,
            justify="left",
            anchor="w",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=13),
        ).grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        ctk.CTkLabel(
            choose_card,
            textvariable=self.model_status_var,
            text_color=COLORS["muted"],
            anchor="w",
            justify="left",
            wraplength=880,
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.download_model_button = ctk.CTkButton(
            choose_card,
            text="Download Selected Quality",
            command=self._download_model_requested,
            height=42,
            corner_radius=9,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=("#FFFFFF", "#001219"),
            font=ctk.CTkFont(family=self.font_family, size=13, weight="bold"),
        )
        self.download_model_button.grid(row=4, column=0, sticky="w", padx=20, pady=(0, 20))

        self.download_progress_frame = self._card(
            page, row=3, column=0, sticky="ew", padx=28, pady=(0, 14)
        )
        self.download_progress_frame.grid_columnconfigure(0, weight=1)
        self.download_progress_title = ctk.CTkLabel(
            self.download_progress_frame,
            text="Downloading speech quality",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=15, weight="bold"),
        )
        self.download_progress_title.grid(
            row=0, column=0, sticky="w", padx=(20, 10), pady=(18, 10)
        )
        self.stop_download_button = ctk.CTkButton(
            self.download_progress_frame,
            text="Stop Download",
            command=self._stop_model_download_requested,
            width=130,
            height=34,
            corner_radius=8,
            fg_color=COLORS["danger"],
            hover_color=("#A83440", "#D94852"),
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=self.font_family, size=12, weight="bold"),
        )
        self.stop_download_button.grid(
            row=0, column=1, sticky="e", padx=(10, 20), pady=(14, 8)
        )
        self.download_progress_bar = ctk.CTkProgressBar(
            self.download_progress_frame,
            variable=self.download_progress_value,
            mode="determinate",
            height=12,
            corner_radius=6,
            progress_color=COLORS["accent"],
            fg_color=COLORS["surface_raised"],
        )
        self.download_progress_bar.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=20
        )
        ctk.CTkLabel(
            self.download_progress_frame,
            textvariable=self.download_progress_text_var,
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=12),
        ).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=20, pady=(8, 18)
        )
        self.download_progress_frame.grid_remove()

        compatibility = self._card(
            page, row=4, column=0, sticky="nsew", padx=28, pady=(0, 24)
        )
        compatibility.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            compatibility,
            text="Availability on this PC",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 8))
        ctk.CTkLabel(
            compatibility,
            text=(
                "✓ Recommended    ! May run slowly or could not be fully confirmed    "
                "× Unavailable for download"
            ),
            text_color=COLORS["muted"],
            justify="left",
            anchor="w",
            wraplength=900,
            font=ctk.CTkFont(family=self.font_family, size=11),
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        ctk.CTkLabel(
            compatibility,
            textvariable=self.hardware_compatibility_var,
            text_color=COLORS["text_secondary"],
            justify="left",
            anchor="nw",
            wraplength=920,
            font=ctk.CTkFont(family=self.font_family, size=12),
        ).grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 18))

    def _build_settings_page(self) -> None:
        page = self._page_frame("Settings")
        page.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 18))
        self._page_header(
            header,
            "Settings",
            "Language, processing, transcript display, and WAV verification preferences.",
        )

        session_card = self._card(page, row=1, column=0, sticky="ew", padx=28, pady=(0, 14))
        session_card.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(
            session_card,
            text="Session settings",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(18, 12))
        self.language_combo = self._modern_labeled_combo(
            session_card, 0, "Language", self.language_var, tuple(LANGUAGE_LABEL_TO_CODE)
        )
        self.device_combo = self._modern_labeled_combo(
            session_card, 1, "Processor", self.device_var, ("Auto", "CPU", "NVIDIA GPU")
        )
        self.sensitivity_combo = self._modern_labeled_combo(
            session_card, 2, "Audio sensitivity", self.sensitivity_var, tuple(SENSITIVITY_THRESHOLDS)
        )

        verify_card = self._card(page, row=2, column=0, sticky="ew", padx=28, pady=(0, 14))
        verify_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            verify_card,
            text="WAV verification",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            verify_card,
            text=(
                "Stop saves the original WAV and live transcript. Verify from WAV runs the separate "
                "full-recording accuracy pass when you choose."
            ),
            wraplength=800,
            justify="left",
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))
        self.noise_switch = ctk.CTkSwitch(
            verify_card,
            text="Reduce steady background noise",
            variable=self.noise_reduction_var,
            progress_color=COLORS["accent"],
            text_color=COLORS["text"],
        )
        self.noise_switch.grid(row=2, column=0, sticky="w", padx=20, pady=7)
        self.review_switch = ctk.CTkSwitch(
            verify_card,
            text="Add grammar and diction comments (English, Filipino, and Taglish)",
            variable=self.review_var,
            progress_color=COLORS["accent"],
            text_color=COLORS["text"],
        )
        self.review_switch.grid(row=3, column=0, sticky="w", padx=20, pady=7)
        self.appendix_switch = ctk.CTkSwitch(
            verify_card,
            text="Include the live transcript appendix in Word exports",
            variable=self.live_appendix_var,
            progress_color=COLORS["accent"],
            text_color=COLORS["text"],
        )
        self.appendix_switch.grid(row=4, column=0, sticky="w", padx=20, pady=7)
        self.timestamps_switch = ctk.CTkSwitch(
            verify_card,
            text="Show timestamps in the transcript",
            variable=self.timestamps_var,
            command=self._redraw_all,
            progress_color=COLORS["accent"],
            text_color=COLORS["text"],
        )
        self.timestamps_switch.grid(row=5, column=0, sticky="w", padx=20, pady=(7, 20))

        language_card = self._card(page, row=3, column=0, sticky="ew", padx=28, pady=(0, 16))
        language_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            language_card,
            text="Supported language modes",
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=self.font_family, size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 8))
        ctk.CTkLabel(
            language_card,
            text=(
                "English • Filipino / Tagalog • Taglish • Spanish • French • German • Italian • "
                "Portuguese • Dutch\n\nThe same downloaded multilingual speech model handles all supported languages."
            ),
            justify="left",
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))

    def _modern_labeled_combo(self, parent, column, label, variable, values):
        holder = ctk.CTkFrame(parent, fg_color="transparent")
        holder.grid(row=1, column=column, sticky="ew", padx=(20 if column == 0 else 8, 20 if column == 2 else 8), pady=(0, 20))
        holder.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            holder,
            text=label,
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        combo = ctk.CTkComboBox(
            holder,
            variable=variable,
            values=list(values),
            state="readonly",
            height=40,
            corner_radius=8,
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            button_color=COLORS["surface_raised"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
        )
        combo.grid(row=1, column=0, sticky="ew")
        return combo

    def _create_text_tab(self, title: str) -> tk.Text:
        frame = self.notebook.add(title)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        text = tk.Text(
            frame,
            wrap="word",
            font=(self.font_family, 12),
            padx=16,
            pady=14,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            undo=True,
        )
        text.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        text.tag_configure("timestamp", foreground="#78838E")
        text.tag_configure("heading", font=(self.font_family, 11, "bold"), spacing1=8, spacing3=3)
        text.tag_configure("body", spacing1=3, spacing3=7)
        text.tag_configure("note", foreground="#78838E", spacing3=8)
        self.text_widgets.append(text)
        return text

    def _label_and_combo(self, parent, column, label, variable, values, width):
        return self._modern_labeled_combo(parent, column, label, variable, values)

    def _show_page(self, name: str) -> None:
        frame = self.pages.get(name)
        if frame is None:
            return
        frame.tkraise()
        self.current_page = name
        for page_name, button in self.nav_buttons.items():
            active = page_name == name
            button.configure(
                fg_color=COLORS["surface_raised"] if active else "transparent",
                text_color=COLORS["text"] if active else COLORS["text_secondary"],
            )

    def _change_theme(self, value: str) -> None:
        theme = value if value in THEME_OPTIONS else THEME_OLED
        self.theme_var.set(theme)
        ctk.set_appearance_mode("Dark" if theme == THEME_OLED else "Light")
        self.settings.theme_name = theme
        self.settings.save()
        self.root.after(20, self._apply_text_theme)

    def _apply_text_theme(self) -> None:
        dark = self.theme_var.get() == THEME_OLED
        background = "#0B0E11" if dark else "#FFFFFF"
        foreground = "#F5F7FA" if dark else "#171717"
        selection = "#184A5F" if dark else "#BDE7F7"
        timestamp = "#7E8995" if dark else "#766F65"
        note = "#8C97A3" if dark else "#746E65"
        for widget in self.text_widgets:
            widget.configure(
                background=background,
                foreground=foreground,
                insertbackground=foreground,
                selectbackground=selection,
                selectforeground=foreground,
            )
            widget.tag_configure("timestamp", foreground=timestamp)
            widget.tag_configure("note", foreground=note)

    def _update_notice_wraplength(self, event=None) -> None:
        width = getattr(event, "width", None) if event is not None else None
        if not width:
            width = self.notice_frame.winfo_width() if hasattr(self, "notice_frame") else 800
        self.notice_message_label.configure(wraplength=max(320, int(width) - 74))


    def _selected_topic_profile(self) -> TopicProfile:
        profile = self.topic_manager.get_by_name(self.topic_var.get())
        return profile or self.topic_manager.default_profile

    def _refresh_topic_options(
        self,
        *,
        select_id: str | None = None,
        load_editor: bool = False,
    ) -> None:
        self.topic_manager.reload()
        profiles = self.topic_manager.profiles
        names = [profile.name for profile in profiles]
        if hasattr(self, "topic_combo"):
            self.topic_combo.configure(values=names)
        if hasattr(self, "topic_editor_combo"):
            self.topic_editor_combo.configure(values=names)

        selected = self.topic_manager.get(select_id or self.settings.topic_profile_id)
        if selected is None:
            selected = self.topic_manager.get_by_name(self.topic_var.get())
        if selected is None:
            selected = self.topic_manager.default_profile

        self.topic_var.set(selected.name)
        self.settings.topic_profile_id = selected.id
        self.settings.save()
        self._update_topic_summary(selected)

        if load_editor or self.topic_editor_selected_id is None:
            self._load_topic_editor(selected)

    def _update_topic_summary(self, profile: TopicProfile | None = None) -> None:
        selected = profile or self._selected_topic_profile()
        term_count = len(selected.important_terms)
        suffix = f"{term_count} saved important term" + ("" if term_count == 1 else "s")
        self.topic_summary_var.set(f"{selected.description}  •  {suffix}")

    def _on_topic_selected(self, choice: str | None = None) -> None:
        profile = self.topic_manager.get_by_name(choice or self.topic_var.get())
        if profile is None:
            profile = self.topic_manager.default_profile
        self.topic_var.set(profile.name)
        self.settings.topic_profile_id = profile.id
        self.settings.save()
        self._update_topic_summary(profile)

    def _on_topic_editor_selected(self, choice: str | None = None) -> None:
        profile = self.topic_manager.get_by_name(choice or self.topic_editor_profile_var.get())
        if profile is not None:
            self._load_topic_editor(profile)

    def _load_topic_editor(self, profile: TopicProfile) -> None:
        self.topic_editor_selected_id = profile.id
        self.topic_editor_profile_var.set(profile.name)
        self.topic_name_var.set(profile.name)
        if hasattr(self, "topic_description_text"):
            self.topic_description_text.delete("1.0", "end")
            self.topic_description_text.insert("1.0", profile.description)
        if hasattr(self, "topic_terms_text"):
            self.topic_terms_text.delete("1.0", "end")
            self.topic_terms_text.insert("1.0", "\n".join(profile.important_terms))

    def _topic_form_values(self) -> tuple[str, str, str]:
        return (
            self.topic_name_var.get(),
            self.topic_description_text.get("1.0", "end").strip(),
            self.topic_terms_text.get("1.0", "end").strip(),
        )

    def _clear_topic_form(self) -> None:
        self.topic_editor_selected_id = None
        self.topic_editor_profile_var.set("")
        self.topic_name_var.set("")
        self.topic_description_text.delete("1.0", "end")
        self.topic_terms_text.delete("1.0", "end")
        self.topic_name_entry.focus_set()

    def _add_topic_profile(self) -> None:
        if self.session is not None or self.model_loading or self.finalizing:
            messagebox.showinfo(
                "Session is active",
                "Finish the active transcription or verification before changing topic profiles.",
            )
            return
        name, description, terms = self._topic_form_values()
        try:
            profile = self.topic_manager.add(name, description, terms)
        except ValueError as exc:
            messagebox.showwarning("Topic profile not saved", str(exc))
            return
        self.topic_editor_selected_id = profile.id
        self._refresh_topic_options(select_id=profile.id, load_editor=True)
        self.activity_var.set(f"Topic profile added: {profile.name}")

    def _save_topic_profile(self) -> None:
        if self.topic_editor_selected_id is None:
            messagebox.showinfo(
                "Choose a saved topic",
                "Select a saved topic profile to edit, or use Add New to create one.",
            )
            return
        if self.session is not None or self.model_loading or self.finalizing:
            messagebox.showinfo(
                "Session is active",
                "Finish the active transcription or verification before changing topic profiles.",
            )
            return
        name, description, terms = self._topic_form_values()
        try:
            profile = self.topic_manager.update(
                self.topic_editor_selected_id,
                name,
                description,
                terms,
            )
        except ValueError as exc:
            messagebox.showwarning("Topic profile not saved", str(exc))
            return
        self._refresh_topic_options(select_id=profile.id, load_editor=True)
        self.activity_var.set(f"Topic profile updated: {profile.name}")

    def _remove_topic_profile(self) -> None:
        profile = self.topic_manager.get(self.topic_editor_selected_id)
        if profile is None:
            messagebox.showinfo("Choose a topic", "Select a saved topic profile first.")
            return
        if self.session is not None or self.model_loading or self.finalizing:
            messagebox.showinfo(
                "Session is active",
                "Finish the active transcription or verification before removing topic profiles.",
            )
            return
        if not messagebox.askyesno(
            "Remove topic profile",
            f"Remove “{profile.name}” from this portable copy of Live Scribe?",
        ):
            return
        try:
            self.topic_manager.remove(profile.id)
        except ValueError as exc:
            messagebox.showwarning("Topic profile not removed", str(exc))
            return
        next_profile = self.topic_manager.default_profile
        self.topic_editor_selected_id = next_profile.id
        self._refresh_topic_options(select_id=next_profile.id, load_editor=True)
        self.activity_var.set(f"Topic profile removed: {profile.name}")

    def _topic_context_for_session(self) -> tuple[str, list[str]]:
        profile = self._selected_topic_profile()
        self.settings.topic_profile_id = profile.id
        return profile.context_prompt(), profile.terms_for_recognition()
    def _hardware_model_selection_options(self) -> tuple[str, ...]:
        labels: list[str] = [MODEL_PLACEHOLDER]
        for model_name in MODEL_OPTIONS:
            capability = self.hardware_assessment.capability(model_name)
            if capability.download_allowed or is_model_downloaded(model_name):
                labels.append(model_display_label(model_name))
        return tuple(labels)

    def _refresh_hardware_advice(self, *, update_selector: bool) -> None:
        assessment = self.hardware_assessment
        self.hardware_summary_var.set(assessment.snapshot.summary())
        recommended_name = model_friendly_name(assessment.recommended_model)
        maximum = assessment.capability("large-v3")
        recommendation = f"Recommended daily-use option: {recommended_name}."
        if maximum.status == STATUS_UNAVAILABLE:
            recommendation += " Maximum Accuracy is unavailable for download on this PC."
        elif maximum.status == STATUS_CAUTION:
            recommendation += (
                " Maximum Accuracy may work, but Live Scribe cannot confidently "
                "predict its speed or stability on this PC."
            )
        else:
            recommendation += (
                " Maximum Accuracy is also supported, though Best Overall remains "
                "the faster daily-use choice."
            )
        self.hardware_recommendation_var.set(recommendation)
        self.hardware_compatibility_var.set(assessment.compatibility_text())

        if update_selector and hasattr(self, "model_combo"):
            options = self._hardware_model_selection_options()
            self.model_combo.configure(values=list(options))
            selected = self._selected_model_name()
            if (
                selected
                and not is_model_downloaded(selected)
                and not assessment.capability(selected).download_allowed
            ):
                self.model_var.set(MODEL_PLACEHOLDER)
                self.settings.model_name = ""
                self.settings.save()

    def _show_first_run_hardware_notice(self) -> None:
        self.first_run_hardware_notice = False
        self.settings.hardware_check_completed = True
        self.settings.hardware_check_version = HARDWARE_CHECK_VERSION
        self.settings.save()
        self._show_page("Models")
        messagebox.showinfo(
            "PC check complete",
            self.hardware_assessment.buyer_notice(),
        )

    def _recheck_this_pc(self) -> None:
        if self.model_loading or self.model_downloading or self.finalizing or self.session is not None:
            messagebox.showinfo(
                "Please wait",
                "Finish the active download, transcription, or WAV verification before checking this PC again.",
            )
            return

        self.recheck_pc_button.configure(state="disabled", text="Checking…")
        self.status_var.set("Checking PC")
        self.activity_var.set("Checking RAM, CPU, GPU compatibility, and free model storage.")
        self.root.update_idletasks()

        try:
            self.hardware_assessment = assess_this_pc()
            save_hardware_assessment(self.hardware_assessment)
            self.settings.hardware_check_completed = True
            self.settings.hardware_check_version = HARDWARE_CHECK_VERSION
            self._refresh_hardware_advice(update_selector=True)
            self._update_model_summary()
            self._update_model_status()
            self._set_controls_for_idle()
            self.settings.save()
        finally:
            self.recheck_pc_button.configure(state="normal", text="Check This PC Again")

        self.status_var.set("PC checked")
        self.activity_var.set(
            f"PC check complete. Recommended: "
            f"{model_friendly_name(self.hardware_assessment.recommended_model)}."
        )
        messagebox.showinfo(
            "PC check complete",
            self.hardware_assessment.buyer_notice(),
        )

    def _model_capability_note(self, model_name: str) -> str:
        if model_name not in MODEL_OPTIONS:
            return ""
        capability = self.hardware_assessment.capability(model_name)
        return f"{capability.headline}. {capability.detail}".strip()

    def _selected_model_name(self) -> str:
        return model_id_from_display(self.model_var.get())

    def _on_model_selected(self, _choice=None) -> None:
        self.settings.model_name = self._selected_model_name()
        self.settings.save()
        self._update_model_summary()
        self._update_model_status()
        if not (self.model_loading or self.model_downloading or self.finalizing or self.session is not None):
            self._set_controls_for_idle()

    def _update_model_summary(self) -> None:
        model_name = self._selected_model_name()
        if not model_name:
            self.model_summary_var.set(
                "Choose from the qualities Live Scribe considers usable on this PC. "
                "Unavailable downloads are removed from this selector."
            )
            return
        capability_note = self._model_capability_note(model_name)
        self.model_summary_var.set(
            f"{model_short_description(model_name)}.\n"
            f"{model_long_description(model_name)}\n\n"
            f"PC check: {capability_note}"
        )

    def _update_model_status(self) -> None:
        model_name = self._selected_model_name()
        status = model_status(model_name)
        if model_name in MODEL_OPTIONS:
            capability = self.hardware_assessment.capability(model_name)
            if capability.status == STATUS_UNAVAILABLE:
                if is_model_downloaded(model_name):
                    status += " This installed model is disabled on this PC by the capability check."
                else:
                    status += " Download disabled by the PC capability check."
            elif capability.status == STATUS_CAUTION:
                status += " Hardware note: performance is uncertain."
        self.model_status_var.set(status)

    def _collect_settings(self) -> AppSettings:
        settings = super()._collect_settings()
        settings.theme_name = self.theme_var.get()
        settings.topic_profile_id = self._selected_topic_profile().id
        settings.hardware_check_completed = self.settings.hardware_check_completed
        settings.hardware_check_version = self.settings.hardware_check_version
        return settings

    def _set_settings_state(self, state: str) -> None:
        for combo in (
            self.audio_source_combo,
            self.microphone_combo,
            self.language_combo,
            self.model_combo,
            self.device_combo,
            self.sensitivity_combo,
            self.topic_combo,
        ):
            combo.configure(state=state)
        switch_state = "normal" if state == "readonly" else "disabled"
        for switch in (
            self.noise_switch,
            self.review_switch,
            self.appendix_switch,
            self.timestamps_switch,
        ):
            switch.configure(state=switch_state)
        enabled = "normal" if state == "readonly" else "disabled"
        self.detect_button.configure(state=enabled)
        self.manage_topics_button.configure(state=enabled)
        if hasattr(self, "recheck_pc_button"):
            self.recheck_pc_button.configure(state=enabled)

    def _set_controls_for_idle(self) -> None:
        super()._set_controls_for_idle()
        model_name = self._selected_model_name()
        if not model_name:
            return
        capability = self.hardware_assessment.capability(model_name)
        if capability.status == STATUS_UNAVAILABLE:
            self.start_button.configure(state="disabled")
            self.download_model_button.configure(state="disabled")

    def _download_model_requested(self) -> None:
        if self.model_loading or self.model_downloading or self.finalizing or self.session is not None:
            return
        model_name = self._selected_model_name()
        if not model_name:
            messagebox.showinfo(
                "Choose speech quality",
                "Choose a speech quality option first, then click Download Selected Quality.",
            )
            return
        friendly = model_friendly_name(model_name)
        size = model_size_label(model_name)
        capability = self.hardware_assessment.capability(model_name)
        if capability.status == STATUS_UNAVAILABLE:
            installed_note = (
                "This model is already stored locally, but Live Scribe has disabled it on this PC."
                if is_model_downloaded(model_name)
                else "Live Scribe has disabled this model download on this PC."
            )
            messagebox.showwarning(
                "Unavailable on this PC",
                f"{friendly} is unavailable on this PC.\n\n"
                f"{installed_note}\n\n"
                f"{capability.detail}\n\n"
                "Choose another speech quality or improve the detected limitation and click Check This PC Again.",
            )
            self._set_controls_for_idle()
            return
        if is_model_downloaded(model_name):
            messagebox.showinfo(
                "Already downloaded",
                f"{friendly} ({size}) is already stored locally and can be used offline.",
            )
            self._set_controls_for_idle()
            return
        hardware_warning = ""
        if capability.status == STATUS_CAUTION:
            hardware_warning = (
                f"\n\nPC capability note:\n{capability.detail}\n"
                "This option is allowed because Live Scribe cannot determine with certainty that it will fail."
            )
        approved = messagebox.askokcancel(
            "Download speech quality",
            f"Download {friendly} ({size}) now?\n\n"
            "Only this selected AI speech model will be downloaded. Keep Live Scribe open "
            "and stay connected until the progress card disappears. Future sessions can reuse it offline."
            f"{hardware_warning}",
        )
        if not approved:
            return
        self.settings.model_name = model_name
        self.settings.save()
        self.model_download_cancel_event.clear()
        self.model_downloading = True
        self._set_controls_for_loading()
        self._show_download_progress(model_name)
        self.status_var.set("Downloading")
        self.activity_var.set("Downloading the selected speech quality into the portable models folder.")
        threading.Thread(
            target=self._download_model_worker,
            args=(model_name,),
            name="model-downloader",
            daemon=True,
        ).start()

    def _show_download_progress(self, model_name: str) -> None:
        self._show_page("Models")
        self.stop_download_button.configure(state="normal", text="Stop Download")
        friendly = model_friendly_name(model_name)
        self.download_progress_title.configure(text=f"Downloading {friendly}")
        self.download_progress_value.set(0.0)
        self.download_progress_text_var.set(
            f"Preparing {friendly} ({model_size_label(model_name)})…"
        )
        self.download_progress_bar.stop()
        self.download_progress_bar.configure(mode="indeterminate")
        self.download_progress_bar.start()
        self.download_progress_frame.grid()

    def _apply_download_progress(self, progress: ModelDownloadProgress) -> None:
        if not self.model_downloading and progress.phase != "complete":
            return
        percent = progress.percent
        if percent is None:
            if str(self.download_progress_bar.cget("mode")) != "indeterminate":
                self.download_progress_bar.configure(mode="indeterminate")
                self.download_progress_bar.start()
        else:
            self.download_progress_bar.stop()
            self.download_progress_bar.configure(mode="determinate")
            self.download_progress_value.set(percent / 100.0)

        friendly = model_friendly_name(progress.model_name)
        if progress.phase == "preparing":
            self.status_var.set("Preparing download")
            self.download_progress_text_var.set(progress.message or "Checking model files and size…")
            return

        details: list[str] = []
        downloaded = self._format_download_bytes(progress.downloaded_bytes)
        if progress.total_bytes > 0:
            total = self._format_download_bytes(progress.total_bytes)
            mark = "about " if progress.total_is_estimate else ""
            details.append(f"{downloaded} of {mark}{total}")
        else:
            details.append(f"{downloaded} downloaded")
        if percent is not None:
            details.append(f"{percent:.1f}%")
        if progress.speed_bytes_per_second > 0:
            details.append(f"{self._format_download_bytes(progress.speed_bytes_per_second)}/s")
        eta = self._format_download_eta(progress.eta_seconds)
        if eta:
            details.append(eta)
        self.download_progress_text_var.set(f"{friendly}: " + "  •  ".join(details))
        self.status_var.set("Downloading" if percent is None else f"Downloading {percent:.0f}%")

    def _model_download_cancelled(self, model_name: str) -> None:
        self.model_downloading = False
        self._hide_download_progress()
        self._update_model_summary()
        self._update_model_status()
        self._set_controls_for_idle()
        friendly = model_friendly_name(model_name)
        self.status_var.set("Download stopped")
        self.activity_var.set(
            f"{friendly} download stopped safely. Download it again later to resume."
        )
        messagebox.showinfo(
            "Download stopped",
            f"The {friendly} download was stopped safely. Partial files were kept. "
            "Click Download Selected Quality again later to resume from the saved progress.",
        )

    def _model_download_finished(self, model_name: str) -> None:
        self.model_downloading = False
        self._hide_download_progress()
        self.settings.model_name = model_name
        self.settings.save()
        self._update_model_summary()
        self._update_model_status()
        self._set_controls_for_idle()
        friendly = model_friendly_name(model_name)
        self.status_var.set("Ready")
        self.activity_var.set(f"{friendly} is ready. Live Scribe can now work offline.")
        messagebox.showinfo(
            "Speech quality ready",
            f"{friendly} finished downloading and is ready for offline transcription.",
        )
        self._show_page("Live Session")

    def _show_export_menu(self) -> None:
        menu = tk.Menu(self.root, tearoff=False)
        menu.add_command(label="Word document (.docx)", command=self._save_docx)
        menu.add_command(label="Plain text (.txt)", command=self._save_txt)
        menu.add_command(label="Subtitles (.srt)", command=self._save_srt)
        menu.add_separator()
        menu.add_command(label="Open recordings folder", command=self._open_recording_folder)
        x = self.export_button.winfo_rootx()
        y = self.export_button.winfo_rooty() + self.export_button.winfo_height() + 4
        menu.tk_popup(x, y)

    def _session_started(self, engine: WhisperEngine, session: LiveTranscriptionSession) -> None:
        super()._session_started(engine, session)
        self.recording_dot.configure(text_color=COLORS["danger"])
        self._show_page("Live Session")

    def _handle_session_event(self, event: SessionEvent) -> None:
        super()._handle_session_event(event)
        if event.kind == "finished":
            self.recording_dot.configure(text_color=COLORS["success"])

    def _reset_document(self) -> None:
        super()._reset_document()
        self.recording_dot.configure(text_color=COLORS["muted"])

    def _finalization_done(self, result: PostSessionResult) -> None:
        super()._finalization_done(result)
        self._show_page("Live Session")

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
                microphone=self.selected_audio_input_name,
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
