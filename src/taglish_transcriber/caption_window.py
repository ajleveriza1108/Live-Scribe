from __future__ import annotations

import tkinter as tk

import customtkinter as ctk


class FloatingCaptionWindow:
    def __init__(self, parent, *, font_family: str, theme_name: str) -> None:
        self.parent = parent
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Live Scribe Captions")
        self.window.geometry("860x190")
        self.window.minsize(420, 120)
        self.window.attributes("-topmost", True)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.font_family = font_family
        self.font_size = 28
        self.text_var = tk.StringVar(value="Captions will appear here when speech is detected.")

        controls = ctk.CTkFrame(self.window, fg_color="transparent")
        controls.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            controls,
            text="Floating captions",
            font=ctk.CTkFont(family=font_family, size=13, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            controls,
            text="A−",
            width=42,
            command=lambda: self._change_size(-2),
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            controls,
            text="A+",
            width=42,
            command=lambda: self._change_size(2),
        ).pack(side="right", padx=(4, 0))

        self.caption_label = ctk.CTkLabel(
            self.window,
            textvariable=self.text_var,
            justify="left",
            anchor="w",
            wraplength=810,
            font=ctk.CTkFont(family=font_family, size=self.font_size, weight="bold"),
        )
        self.caption_label.pack(fill="both", expand=True, padx=18, pady=(6, 16))
        self.window.bind("<Configure>", self._resize_wrap)
        self.hide()

    def _resize_wrap(self, event=None) -> None:
        width = self.window.winfo_width()
        self.caption_label.configure(wraplength=max(360, width - 42))

    def _change_size(self, delta: int) -> None:
        self.font_size = max(16, min(54, self.font_size + delta))
        self.caption_label.configure(
            font=ctk.CTkFont(
                family=self.font_family,
                size=self.font_size,
                weight="bold",
            )
        )

    def update(self, text: str, speaker: str = "") -> None:
        clean = " ".join(text.strip().split())
        if speaker:
            clean = f"{speaker}: {clean}"
        if clean:
            self.text_var.set(clean)

    def show(self) -> None:
        self.window.deiconify()
        self.window.lift()
        self.window.attributes("-topmost", True)

    def hide(self) -> None:
        self.window.withdraw()

    def toggle(self) -> None:
        if self.window.state() == "withdrawn":
            self.show()
        else:
            self.hide()

    def destroy(self) -> None:
        try:
            self.window.destroy()
        except tk.TclError:
            pass
