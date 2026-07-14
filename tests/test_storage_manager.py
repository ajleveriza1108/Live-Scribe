from src.taglish_transcriber.storage_manager import format_size, storage_items


def test_storage_manager_has_models_and_user_storage_rows() -> None:
    items = storage_items()
    keys = {item.key for item in items}
    assert "model:small" in keys
    assert "partial" in keys
    assert "temp" in keys
    assert "recordings" in keys
    assert format_size(1024) == "1.00 KB"
