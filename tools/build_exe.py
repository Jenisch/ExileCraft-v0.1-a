"""Build a standalone Windows executable for ExileCraft using PyInstaller."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

try:
    from PyInstaller.__main__ import run as pyinstaller_run
except ModuleNotFoundError as exc:  # pragma: no cover - checked manually
    raise SystemExit(
        "PyInstaller is not installed. Install it with `py -m pip install -r requirements.txt` "
        "before building the executable."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"


def _format_add_data(path: Path, target: str) -> str:
    """Format the --add-data argument for PyInstaller respecting platform separators."""

    return f"{path}{os.pathsep}{target}"


def build_exe(*, clean: bool = False, one_file: bool = True, console: bool = False) -> None:
    """Invoke PyInstaller with sensible defaults for the ExileCraft GUI."""

    if clean:
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        shutil.rmtree(DIST_DIR, ignore_errors=True)

    add_data = []
    if DATA_DIR.exists():
        add_data.append(_format_add_data(DATA_DIR, "data"))

    args = [
        "main.py",
        "--name=ExileCraft",
        "--clean",
        "--noconfirm",
        "--hidden-import=tkinter",
        f"--add-data={_format_add_data(ROOT / 'requirements.txt', '.')}",
    ]
    for data_entry in add_data:
        args.append(f"--add-data={data_entry}")

    if one_file:
        args.append("--onefile")
    if not console:
        args.append("--noconsole")

    pyinstaller_run(args)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--console", action="store_true", help="Leave a console window attached")
    parser.add_argument("--clean", action="store_true", help="Remove previous build artefacts first")
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Create an unpacked folder instead of a single-file executable",
    )
    args = parser.parse_args(argv)
    build_exe(clean=args.clean, one_file=not args.onedir, console=args.console)


if __name__ == "__main__":  # pragma: no cover - manual execution script
    main()
