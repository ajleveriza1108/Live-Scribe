from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_remains_one_folder_build() -> None:
    source = (ROOT / "portable_app.spec").read_text(encoding="utf-8")
    assert "COLLECT(" in source
    assert "exclude_binaries=True" in source


def test_launchers_redirect_writable_runtime_state() -> None:
    windows = (ROOT / "launchers" / "start_windows.bat").read_text(encoding="utf-8")
    linux = (ROOT / "launchers" / "start_linux.sh").read_text(encoding="utf-8")
    for source in (windows, linux):
        assert "LIVE_SCRIBE_HOME" in source
        assert "HF_HOME" in source
        assert "HF_XET_CACHE" in source
        assert "TMP" in source
        assert "PYTHONPYCACHEPREFIX" in source


def test_buyer_release_includes_portable_instructions() -> None:
    build = (ROOT / "scripts" / "build_portable.py").read_text(encoding="utf-8")
    assert '"PORTABLE_USE.txt"' in build
    assert '".live-scribe-portable"' in build
    assert (ROOT / "PORTABLE_USE.txt").is_file()
    assert (ROOT / ".live-scribe-portable").is_file()
