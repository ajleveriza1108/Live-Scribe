from __future__ import annotations

from pathlib import Path

import pytest

from src.taglish_transcriber.topic_profiles import TopicProfileManager


EXPECTED_STARTERS = {
    "General Conversation",
    "Office & Business Meeting",
    "School, Class & Lecture",
    "Zoom, Google Meet & Online Meeting",
    "Interview & Research",
    "Church, Sermon & Bible Study",
    "Livestream, Webinar & Presentation",
    "Technology & Programming",
    "E-commerce & Online Selling",
    "News & Current Events",
}


def test_topic_manager_seeds_general_use_profiles(tmp_path: Path) -> None:
    manager = TopicProfileManager(tmp_path / "topic_profiles.json")
    assert set(manager.names) == EXPECTED_STARTERS
    assert manager.default_profile.name == "General Conversation"


def test_topic_profiles_support_add_edit_and_remove(tmp_path: Path) -> None:
    manager = TopicProfileManager(tmp_path / "topic_profiles.json")

    created = manager.add(
        "Weekly Inventory Review",
        "Supplier stock and product availability meeting.",
        "Walmart, Sportsman's Guide, SKU, backorder, inventory",
    )
    assert manager.get(created.id) is not None
    assert "SKU" in created.important_terms

    updated = manager.update(
        created.id,
        "Weekly Supplier Review",
        "Supplier stock, pricing, and availability.",
        ["SKU", "member price", "out of stock"],
    )
    assert updated.name == "Weekly Supplier Review"
    assert updated.important_terms == ("SKU", "member price", "out of stock")

    assert manager.remove(created.id)
    assert manager.get(created.id) is None


def test_topic_profile_validation_and_last_profile_protection(tmp_path: Path) -> None:
    manager = TopicProfileManager(tmp_path / "topic_profiles.json")
    with pytest.raises(ValueError):
        manager.add("", "", "")

    for profile in list(manager.profiles)[1:]:
        manager.remove(profile.id)

    with pytest.raises(ValueError):
        manager.remove(manager.default_profile.id)
