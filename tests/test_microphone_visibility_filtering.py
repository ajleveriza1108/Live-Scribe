from __future__ import annotations

from src.taglish_transcriber.audio import (
    MicrophoneInfo,
    _deduplicate_microphones,
    _microphone_matches_connected_key,
    _microphone_name_key,
    list_available_microphones,
)


def _mic(
    index: int,
    name: str,
    *,
    host: str,
    default: bool = False,
    available: bool = True,
) -> MicrophoneInfo:
    return MicrophoneInfo(
        index=index,
        name=name,
        sample_rate=48000.0,
        max_input_channels=2,
        is_default=default,
        available=available,
        host_api_name=host,
    )


def test_microphone_name_normalization_collapses_backend_punctuation() -> None:
    assert _microphone_name_key("Microphone Array (Realtek(R) Audio)") == (
        "microphone array realtek audio"
    )


def test_connected_name_matching_accepts_small_backend_decorations() -> None:
    microphone = _mic(
        8,
        "Microphone Array (Realtek(R) Audio)",
        host="Windows WASAPI",
    )
    connected = {"microphone array realtek audio"}
    assert _microphone_matches_connected_key(microphone, connected)


def test_duplicate_host_api_entries_collapse_to_one_user_choice(monkeypatch) -> None:
    monkeypatch.setattr("src.taglish_transcriber.audio.sys.platform", "win32")
    microphones = [
        _mic(1, "USB Microphone", host="MME", default=True),
        _mic(14, "USB Microphone", host="Windows DirectSound"),
        _mic(27, "USB Microphone", host="Windows WASAPI"),
    ]
    result = _deduplicate_microphones(
        microphones,
        native_default_key="usb microphone",
    )
    assert len(result) == 1
    assert result[0].index == 27
    assert result[0].host_api_name == "Windows WASAPI"
    assert result[0].is_default is True


def test_unavailable_duplicate_never_wins(monkeypatch) -> None:
    monkeypatch.setattr("src.taglish_transcriber.audio.sys.platform", "win32")
    microphones = [
        _mic(
            27,
            "USB Microphone",
            host="Windows WASAPI",
            available=False,
        ),
        _mic(
            14,
            "USB Microphone",
            host="Windows DirectSound",
            available=True,
        ),
    ]
    result = _deduplicate_microphones(microphones)
    assert len(result) == 1
    assert result[0].index == 14
    assert result[0].available is True


def test_user_list_hides_aliases_disconnected_and_duplicate_windows_rows(
    monkeypatch,
) -> None:
    monkeypatch.setattr("src.taglish_transcriber.audio.sys.platform", "win32")
    raw = [
        _mic(0, "Microsoft Sound Mapper - Input", host="MME", default=True),
        _mic(2, "USB Microphone", host="MME"),
        _mic(12, "USB Microphone", host="Windows DirectSound"),
        _mic(24, "USB Microphone", host="Windows WASAPI"),
        _mic(30, "Old Webcam Microphone", host="Windows WASAPI"),
        _mic(
            31,
            "Disconnected Headset",
            host="Windows WASAPI",
            available=False,
        ),
    ]
    monkeypatch.setattr(
        "src.taglish_transcriber.audio.list_microphones",
        lambda: raw,
    )
    monkeypatch.setattr(
        "src.taglish_transcriber.audio._connected_windows_microphone_keys",
        lambda: ({"usb microphone"}, "usb microphone"),
    )

    visible = list_available_microphones()
    assert [item.name for item in visible] == ["USB Microphone"]
    assert visible[0].index == 24
    assert visible[0].is_default is True


def test_native_name_mismatch_falls_back_instead_of_hiding_everything(
    monkeypatch,
) -> None:
    monkeypatch.setattr("src.taglish_transcriber.audio.sys.platform", "win32")
    raw = [
        _mic(8, "Built-in Microphone", host="Windows WASAPI"),
        _mic(9, "USB Mic", host="Windows WASAPI"),
    ]
    monkeypatch.setattr(
        "src.taglish_transcriber.audio.list_microphones",
        lambda: raw,
    )
    monkeypatch.setattr(
        "src.taglish_transcriber.audio._connected_windows_microphone_keys",
        lambda: ({"different backend name"}, ""),
    )

    visible = list_available_microphones()
    assert {item.name for item in visible} == {
        "Built-in Microphone",
        "USB Mic",
    }
