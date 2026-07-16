from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Iterable

import customtkinter as ctk


class WholeClickableDropdown(ctk.CTkButton):
    """A full-width dropdown whose entire surface opens the menu.

    Unlike a readonly CTkComboBox, the text area and arrow area are both
    clickable. Individual unavailable items can be displayed disabled.
    """

    def __init__(
        self,
        master,
        *,
        variable: tk.StringVar,
        values: Iterable[str],
        disabled_values: Iterable[str] = (),
        command: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        self.variable = variable
        self.values = list(values)
        self.disabled_values = set(disabled_values)
        self.selection_command = command
        self._logical_state = kwargs.pop("state", "normal")
        kwargs.pop("text", None)
        kwargs.pop("textvariable", None)
        super().__init__(
            master,
            text="",
            command=self._open_dropdown,
            anchor="w",
            **kwargs,
        )
        self.variable.trace_add("write", self._variable_changed)
        self._sync_text()

    def _variable_changed(self, *_args) -> None:
        self._sync_text()

    def _sync_text(self) -> None:
        value = self.variable.get().strip() or "Choose an option"
        self.configure(text=f"{value}    ▼")

    def get(self) -> str:
        return self.variable.get()

    def set(self, value: str) -> None:
        self.variable.set(value)

    def configure(self, require_redraw: bool = False, **kwargs):
        values = kwargs.pop("values", None)
        disabled_values = kwargs.pop("disabled_values", None)
        state = kwargs.pop("state", None)
        if values is not None:
            self.values = list(values)
        if disabled_values is not None:
            self.disabled_values = set(disabled_values)
        if state is not None:
            self._logical_state = state
            kwargs["state"] = "disabled" if state == "disabled" else "normal"
        result = super().configure(require_redraw=require_redraw, **kwargs)
        self._sync_text()
        return result

    config = configure

    def _menu_colors(self) -> tuple[str, str, str]:
        dark = ctk.get_appearance_mode().casefold() == "dark"
        if dark:
            return "#11151A", "#F5F7FA", "#252B33"
        return "#FFFFFF", "#171717", "#E8E3DA"

    def _open_dropdown(self) -> None:
        if self._logical_state == "disabled":
            return
        background, foreground, active = self._menu_colors()
        menu = tk.Menu(
            self,
            tearoff=False,
            bg=background,
            fg=foreground,
            activebackground=active,
            activeforeground=foreground,
            disabledforeground="#737B84",
            relief="flat",
            borderwidth=1,
            font=self._font,
        )
        for value in self.values:
            menu.add_command(
                label=value,
                state=("disabled" if value in self.disabled_values else "normal"),
                command=lambda selected=value: self._select(selected),
            )
        try:
            menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())
        finally:
            menu.grab_release()

    def _select(self, value: str) -> None:
        if value in self.disabled_values:
            return
        self.variable.set(value)
        if self.selection_command is not None:
            self.selection_command(value)
