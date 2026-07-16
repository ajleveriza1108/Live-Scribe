from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FakeStringVar:
    def __init__(self, value: str = "") -> None:
        self._value = value
        self._callbacks = []

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value
        for callback in list(self._callbacks):
            callback("", "", "")

    def trace_add(self, _mode: str, callback) -> None:
        self._callbacks.append(callback)


class FakeMenu:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def add_command(self, **_kwargs) -> None:
        pass

    def tk_popup(self, *_args) -> None:
        pass

    def grab_release(self) -> None:
        pass


class FakeCTkButton:
    def __init__(self, _master=None, **kwargs) -> None:
        self._font = "FakeFont"
        self.last_configuration = dict(kwargs)

        # This reproduces the behavior that triggered the Windows
        # startup crash inside CustomTkinter CTkButton._set_cursor().
        self.configure(cursor="hand2")

    def configure(self, require_redraw: bool = False, **kwargs):
        self.last_configuration.update(kwargs)
        return None

    config = configure

    def winfo_rootx(self) -> int:
        return 0

    def winfo_rooty(self) -> int:
        return 0

    def winfo_height(self) -> int:
        return 30


def _load_widget_module(monkeypatch):
    fake_tk = types.ModuleType("tkinter")
    fake_tk.StringVar = FakeStringVar
    fake_tk.Menu = FakeMenu

    fake_ctk = types.ModuleType("customtkinter")
    fake_ctk.CTkButton = FakeCTkButton
    fake_ctk.get_appearance_mode = lambda: "Dark"

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)

    path = (
        ROOT
        / "src"
        / "taglish_transcriber"
        / "ui_widgets.py"
    )
    spec = importlib.util.spec_from_file_location(
        "live_scribe_dropdown_regression",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dropdown_survives_initialization_time_configure(monkeypatch) -> None:
    module = _load_widget_module(monkeypatch)
    variable = FakeStringVar("Default microphone")

    dropdown = module.WholeClickableDropdown(
        None,
        variable=variable,
        values=["Default microphone", "USB microphone"],
        state="readonly",
    )

    assert dropdown.get() == "Default microphone"
    assert dropdown.last_configuration["text"].endswith("▼")


def test_dropdown_updates_without_recursive_configure(monkeypatch) -> None:
    module = _load_widget_module(monkeypatch)
    variable = FakeStringVar("Microphone A")

    dropdown = module.WholeClickableDropdown(
        None,
        variable=variable,
        values=["Microphone A", "Microphone B"],
    )
    variable.set("Microphone B")
    dropdown.configure(
        values=["Microphone B", "Microphone C"],
        disabled_values=["Microphone C"],
        state="readonly",
    )

    assert dropdown.get() == "Microphone B"
    assert dropdown.last_configuration["text"].startswith(
        "Microphone B"
    )
    assert dropdown.disabled_values == {"Microphone C"}
