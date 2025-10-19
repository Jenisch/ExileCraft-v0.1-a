"""Utility to import the full RePoE database for ExileCraft."""
from __future__ import annotations

import argparse
import io
import shutil
import zipfile
from pathlib import Path
from typing import Iterable, Mapping

try:
    import requests
except ImportError as exc:  # pragma: no cover - handled at runtime
    raise SystemExit("The 'requests' package is required. Install it with `pip install requests`." ) from exc


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = REPO_ROOT / "data" / "repoe"
DOWNLOAD_URL = "https://github.com/brather1ng/RePoE/archive/refs/heads/master.zip"
REQUIRED_FILES = {
    "base_items.min.json",
    "mods.min.json",
}


def _resolve_source(path: Path) -> Path:
    if (path / "base_items.min.json").exists():
        return path
    if (path / "data").exists() and (path / "data" / "base_items.min.json").exists():
        return path / "data"
    raise FileNotFoundError(
        "Could not locate base_items.min.json in the provided source. Point the script to the RePoE/data folder."
    )


def _copy_required_files(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_FILES:
        src = source / filename
        if not src.exists():
            raise FileNotFoundError(f"Required file '{filename}' missing from source {source}.")
        shutil.copy2(src, destination / filename)


def _download_repoe(url: str, destination: Path) -> None:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = {name: name for name in archive.namelist()}
    member_map: Mapping[str, str] = {}
    for filename in REQUIRED_FILES:
        match = next((name for name in names if name.endswith(f"/data/{filename}")), None)
        if not match:
            raise FileNotFoundError(
                f"Did not find {filename} inside downloaded archive. The RePoE structure may have changed."
            )
        member_map[filename] = match

    destination.mkdir(parents=True, exist_ok=True)
    for filename, archive_name in member_map.items():
        with archive.open(archive_name) as src, open(destination / filename, "wb") as handle:
            shutil.copyfileobj(src, handle)


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        help="Local path to a RePoE data folder. If omitted, --download must be used.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the latest RePoE snapshot directly from GitHub.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing data without prompting.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    args = _parse_args(argv)

    if not args.download and not args.source:
        raise SystemExit("Provide --source or --download to populate the dataset.")

    if TARGET_DIR.exists() and not args.force:
        response = input(
            f"Existing data found in {TARGET_DIR}. Overwrite? [y/N]: "
        ).strip().lower()
        if response not in {"y", "yes"}:
            print("Aborting without changes.")
            return

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    if args.download:
        print("Downloading RePoE snapshot... This may take a moment.")
        try:
            _download_repoe(DOWNLOAD_URL, TARGET_DIR)
            print("Download complete. Required files extracted.")
        except Exception as exc:  # pragma: no cover - network failures are runtime concerns
            raise SystemExit(f"Failed to download RePoE data: {exc}") from exc

    if args.source:
        try:
            resolved = _resolve_source(args.source)
            _copy_required_files(resolved, TARGET_DIR)
            print(f"Copied RePoE data from {resolved}.")
        except Exception as exc:
            raise SystemExit(f"Unable to copy from {args.source}: {exc}") from exc

    print("RePoE dataset ready. Relaunch the planner to use the full database.")


if __name__ == "__main__":
    main()
