#!/usr/bin/env bash
set -euo pipefail

# 06_scripts_and_tooling/device_watchdog/deploy_mobile_mesh.sh
# One-click wrapper for deploy_mobile_mesh.py

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="/usr/bin/python3"

echo "[Deployer] Starting Lauburu One-Click Mobile Deployment..."
exec "$PYTHON_BIN" "$SCRIPT_DIR/deploy_mobile_mesh.py" "$@"
