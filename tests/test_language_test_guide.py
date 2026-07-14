from pathlib import Path


def test_language_test_guide_has_eight_youtube_links() -> None:
    guide = (Path(__file__).resolve().parents[1] / "LANGUAGE_TEST_VIDEOS.md").read_text(encoding="utf-8")
    assert guide.count("https://www.youtube.com/watch?v=") == 8
    for language in ("English", "Filipino / Tagalog", "Spanish", "French", "German", "Italian", "Portuguese", "Dutch"):
        assert f"## {language}" in guide
