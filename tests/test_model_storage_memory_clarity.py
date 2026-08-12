from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _function_source(path: Path, function_name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"Function not found: {function_name}")


def test_models_page_distinguishes_selection_download_and_ram() -> None:
    source = (ROOT / "src/taglish_transcriber/ui.py").read_text(encoding="utf-8")
    assert "self.model_memory_var" in source
    assert 'text="No Model Loaded in RAM"' in source
    assert '"RAM now: No speech model is loaded.' in source
    assert "Release Loaded Model from RAM" in source


def test_release_ram_button_only_enables_for_a_loaded_engine() -> None:
    source = _function_source(
        ROOT / "src/taglish_transcriber/ui.py",
        "_update_model_memory_ui",
    )
    assert "engine.is_loaded" in source
    assert 'state="disabled"' in source
    assert 'state="disabled" if busy else "normal"' in source


def test_storage_window_explains_zero_byte_models_and_ram_separately() -> None:
    source = _function_source(
        ROOT / "src/taglish_transcriber/productivity_features.py",
        "_open_storage_manager",
    )
    assert "Storage & Memory Manager" in source
    assert "Disk storage = downloaded model files" in source
    assert "0 B + Not downloaded has no model files to delete" in source
    assert 'text="Remove Model Files"' in source


def test_zero_byte_model_rows_cannot_enable_remove() -> None:
    source = _function_source(
        ROOT / "src/taglish_transcriber/productivity_features.py",
        "_update_storage_action_states",
    )
    assert "selected_item.size_bytes > 0" in source
    assert 'state="normal" if removable_model else "disabled"' in source


def test_removing_model_files_keeps_the_quality_selected() -> None:
    source = _function_source(
        ROOT / "src/taglish_transcriber/productivity_features.py",
        "_remove_selected_model_storage",
    )
    assert "Keep the user's selected speech quality" in source
    assert "self.settings.model_name =" not in source
    assert "self.model_var.set(MODEL_PLACEHOLDER)" not in source
    assert "self.engine.unload()" in source


def test_storage_actions_use_compact_two_row_grid() -> None:
    source = _function_source(
        ROOT / "src/taglish_transcriber/productivity_features.py",
        "_open_storage_manager",
    )
    assert 'window.geometry("900x500")' in source
    assert "self.storage_remove_model_button.grid(" in source
    assert "self.storage_delete_all_button.grid(" in source
    assert "self.storage_close_button.grid(" in source
