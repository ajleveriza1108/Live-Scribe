from __future__ import annotations

import threading

import pytest

from src.taglish_transcriber.models import (
    ModelDownloadCancelled,
    _ProgressTracker,
    _make_tqdm_class,
    _raise_if_download_cancelled,
)


def test_cancel_helper_raises_when_stop_is_requested() -> None:
    event = threading.Event()
    event.set()
    with pytest.raises(ModelDownloadCancelled):
        _raise_if_download_cancelled(event)


def test_progress_class_stops_on_next_update() -> None:
    event = threading.Event()
    tracker = _ProgressTracker(
        model_name="small",
        total_bytes=100,
        total_is_estimate=False,
        callback=None,
        cancel_event=event,
    )
    progress_class = _make_tqdm_class(tracker)
    progress = progress_class(total=100, unit="B")
    event.set()
    with pytest.raises(ModelDownloadCancelled):
        progress.update(1)
