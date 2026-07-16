from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

VERSION = "0.8.1"
APP_DIR_NAME = "LiveScribe"
PRODUCT_SLUG = "Live-Scribe"
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"
RELEASE = ROOT / "release"


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def platform_label() -> str:
    machine = platform.machine().lower()
    if sys.platform == "win32":
        return "Windows-x64" if machine in {"amd64", "x86_64"} else f"Windows-{machine}"
    if sys.platform == "darwin":
        architecture = "Apple-Silicon" if machine in {"arm64", "aarch64"} else "Intel"
        return f"macOS-{architecture}"
    architecture = "x64" if machine in {"amd64", "x86_64"} else machine
    return f"Linux-{architecture}"


def make_writable_executable(path: Path) -> None:
    if path.exists():
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def copy_common_files(destination: Path) -> None:
    for filename in (
        "BUYER_GUIDE.txt",
        "LICENSE.txt",
        "THIRD_PARTY_NOTICES.md",
        "RESEARCH_NOTES.md",
        "README.md",
        "PORTABLE_USE.txt",
        "LANGUAGE_TEST_VIDEOS.md",
    ):
        shutil.copy2(ROOT / filename, destination / filename)
    for folder in ("Skills", "Knowledge", "dictionary", "engines"):
        shutil.copytree(ROOT / folder, destination / folder)
    for folder in ("models", "exports", "recordings", "data"):
        target = destination / folder
        target.mkdir(parents=True, exist_ok=True)
        (target / ".keep").write_text("Keep this folder with the portable app.\n", encoding="utf-8")
    shutil.copy2(ROOT / ".live-scribe-portable", destination / ".live-scribe-portable")


def package_release() -> Path:
    label = platform_label()
    release_name = f"{PRODUCT_SLUG}-v{VERSION}-{label}"
    destination = RELEASE / release_name
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    copy_common_files(destination)

    if sys.platform == "darwin":
        app_bundle = DIST / "Live Scribe.app"
        if app_bundle.exists():
            shutil.copytree(app_bundle, destination / app_bundle.name, symlinks=True)
        else:
            shutil.copytree(DIST / APP_DIR_NAME, destination / APP_DIR_NAME, symlinks=True)
        shutil.copy2(ROOT / "launchers" / "start_macos.sh", destination / "start_macos.sh")
        shutil.copy2(
            ROOT / "launchers" / "Start Live Scribe.command",
            destination / "Start Live Scribe.command",
        )
        make_writable_executable(destination / "start_macos.sh")
        make_writable_executable(destination / "Start Live Scribe.command")
    elif sys.platform == "win32":
        shutil.copytree(DIST / APP_DIR_NAME, destination / APP_DIR_NAME)
        shutil.copy2(ROOT / "launchers" / "start_windows.bat", destination / "Start Live Scribe.bat")
    else:
        shutil.copytree(DIST / APP_DIR_NAME, destination / APP_DIR_NAME, symlinks=True)
        shutil.copy2(ROOT / "launchers" / "start_linux.sh", destination / "start_linux.sh")
        make_writable_executable(destination / "start_linux.sh")

    return destination


def zip_folder(folder: Path) -> Path:
    archive = folder.parent / f"{folder.name}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            arcname = path.relative_to(folder.parent)
            info = zipfile.ZipInfo.from_file(path, arcname=str(arcname))
            info.compress_type = zipfile.ZIP_DEFLATED
            with path.open("rb") as source:
                zf.writestr(info, source.read())
    return archive


def tar_folder(folder: Path) -> Path:
    archive = folder.parent / f"{folder.name}.tar.gz"
    if archive.exists():
        archive.unlink()
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(folder, arcname=folder.name, recursive=True)
    return archive


def packaged_executable() -> Path:
    if sys.platform == "darwin":
        bundled = DIST / "Live Scribe.app" / "Contents" / "MacOS" / APP_DIR_NAME
        if bundled.exists():
            return bundled
    suffix = ".exe" if sys.platform == "win32" else ""
    return DIST / APP_DIR_NAME / f"{APP_DIR_NAME}{suffix}"


def smoke_test() -> None:
    executable = packaged_executable()
    if not executable.exists():
        raise FileNotFoundError(f"Packaged executable not found: {executable}")
    smoke_home = BUILD / "portable-smoke-home"
    if smoke_home.exists():
        shutil.rmtree(smoke_home)
    smoke_home.mkdir(parents=True)
    env = os.environ.copy()
    env["LIVE_SCRIBE_HOME"] = str(smoke_home)
    run([str(executable), "--self-test"], env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-smoke-test", action="store_true")
    args = parser.parse_args()

    if not args.skip_tests:
        run([sys.executable, "-m", "pytest"])

    for folder in (DIST, BUILD, RELEASE):
        if folder.exists():
            shutil.rmtree(folder)
    RELEASE.mkdir(parents=True)

    run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "portable_app.spec"])

    if not args.skip_smoke_test:
        smoke_test()

    destination = package_release()
    archives = [zip_folder(destination)]
    if sys.platform != "win32":
        archives.append(tar_folder(destination))

    print("Portable release created:")
    for archive in archives:
        print(f"  {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
