from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from .interview import (
    AssistantSuggestion,
    InterviewProfile,
    InterviewProfileStore,
    LocalInterviewAI,
    PreparedQuestionMatcher,
    create_profile,
    looks_like_question,
    prepare_question_bank,
    prepared_suggestion,
)


class InterviewModeMixin:
    """Modern Interview Mode layered over the existing transcription app."""

    def __init__(self) -> None:
        self.interview_store = InterviewProfileStore()
        self.interview_profiles: list[InterviewProfile] = self.interview_store.load()
        self.interview_profile: InterviewProfile | None = None
        self.interview_matcher: PreparedQuestionMatcher | None = None
        self.interview_mode_active = False
        self.interview_role_var: tk.StringVar | None = None
        self.interview_assist_mode_var: tk.StringVar | None = None
        self.interview_profile_name_var: tk.StringVar | None = None
        self.interview_status_var: tk.StringVar | None = None
        self.interview_question_var: tk.StringVar | None = None
        self.interview_match_var: tk.StringVar | None = None
        self.interview_endpoint_var: tk.StringVar | None = None
        self.interview_model_var: tk.StringVar | None = None
        self._last_interview_entry_count = 0
        super().__init__()

    def _build_ui(self) -> None:
        super()._build_ui()
        self._build_interview_page()

    def _build_interview_page(self) -> None:
        page = self._page_frame("Interview Mode")
        page.grid_rowconfigure(3, weight=1)
        page.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 14))
        header.grid_columnconfigure(0, weight=1)
        self._page_header(
            header,
            "Interview Mode",
            "Prepare likely questions, match paraphrased live questions, and keep private answer suggestions separate from the transcript.",
        )

        setup = self._card(page, row=1, column=0, sticky="ew", padx=28, pady=(0, 12))
        for column in range(4):
            setup.grid_columnconfigure(column, weight=1)

        self.interview_profile_name_var = tk.StringVar(value="")
        self.interview_role_var = tk.StringVar(value="Interviewer")
        self.interview_assist_mode_var = tk.StringVar(value="Instant Assist")
        self.interview_status_var = tk.StringVar(value="Create or load an interview profile.")
        self.interview_question_var = tk.StringVar(value="No question detected yet.")
        self.interview_match_var = tk.StringVar(value="Prepared question matching is waiting.")
        self.interview_endpoint_var = tk.StringVar(
            value="http://127.0.0.1:8080/v1/chat/completions"
        )
        self.interview_model_var = tk.StringVar(value="local-interview-model")

        ctk.CTkLabel(
            setup,
            text="Profile name",
            text_color=self._color("text_secondary"),
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 5))
        self.interview_profile_entry = ctk.CTkEntry(
            setup,
            textvariable=self.interview_profile_name_var,
            height=38,
            fg_color=self._color("surface_alt"),
            border_color=self._color("border"),
        )
        self.interview_profile_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            setup,
            text="Incoming speech role",
            text_color=self._color("text_secondary"),
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=0, column=1, sticky="w", padx=8, pady=(14, 5))
        self.interview_role_menu = ctk.CTkOptionMenu(
            setup,
            variable=self.interview_role_var,
            values=["Interviewer", "Interviewee"],
            height=38,
            fg_color=self._color("surface_raised"),
            button_color=self._color("surface_raised"),
            text_color=self._color("text"),
        )
        self.interview_role_menu.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 14))

        ctk.CTkLabel(
            setup,
            text="Assistance mode",
            text_color=self._color("text_secondary"),
            font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
        ).grid(row=0, column=2, sticky="w", padx=8, pady=(14, 5))
        self.interview_assist_menu = ctk.CTkOptionMenu(
            setup,
            variable=self.interview_assist_mode_var,
            values=["Prepared Answers Only", "Instant Assist", "Full Assist"],
            height=38,
            fg_color=self._color("surface_raised"),
            button_color=self._color("surface_raised"),
            text_color=self._color("text"),
        )
        self.interview_assist_menu.grid(row=1, column=2, sticky="ew", padx=8, pady=(0, 14))

        button_holder = ctk.CTkFrame(setup, fg_color="transparent")
        button_holder.grid(row=1, column=3, sticky="e", padx=16, pady=(0, 14))
        ctk.CTkButton(
            button_holder,
            text="New / Edit Profile",
            command=self._open_interview_profile_editor,
            height=38,
            fg_color=self._color("surface_raised"),
            hover_color=self._color("border"),
            text_color=self._color("text"),
        ).pack(side="left", padx=(0, 6))
        self.interview_start_button = ctk.CTkButton(
            button_holder,
            text="Start Interview Assist",
            command=self._toggle_interview_assist,
            height=38,
            fg_color=self._color("success"),
            hover_color=self._color("success"),
            text_color="#FFFFFF",
        )
        self.interview_start_button.pack(side="left")

        status = ctk.CTkLabel(
            setup,
            textvariable=self.interview_status_var,
            text_color=self._color("text_secondary"),
            anchor="w",
            justify="left",
            wraplength=1000,
        )
        status.grid(row=2, column=0, columnspan=4, sticky="ew", padx=16, pady=(0, 14))

        body = ctk.CTkFrame(page, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=28, pady=(0, 22))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        transcript_card = self._card(body, row=0, column=0, sticky="nsew", padx=(0, 6))
        transcript_card.grid_rowconfigure(2, weight=1)
        transcript_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            transcript_card,
            text="Interview transcript",
            text_color=self._color("text"),
            font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            transcript_card,
            text=(
                "Only spoken words belong here. Choose Interviewer or Interviewee "
                "before the next incoming phrase when using one audio stream."
            ),
            text_color=self._color("text_secondary"),
            wraplength=480,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.interview_transcript_text = tk.Text(
            transcript_card,
            wrap="word",
            font=(self.font_family, 11),
            padx=12,
            pady=12,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        self.interview_transcript_text.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.text_widgets.append(self.interview_transcript_text)

        assistant_card = self._card(body, row=0, column=1, sticky="nsew", padx=(6, 0))
        assistant_card.grid_rowconfigure(5, weight=1)
        assistant_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            assistant_card,
            text="Private Interview Assistant",
            text_color=self._color("text"),
            font=ctk.CTkFont(family=self.font_family, size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            assistant_card,
            textvariable=self.interview_question_var,
            text_color=self._color("text"),
            wraplength=500,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 4))
        ctk.CTkLabel(
            assistant_card,
            textvariable=self.interview_match_var,
            text_color=self._color("text_secondary"),
            wraplength=500,
            justify="left",
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))

        controls = ctk.CTkFrame(assistant_card, fg_color="transparent")
        controls.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))
        ctk.CTkButton(
            controls,
            text="Generate from latest question",
            command=self._generate_latest_interview_answer,
            height=34,
            fg_color=self._color("surface_raised"),
            hover_color=self._color("border"),
            text_color=self._color("text"),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            controls,
            text="Clear suggestion",
            command=self._clear_interview_suggestion,
            height=34,
            fg_color="transparent",
            border_width=1,
            border_color=self._color("border"),
            text_color=self._color("text"),
        ).pack(side="left")

        self.interview_answer_text = tk.Text(
            assistant_card,
            wrap="word",
            font=(self.font_family, 12),
            padx=14,
            pady=14,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        self.interview_answer_text.grid(row=5, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.text_widgets.append(self.interview_answer_text)

        self._load_first_interview_profile()
        self._refresh_interview_transcript()
        self._apply_text_theme()

    def _load_first_interview_profile(self) -> None:
        if not self.interview_profiles:
            return
        self.interview_profile = self.interview_profiles[0]
        self.interview_profile_name_var.set(self.interview_profile.name)
        self.interview_matcher = PreparedQuestionMatcher(self.interview_profile.questions)
        self.interview_status_var.set(
            f"Loaded {self.interview_profile.name}: "
            f"{len(self.interview_profile.questions)} prepared questions."
        )

    def _open_interview_profile_editor(self) -> None:
        profile = self.interview_profile or create_profile()
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Interview Preparation Template")
        dialog.geometry("980x760")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        scroll.grid_columnconfigure(1, weight=1)

        fields = [
            ("Profile name", "name"),
            ("Applicant name", "applicant_name"),
            ("Target job", "target_job"),
            ("Company", "company"),
            ("Interview type", "interview_type"),
            ("Preferred answer style", "preferred_answer_style"),
            ("Preferred answer length", "preferred_answer_length"),
            ("Experience", "experience"),
            ("Skills", "skills"),
            ("Projects and achievements", "projects"),
            ("Strengths", "strengths"),
            ("Weaknesses being improved", "weaknesses"),
            ("Salary preference", "salary_preference"),
            ("Availability", "availability"),
            ("Company notes", "company_notes"),
            ("Resume text", "resume_text"),
            ("Job description", "job_description"),
        ]
        widgets: dict[str, object] = {}
        multiline = {
            "experience", "skills", "projects", "strengths", "weaknesses",
            "company_notes", "resume_text", "job_description",
        }

        for row, (label, attribute) in enumerate(fields):
            ctk.CTkLabel(
                scroll,
                text=label,
                anchor="nw",
                text_color=self._color("text_secondary"),
                font=ctk.CTkFont(family=self.font_family, size=11, weight="bold"),
            ).grid(row=row, column=0, sticky="nw", padx=(8, 12), pady=7)
            value = str(getattr(profile, attribute, ""))
            if attribute in multiline:
                widget = ctk.CTkTextbox(scroll, height=86)
                widget.insert("1.0", value)
            else:
                widget = ctk.CTkEntry(scroll, height=36)
                widget.insert(0, value)
            widget.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=5)
            widgets[attribute] = widget

        note = ctk.CTkLabel(
            scroll,
            text=(
                "Generate Template creates a broad role-specific question bank with "
                "alternative phrasings, keywords, categories, answer points, and truthful "
                "prepared-answer frameworks. Review and personalize the answers before use."
            ),
            wraplength=800,
            justify="left",
            anchor="w",
            text_color=self._color("text_secondary"),
        )
        note.grid(row=len(fields), column=0, columnspan=2, sticky="ew", padx=8, pady=(12, 8))

        def save_profile() -> None:
            for attribute, widget in widgets.items():
                if isinstance(widget, ctk.CTkTextbox):
                    value = widget.get("1.0", "end").strip()
                else:
                    value = widget.get().strip()
                setattr(profile, attribute, value)
            profile.name = profile.name or profile.target_job or "Interview Profile"
            profile.questions = prepare_question_bank(profile)
            existing = next(
                (index for index, item in enumerate(self.interview_profiles) if item.id == profile.id),
                None,
            )
            if existing is None:
                self.interview_profiles.append(profile)
            else:
                self.interview_profiles[existing] = profile
            self.interview_store.save(self.interview_profiles)
            self.interview_profile = profile
            self.interview_profile_name_var.set(profile.name)
            self.interview_matcher = PreparedQuestionMatcher(profile.questions)
            self.interview_status_var.set(
                f"Prepared {len(profile.questions)} likely questions for "
                f"{profile.target_job or 'the selected interview'}."
            )
            dialog.destroy()

        ctk.CTkButton(
            scroll,
            text="Generate Interview Template and Question Bank",
            command=save_profile,
            height=42,
            fg_color=self._color("success"),
            hover_color=self._color("success"),
            text_color="#FFFFFF",
        ).grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", padx=8, pady=(4, 16))

    def _toggle_interview_assist(self) -> None:
        if self.interview_mode_active:
            self.interview_mode_active = False
            self.interview_start_button.configure(text="Start Interview Assist")
            self.interview_status_var.set("Interview assistance stopped. Normal transcription remains available.")
            return
        if self.interview_profile is None:
            messagebox.showinfo(
                "Interview profile required",
                "Create the Interview Preparation Template before starting Interview Assist.",
                parent=self.root,
            )
            return
        if not self.interview_profile.questions:
            self.interview_profile.questions = prepare_question_bank(self.interview_profile)
            self.interview_store.save(self.interview_profiles)
        self.interview_matcher = PreparedQuestionMatcher(self.interview_profile.questions)
        self.interview_mode_active = True
        self._last_interview_entry_count = len(self.document.live_entries)
        self.interview_start_button.configure(text="Stop Interview Assist")
        self.interview_status_var.set(
            f"Interview Assist is ready with {len(self.interview_profile.questions)} prepared questions. "
            "Start Live Session transcription and select the role for incoming speech."
        )

    def _handle_session_event(self, event) -> None:
        super()._handle_session_event(event)
        if event.kind != "segment" or not self.interview_mode_active:
            return
        if len(self.document.live_entries) <= self._last_interview_entry_count:
            return
        self._last_interview_entry_count = len(self.document.live_entries)
        entry_index = len(self.document.live_entries) - 1
        role = self.interview_role_var.get() if self.interview_role_var else "Interviewer"
        updated = self.document.update_entry(entry_index, speaker=role, use_live=True)
        self._refresh_editor(select_last=True)
        self._refresh_interview_transcript()
        if role == "Interviewer" and looks_like_question(updated.text):
            self._process_interview_question(updated.text)

    def _refresh_interview_transcript(self) -> None:
        if not hasattr(self, "interview_transcript_text"):
            return
        self.interview_transcript_text.configure(state="normal")
        self.interview_transcript_text.delete("1.0", "end")
        for entry in self.document.live_entries:
            speaker = entry.speaker or "Speaker"
            self.interview_transcript_text.insert(
                "end",
                f"{speaker}: {entry.text}\n\n",
            )
        self.interview_transcript_text.see("end")
        self.interview_transcript_text.configure(state="disabled")

    def _process_interview_question(self, question: str) -> None:
        self.interview_question_var.set(f"Detected question:\n{question}")
        if self.interview_matcher is None:
            self.interview_match_var.set("No prepared question bank is loaded.")
            return
        match = self.interview_matcher.match(question)
        suggestion = prepared_suggestion(match)
        if suggestion is not None:
            self.interview_match_var.set(
                f"Matched prepared question ({match.confidence:.0f}%): "
                f"{suggestion.matched_question}"
            )
            self._show_interview_suggestion(suggestion)
            if match.confidence >= 85:
                return
        else:
            self.interview_match_var.set(
                f"No reliable prepared match ({match.confidence:.0f}%)."
            )

        mode = self.interview_assist_mode_var.get() if self.interview_assist_mode_var else "Instant Assist"
        if mode != "Prepared Answers Only":
            self._generate_interview_answer(question)

    def _recent_interview_context(self) -> str:
        entries = self.document.live_entries[-6:]
        return "\n".join(
            f"{entry.speaker or 'Speaker'}: {entry.text}" for entry in entries
        )

    def _generate_latest_interview_answer(self) -> None:
        question = self.interview_question_var.get().replace("Detected question:\n", "").strip()
        if not question or question == "No question detected yet.":
            messagebox.showinfo(
                "No question detected",
                "Start Interview Assist or type/select a recent interviewer question first.",
                parent=self.root,
            )
            return
        self._generate_interview_answer(question)

    def _generate_interview_answer(self, question: str) -> None:
        profile = self.interview_profile
        if profile is None:
            return
        endpoint = (
            self.interview_endpoint_var.get().strip()
            if self.interview_endpoint_var
            else "http://127.0.0.1:8080/v1/chat/completions"
        )
        model = (
            self.interview_model_var.get().strip()
            if self.interview_model_var
            else "local-interview-model"
        )
        self.interview_status_var.set("Generating short local answer points…")
        self.interview_answer_text.configure(state="normal")
        self.interview_answer_text.delete("1.0", "end")
        self.interview_answer_text.insert("end", "Local AI is preparing a truthful answer…\n")
        self.interview_answer_text.configure(state="disabled")

        def worker() -> None:
            try:
                result = LocalInterviewAI(endpoint, model).generate(
                    profile=profile,
                    question=question,
                    recent_context=self._recent_interview_context(),
                )
            except Exception as exc:
                self.root.after(
                    0,
                    lambda: self._show_interview_error(str(exc)),
                )
                return
            self.root.after(0, lambda: self._show_interview_suggestion(result))

        threading.Thread(target=worker, daemon=True, name="interview-local-ai").start()

    def _show_interview_error(self, message: str) -> None:
        self.interview_status_var.set(message)
        self.interview_answer_text.configure(state="normal")
        self.interview_answer_text.delete("1.0", "end")
        self.interview_answer_text.insert(
            "end",
            message
            + "\n\nPrepared answers continue to work without the local AI server.",
        )
        self.interview_answer_text.configure(state="disabled")

    def _show_interview_suggestion(self, suggestion: AssistantSuggestion) -> None:
        self.interview_answer_text.configure(state="normal")
        self.interview_answer_text.delete("1.0", "end")
        self.interview_answer_text.insert("end", f"SOURCE: {suggestion.source}\n")
        if suggestion.confidence:
            self.interview_answer_text.insert(
                "end",
                f"MATCH CONFIDENCE: {suggestion.confidence:.0f}%\n",
            )
        if suggestion.points:
            self.interview_answer_text.insert("end", "\nINSTANT ANSWER POINTS\n")
            for point in suggestion.points:
                self.interview_answer_text.insert("end", f"• {point}\n")
        self.interview_answer_text.insert("end", "\nSUGGESTED ANSWER\n")
        self.interview_answer_text.insert("end", suggestion.answer)
        self.interview_answer_text.configure(state="disabled")
        self.interview_status_var.set(
            f"{suggestion.source} displayed privately. It is not added to the official transcript."
        )

    def _clear_interview_suggestion(self) -> None:
        self.interview_answer_text.configure(state="normal")
        self.interview_answer_text.delete("1.0", "end")
        self.interview_answer_text.configure(state="disabled")
        self.interview_match_var.set("Prepared question matching is waiting.")
