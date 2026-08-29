#!/usr/bin/env bash
# ==============================================================================
# Open Wearables & Lauburu Mesh TUI Cockpit - Multi-Arch Container Entrypoint
# Supported Modes:
#   - interactive / tty: Interactive console cockpit
#   - web: Web-TUI server on Port 8088 (textual-web)
#   - verify: Headless pilot verification test
#   - custom commands: Passed through to exec
# Subsystem: 01_apps/canonical_port/entrypoint.sh
# ==============================================================================
set -euo pipefail

MODE="${1:-${MODE:-interactive}}"
PORT="${PORT:-8088}"
HOST="${HOST:-0.0.0.0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${PYTHONPATH:-}"
export TERM="${TERM:-xterm-256color}"
export COLORTERM="${COLORTERM:-truecolor}"

echo "=============================================================================="
echo "⚡ OPEN WEARABLES & LAUBURU TUI MESH COCKPIT"
echo "• Architecture: $(uname -m)"
echo "• Operating Mode: ${MODE}"
echo "• Web Port: ${PORT}"
echo "• Directory: ${SCRIPT_DIR}"
echo "=============================================================================="

case "${MODE}" in
  web)
    echo "▶ Launching Web-TUI server on http://${HOST}:${PORT}..."
    exec python3 "${SCRIPT_DIR}/tui/serve_web_tui.py"
    ;;
  interactive|tty)
    echo "▶ Launching Interactive TUI Console..."
    exec python3 "${SCRIPT_DIR}/tui/canonical_tui.py"
    ;;
  verify|test)
    echo "▶ Executing Headless Verification..."
    exec python3 "${SCRIPT_DIR}/tui/verify_tui.py"
    ;;
  *)
    echo "▶ Custom command execution: $@"
    exec "$@"
    ;;
esac
