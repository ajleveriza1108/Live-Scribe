from src.taglish_transcriber.config import (
    MODEL_OPTIONS,
    MODEL_SELECTION_OPTIONS,
    model_display_label,
    model_id_from_display,
)


def test_only_four_buyer_model_options_are_available() -> None:
    assert MODEL_OPTIONS == (
        "small",
        "medium",
        "large-v3-turbo",
        "large-v3",
    )


def test_buyer_labels_hide_internal_model_names() -> None:
    for model_name in MODEL_OPTIONS:
        label = model_display_label(model_name)
        assert model_id_from_display(label) == model_name
        assert model_name not in label
        assert "MB" in label or "GB" in label

    assert len(MODEL_SELECTION_OPTIONS) == 5
