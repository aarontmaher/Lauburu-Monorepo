#!/usr/bin/env bash
set -euo pipefail

# 06_scripts_and_tooling/device_watchdog/launch_scrcpy_mesh.sh
# One-click wrapper for launch_scrcpy_mesh.py

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="/usr/bin/python3"

echo "[Launcher] Starting Lauburu scrcpy Screen Mirroring Mesh..."
exec "$PYTHON_BIN" "$SCRIPT_DIR/launch_scrcpy_mesh.py" "$@"
