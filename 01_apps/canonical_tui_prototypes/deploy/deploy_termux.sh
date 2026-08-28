#!/usr/bin/env bash
# 01_apps/canonical_tui_prototypes/deploy/deploy_termux.sh
# =========================================================
# Shell launcher for Autonomous Termux Wireless Deployment & Provisioning Engine

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_DEPLOYER="${SCRIPT_DIR}/deploy_termux_tui.py"

if [ ! -f "${PYTHON_DEPLOYER}" ]; then
    echo "Error: Deployment engine not found at ${PYTHON_DEPLOYER}"
    exit 1
fi

chmod +x "${PYTHON_DEPLOYER}" 2>/dev/null || true

# Execute Python deployment engine forwarding all arguments
python3 "${PYTHON_DEPLOYER}" "$@"
