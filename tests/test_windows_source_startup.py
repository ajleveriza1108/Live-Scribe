from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_launcher_bootstraps_missing_source_environment() -> None:
    source = (
        ROOT / "launchers" / "start_windows.bat"
    ).read_text(encoding="utf-8")

    assert "source_setup_windows.ps1" in source
    assert "This is a new Live Scribe source folder." in source
    assert "ExecutionPolicy Bypass" in source
    assert 'if exist "%VENV_PYTHON%"' in source
    assert 'if exist "%PORTABLE_EXE%"' in source
    assert "Starting Live Scribe with the prepared environment" in source


def test_source_setup_requires_python_311_and_installs_dev_requirements() -> None:
    source = (
        ROOT / "scripts" / "source_setup_windows.ps1"
    ).read_text(encoding="utf-8-sig")

    assert "Find-Python311" in source
    assert 'Arguments = @("-3.11")' in source
    assert 'requirements-dev.txt' in source
    assert "-m venv" in source
    assert "-m pip install -r" in source
    assert "--self-test" in source


def test_root_windows_launcher_and_start_guide_exist() -> None:
    assert (ROOT / "Start Live Scribe.bat").is_file()
    guide = (ROOT / "START_HERE_WINDOWS.txt").read_text(
        encoding="utf-8"
    )
    assert "Double-click" in guide
    assert "Start Live Scribe.bat" in guide
    assert "first start needs an internet connection" in guide.casefold()
