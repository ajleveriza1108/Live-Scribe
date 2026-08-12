from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_live_page_uses_compact_readable_shell() -> None:
    source = _source("src/taglish_transcriber/ui.py")
    assert "width=232," in source
    assert "size=24" in source
    assert 'header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 10))' in source
    assert "input_card = ctk.CTkScrollableFrame(" in source
    assert 'input_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))' in source
    assert 'self.start_button.grid(row=0, column=0, padx=(10, 4), pady=8)' in source


def test_workspace_input_controls_stay_readable_but_compact() -> None:
    source = _source("src/taglish_transcriber/ui.py")
    assert 'value="Meeting audio setup"' in source
    assert 'font=ctk.CTkFont(family=self.font_family, size=13, weight="bold")' in source
    assert source.count("height=34,") >= 4
    assert "width=78," in source
    assert "width=116," in source


def test_conversation_panels_do_not_share_the_same_grid_row() -> None:
    source = _source("src/taglish_transcriber/productivity_features.py")
    application_anchor = """self.application_audio_frame.grid(
            row=6,"""
    microphone_anchor = """self.microphone_monitor_frame.grid(
            row=7,"""
    session_anchor = """).grid(row=8, column=0, sticky="w", padx=(14, 8), pady=(0, 8))"""
    assert application_anchor in source
    assert microphone_anchor in source
    assert session_anchor in source


def test_compact_layout_preserves_readable_body_text() -> None:
    ui_source = _source("src/taglish_transcriber/ui.py")
    productivity_source = _source("src/taglish_transcriber/productivity_features.py")
    assert "size=8" not in ui_source
    assert "size=8" not in productivity_source
    # 9px is reserved for sidebar section labels, not body controls.
    assert 'size=9,' in ui_source
    assert 'size=10' in productivity_source


def test_live_setup_is_scrollable_and_height_clamped_so_action_buttons_stay_reachable() -> None:
    source = _source("src/taglish_transcriber/ui.py")
    assert "page.bind(\"<Configure>\", self._update_live_setup_viewport, add=\"+\")" in source
    assert "target_height = max(230, min(390, int(page_height) - 420))" in source
    assert "self.input_card.configure(height=target_height)" in source
    assert 'action_bar = self._card(page, row=4, column=0, sticky="ew", padx=20, pady=(0, 8))' in source
