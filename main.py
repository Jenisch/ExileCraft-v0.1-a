"""Entry point for the ExileCraft planner.

The application now launches a graphical interface by default while keeping the
original Rich-powered CLI accessible via the ``--cli`` flag. Both modes share
the same crafting engine and data loaders so they stay feature parity.
"""
from __future__ import annotations

import argparse
import sys


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ExileCraft crafting planner")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="launch the original console interface instead of the GUI",
    )
    parser.add_argument(
        "--data-source",
        choices=["auto", "repoe", "sample"],
        default="auto",
        help="override which dataset to load",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    if args.cli:
        from cli_app import run_cli

        run_cli(source=args.data_source)
        return

    try:
        from gui_app import run_app

        run_app(source=args.data_source)
    except Exception as exc:  # pragma: no cover - defensive logging
        try:
            import tkinter as tk  # noqa: F401  # pylint: disable=unused-import

            if isinstance(exc, tk.TclError):
                print(
                    "Unable to start the graphical interface. If you are running on a "
                    "headless machine, fall back to the CLI with `python main.py --cli`.",
                    file=sys.stderr,
                )
                print(str(exc), file=sys.stderr)
                sys.exit(1)
        except Exception:  # pragma: no cover - Tk not available
            pass
        raise


if __name__ == "__main__":
    main()
