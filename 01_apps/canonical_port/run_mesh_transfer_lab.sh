#!/usr/bin/env bash
# ==============================================================================
# Dedicated Mesh Transfer Lab Cockpit Launcher
# Subsystem: 01_apps/canonical_port/run_mesh_transfer_lab.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python3"
APP="${SCRIPT_DIR}/tui/tui_mesh_transfer_lab.py"

if [ ! -x "${VENV_PYTHON}" ]; then
    VENV_PYTHON="python3"
fi

export TERM="${TERM:-xterm-256color}"
export COLORTERM="${COLORTERM:-truecolor}"
export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"

echo "=============================================================================="
echo "⚡ LAUNCHING LAUBURU MESH TRANSFER LAB COCKPIT"
echo "• Target App: ${APP}"
echo "• Virtual Env: ${VENV_PYTHON}"
echo "=============================================================================="

# Launch in tmux session
tmux kill-session -t mesh_transfer_lab 2>/dev/null || true
tmux new-session -d -s mesh_transfer_lab -c "${SCRIPT_DIR}/tui"
tmux send-keys -t mesh_transfer_lab:0 "${VENV_PYTHON} ${APP}" C-m

if [ "${1:-attach}" = "attach" ] && [ "$(uname)" = "Darwin" ]; then
    osascript -e 'tell application "Terminal"
        do script "tmux attach -t mesh_transfer_lab"
        activate
    end tell'
fi
echo "✔ Mesh Transfer Lab is live in tmux session: mesh_transfer_lab"
