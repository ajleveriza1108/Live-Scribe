from __future__ import annotations

import os

import huggingface_hub.constants as hub_constants

from src.taglish_transcriber import models


def test_huggingface_xet_is_disabled_for_clean_stop(monkeypatch) -> None:
    monkeypatch.setenv("HF_HUB_DISABLE_XET", "0")
    monkeypatch.setattr(hub_constants, "HF_HUB_DISABLE_XET", False)

    models._configure_clean_hub_cancellation()

    assert os.environ["HF_HUB_DISABLE_XET"] == "1"
    assert hub_constants.HF_HUB_DISABLE_XET is True
