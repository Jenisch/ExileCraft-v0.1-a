#!/usr/bin/env bash
# Lightweight launcher for the ExileCraft CLI on Unix-like systems.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python3 main.py --cli "$@"
