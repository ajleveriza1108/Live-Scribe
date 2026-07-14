from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from .dictionary_engine import VocabularyManager


class VocabularyPronunciationDialog:
    """Modern editor for difficult names, terms, and pronunciation aliases."""

    def __init__(self, parent: tk.Misc) -> None:
        self.manager = VocabularyManager()
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Vocabulary & Pronunciation")
        self.window.geometry("820x610")
        self.window.minsize(720, 540)
        self.window.transient(parent)
        self.window.grab_set()

        self.written_var = tk.StringVar()
        self.aliases_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Add the correct spelling and one or more ways the word may sound."
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
            text="Vocabulary & Pronunciation",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            container,
            text=(
                "Use this for names, places, acronyms, church terms, and technical words "
                "that speech recognition may misunderstand."
            ),
            wraplength=760,
            justify="left",
            text_color=("#625D55", "#A7B0BA"),
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

        form = ctk.CTkFrame(container, corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Correct written spelling").grid(
            row=0, column=0, sticky="w", padx=(16, 10), pady=(16, 8)
        )
        ctk.CTkEntry(form, textvariable=self.written_var, height=38).grid(
            row=0, column=1, sticky="ew", padx=(0, 16), pady=(16, 8)
        )
        ctk.CTkLabel(form, text="Sounds like / mistaken forms").grid(
            row=1, column=0, sticky="w", padx=(16, 10), pady=8
        )
        ctk.CTkEntry(form, textvariable=self.aliases_var, height=38).grid(
            row=1, column=1, sticky="ew", padx=(0, 16), pady=8
        )
        ctk.CTkLabel(
            form,
            text="Separate several forms with commas. Example: kan tos, cant toes",
            text_color=("#7B746A", "#7E8995"),
        ).grid(row=2, column=1, sticky="w", padx=(0, 16), pady=(0, 8))
        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=3, column=1, sticky="e", padx=(0, 16), pady=(4, 16))
        ctk.CTkButton(buttons, text="Clear", width=90, command=self._clear_form).pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons, text="Save Entry", width=110, command=self._save).pack(side="left")

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
        style.configure("LiveScribe.Treeview.Heading", font=("Segoe UI", 10, "bold"))

        self.tree = ttk.Treeview(
            list_frame,
            columns=("written", "aliases"),
            show="headings",
            selectmode="browse",
            style="LiveScribe.Treeview",
        )
        self.tree.heading("written", text="Correct spelling")
        self.tree.heading("aliases", text="Sounds like / mistaken forms")
        self.tree.column("written", width=240, anchor="w")
        self.tree.column("aliases", width=470, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 12))
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 16), pady=(0, 12))
        self.tree.configure(yscrollcommand=scrollbar.set)

        lower = ctk.CTkFrame(container, fg_color="transparent")
        lower.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        lower.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(lower, textvariable=self.status_var, text_color=("#625D55", "#A7B0BA")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(
            lower,
            text="Delete Selected",
            fg_color=("#C43D4B", "#FF5C66"),
            hover_color=("#A83440", "#D94852"),
            command=self._delete_selected,
        ).grid(row=0, column=1, padx=(8, 6))
        ctk.CTkButton(lower, text="Close", command=self.window.destroy).grid(row=0, column=2)

    def _reload_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.manager.reload()
        for entry in self.manager.pronunciation_entries:
            self.tree.insert("", "end", iid=entry.written, values=(entry.written, ", ".join(entry.sounds_like)))

    def _clear_form(self) -> None:
        self.written_var.set("")
        self.aliases_var.set("")
        for selected in self.tree.selection():
            self.tree.selection_remove(selected)

    def _load_selected(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0]).get("values", ())
        if len(values) >= 2:
            self.written_var.set(str(values[0]))
            self.aliases_var.set(str(values[1]))

    def _save(self) -> None:
        aliases = [value.strip() for value in self.aliases_var.get().split(",") if value.strip()]
        try:
            self.manager.save_pronunciation(self.written_var.get(), aliases)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Could not save entry", str(exc), parent=self.window)
            return
        self._reload_tree()
        self.status_var.set("Saved. This entry will be used when the next session starts.")
        self._clear_form()

    def _delete_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select an entry", "Select an entry to delete.", parent=self.window)
            return
        written = selected[0]
        if not messagebox.askyesno(
            "Delete pronunciation entry", f"Delete the entry for {written}?", parent=self.window
        ):
            return
        try:
            self.manager.remove_pronunciation(written)
        except OSError as exc:
            messagebox.showerror("Could not delete entry", str(exc), parent=self.window)
            return
        self._reload_tree()
        self._clear_form()
        self.status_var.set("Entry deleted.")
