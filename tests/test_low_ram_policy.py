from pathlib import Path

from src.taglish_transcriber.resource_policy import resource_policy


ROOT = Path(__file__).resolve().parents[1]


def test_memory_saver_has_small_bounded_resources() -> None:
    policy = resource_policy(True)
    assert policy.audio_queue_blocks <= 64
    assert policy.transcript_queue_items <= 6
    assert policy.model_workers == 1
    assert policy.live_beam_size == 1
    assert policy.live_max_new_tokens <= 128


def test_engine_uses_one_worker_and_can_unload() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "models.py"
    ).read_text(encoding="utf-8")
    assert '"num_workers": self.policy.model_workers' in source
    assert "def unload(self)" in source
    assert "gc.collect()" in source


def test_session_queues_are_policy_bounded() -> None:
    source = (
        ROOT / "src" / "taglish_transcriber" / "session.py"
    ).read_text(encoding="utf-8")
    assert "self.policy.audio_queue_blocks" in source
    assert "self.policy.transcript_queue_items" in source
    assert "self.policy.event_queue_items" in source
