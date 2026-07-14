from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from .dictionary_engine import VocabularyManager


class VocabularyPronunciationDialog:
    """Add, edit, and remove difficult vocabulary and pronunciation aliases."""

    def __init__(self, parent: tk.Misc) -> None:
        self.manager = VocabularyManager()
        self.selected_original: str | None = None

        self.window = ctk.CTkToplevel(parent)
        self.window.title("Vocabulary Manager")
        self.window.geometry("860x640")
        self.window.minsize(740, 560)
        self.window.transient(parent)
        self.window.grab_set()

        self.written_var = tk.StringVar()
        self.aliases_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Add a new entry, or select a saved entry to edit or remove it."
        )
        self._build()
        self._reload_tree()

    def _build(self) -> None:
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(self.window, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=22, pady=22)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            container,
            text="Vocabulary Manager",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            container,
            text=(
                "Add, edit, or remove names, places, acronyms, church terms, and technical words "
                "that speech recognition may misunderstand."
            ),
            wraplength=800,
            justify="left",
            text_color=("#625D55", "#A7B0BA"),
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

        form = ctk.CTkFrame(container, corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Correct written spelling").grid(
            row=0, column=0, sticky="w", padx=(16, 10), pady=(16, 8)
        )
        self.written_entry = ctk.CTkEntry(
            form,
            textvariable=self.written_var,
            height=38,
        )
        self.written_entry.grid(
            row=0, column=1, sticky="ew", padx=(0, 16), pady=(16, 8)
        )

        ctk.CTkLabel(form, text="Sounds like / mistaken forms").grid(
            row=1, column=0, sticky="w", padx=(16, 10), pady=8
        )
        self.aliases_entry = ctk.CTkEntry(
            form,
            textvariable=self.aliases_var,
            height=38,
        )
        self.aliases_entry.grid(
            row=1, column=1, sticky="ew", padx=(0, 16), pady=8
        )
        ctk.CTkLabel(
            form,
            text="Separate several forms with commas. Example: kan tos, cant toes",
            text_color=("#7B746A", "#7E8995"),
        ).grid(row=2, column=1, sticky="w", padx=(0, 16), pady=(0, 8))

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=3, column=1, sticky="e", padx=(0, 16), pady=(4, 16))
        ctk.CTkButton(
            buttons,
            text="Clear Form",
            width=100,
            command=self._clear_form,
        ).pack(side="left", padx=(0, 8))
        self.add_button = ctk.CTkButton(
            buttons,
            text="Add New",
            width=100,
            command=self._add_new,
        )
        self.add_button.pack(side="left", padx=(0, 8))
        self.edit_button = ctk.CTkButton(
            buttons,
            text="Save Changes",
            width=120,
            command=self._save_changes,
            state="disabled",
        )
        self.edit_button.pack(side="left")

        list_frame = ctk.CTkFrame(container, corner_radius=12)
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            list_frame,
            text="Saved entries",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        style = ttk.Style(self.window)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "LiveScribe.Treeview",
            rowheight=30,
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", 10),
        )
        style.configure(
            "LiveScribe.Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
        )

        self.tree = ttk.Treeview(
            list_frame,
            columns=("written", "aliases"),
            show="headings",
            selectmode="browse",
            style="LiveScribe.Treeview",
        )
        self.tree.heading("written", text="Correct spelling")
        self.tree.heading("aliases", text="Sounds like / mistaken forms")
        self.tree.column("written", width=250, anchor="w")
        self.tree.column("aliases", width=500, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 12))
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)
        self.tree.bind("<Double-1>", self._load_selected)

        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 16), pady=(0, 12))
        self.tree.configure(yscrollcommand=scrollbar.set)

        lower = ctk.CTkFrame(container, fg_color="transparent")
        lower.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        lower.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            lower,
            textvariable=self.status_var,
            text_color=("#625D55", "#A7B0BA"),
        ).grid(row=0, column=0, sticky="w")
        self.remove_button = ctk.CTkButton(
            lower,
            text="Remove Selected",
            fg_color=("#C43D4B", "#FF5C66"),
            hover_color=("#A83440", "#D94852"),
            command=self._remove_selected,
            state="disabled",
        )
        self.remove_button.grid(row=0, column=1, padx=(8, 6))
        ctk.CTkButton(
            lower,
            text="Close",
            command=self.window.destroy,
        ).grid(row=0, column=2)

    def _aliases(self) -> list[str]:
        return [
            value.strip()
            for value in self.aliases_var.get().split(",")
            if value.strip()
        ]

    def _reload_tree(self, select_written: str | None = None) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.manager.reload()
        for entry in self.manager.pronunciation_entries:
            self.tree.insert(
                "",
                "end",
                iid=entry.written,
                values=(entry.written, ", ".join(entry.sounds_like)),
            )
        if select_written and self.tree.exists(select_written):
            self.tree.selection_set(select_written)
            self.tree.focus(select_written)
            self.tree.see(select_written)

    def _clear_form(self) -> None:
        self.selected_original = None
        self.written_var.set("")
        self.aliases_var.set("")
        for selected in self.tree.selection():
            self.tree.selection_remove(selected)
        self.edit_button.configure(state="disabled")
        self.remove_button.configure(state="disabled")
        self.add_button.configure(state="normal")
        self.status_var.set("Enter a new vocabulary item, then click Add New.")
        self.written_entry.focus_set()

    def _load_selected(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        original = str(selected[0])
        values = self.tree.item(original).get("values", ())
        if len(values) < 2:
            return
        self.selected_original = original
        self.written_var.set(str(values[0]))
        self.aliases_var.set(str(values[1]))
        self.edit_button.configure(state="normal")
        self.remove_button.configure(state="normal")
        self.add_button.configure(state="disabled")
        self.status_var.set(
            "Editing selected entry. Change either field, then click Save Changes."
        )

    def _add_new(self) -> None:
        try:
            self.manager.add_pronunciation(
                self.written_var.get(),
                self._aliases(),
            )
        except (ValueError, OSError) as exc:
            messagebox.showerror("Could not add entry", str(exc), parent=self.window)
            return
        written = " ".join(self.written_var.get().strip().split())
        self._reload_tree(select_written=written)
        self.status_var.set(
            "Entry added. It will be used when the next transcription session starts."
        )
        self._clear_form()

    def _save_changes(self) -> None:
        if not self.selected_original:
            messagebox.showinfo(
                "Select an entry",
                "Select a saved entry before editing it.",
                parent=self.window,
            )
            return
        try:
            self.manager.update_pronunciation(
                self.selected_original,
                self.written_var.get(),
                self._aliases(),
            )
        except (ValueError, OSError) as exc:
            messagebox.showerror("Could not save changes", str(exc), parent=self.window)
            return
        written = " ".join(self.written_var.get().strip().split())
        self._reload_tree(select_written=written)
        self.status_var.set("Changes saved. The updated entry will be used in the next session.")
        self._clear_form()

    def _remove_selected(self) -> None:
        if not self.selected_original:
            messagebox.showinfo(
                "Select an entry",
                "Select a saved entry to remove.",
                parent=self.window,
            )
            return
        written = self.selected_original
        if not messagebox.askyesno(
            "Remove vocabulary entry",
            f"Remove the entry for {written}?",
            parent=self.window,
        ):
            return
        try:
            removed = self.manager.remove_pronunciation(written)
        except OSError as exc:
            messagebox.showerror("Could not remove entry", str(exc), parent=self.window)
            return
        if not removed:
            messagebox.showinfo(
                "Entry already removed",
                "That vocabulary entry no longer exists.",
                parent=self.window,
            )
        self._reload_tree()
        self._clear_form()
        self.status_var.set("Entry removed.")
