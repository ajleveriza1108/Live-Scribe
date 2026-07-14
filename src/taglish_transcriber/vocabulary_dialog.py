from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .dictionary_engine import VocabularyManager


class VocabularyPronunciationDialog:
    """Small editor for difficult names, terms, and pronunciation aliases."""

    def __init__(self, parent: tk.Misc) -> None:
        self.manager = VocabularyManager()
        self.window = tk.Toplevel(parent)
        self.window.title("Vocabulary & Pronunciation Guide")
        self.window.geometry("760x560")
        self.window.minsize(680, 500)
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
        container = ttk.Frame(self.window, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        ttk.Label(
            container,
            text="Vocabulary & Pronunciation Guide",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            container,
            text=(
                "Use this for names, places, acronyms, church terms, and technical words "
                "that speech recognition may misunderstand."
            ),
            wraplength=700,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 12))

        form = ttk.LabelFrame(container, text="Add or update an entry", padding=10)
        form.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Correct written spelling").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(form, textvariable=self.written_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(form, text="Sounds like / common mistaken forms").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0)
        )
        ttk.Entry(form, textvariable=self.aliases_var).grid(row=1, column=1, sticky="ew", pady=(8, 0))
        ttk.Label(
            form,
            text="Separate several forms with commas. Example: kan tos, cant toes",
            foreground="#555555",
        ).grid(row=2, column=1, sticky="w", pady=(3, 0))

        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=1, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="Clear", command=self._clear_form).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Save Entry", command=self._save).pack(side="left")

        list_frame = ttk.LabelFrame(container, text="Saved pronunciation entries", padding=8)
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("written", "aliases"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("written", text="Correct spelling")
        self.tree.heading("aliases", text="Sounds like / mistaken forms")
        self.tree.column("written", width=220, anchor="w")
        self.tree.column("aliases", width=430, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        lower = ttk.Frame(container)
        lower.grid(row=4, column=0, sticky="ew", pady=(9, 0))
        lower.columnconfigure(0, weight=1)
        ttk.Label(lower, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Button(lower, text="Delete Selected", command=self._delete_selected).grid(row=0, column=1, padx=(8, 6))
        ttk.Button(lower, text="Close", command=self.window.destroy).grid(row=0, column=2)

    def _reload_tree(self) -> None:
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

    def _clear_form(self) -> None:
        self.written_var.set("")
        self.aliases_var.set("")
        for selected in self.tree.selection():
            self.tree.selection_remove(selected)

    def _load_selected(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        values = item.get("values", ())
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
        self.status_var.set("Saved. The entry will be used when the next session starts.")
        self._clear_form()

    def _delete_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select an entry", "Select an entry to delete.", parent=self.window)
            return
        written = selected[0]
        if not messagebox.askyesno(
            "Delete pronunciation entry",
            f"Delete the entry for {written}?",
            parent=self.window,
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
