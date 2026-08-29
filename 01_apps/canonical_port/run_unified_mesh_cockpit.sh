#!/usr/bin/env bash
# ==============================================================================
# Unified Mesh Cockpit Launcher (Omega Harmonized)
# Subsystem: 01_apps/canonical_port/run_unified_mesh_cockpit.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python3"
APP="${SCRIPT_DIR}/tui/unified_mesh_cockpit_tui.py"

if [ ! -x "${VENV_PYTHON}" ]; then
    VENV_PYTHON="python3"
fi

export TERM="${TERM:-xterm-256color}"
export COLORTERM="${COLORTERM:-truecolor}"
export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"

echo "⚡ Starting Unified Mesh Cockpit TUI (Omega Harmonized)..."
${VENV_PYTHON} "${APP}"
