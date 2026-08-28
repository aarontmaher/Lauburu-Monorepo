#!/usr/bin/env bash
# ==============================================================================
# Canonical Port Live TUI Launcher & Real-Time /ai-debate Synchronizer
# Version: 4.0.0-CANONICAL
# Subsystem: 01_apps/canonical_port/run_live_tui.sh
# ==============================================================================
set -euo pipefail

# Robust symlink resolution
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

# Absolute monorepo fallback
if [ ! -f "${SCRIPT_DIR}/tui/canonical_tui.py" ]; then
    SCRIPT_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port"
fi

VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python3"
TUI_APP="${SCRIPT_DIR}/tui/canonical_tui.py"
SYNC_DAEMON="${SCRIPT_DIR}/tui/services/ai_debate_tui_sync.py"

# Fallback to system/uv python if venv python not found
if [ ! -x "${VENV_PYTHON}" ]; then
    if [ -x "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.venv/bin/python3" ]; then
        VENV_PYTHON="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.venv/bin/python3"
    elif command -v uv >/dev/null 2>&1; then
        VENV_PYTHON="uv run python"
    else
        VENV_PYTHON="python3"
    fi
fi

export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${SCRIPT_DIR}/../../05_agents_and_swarms/red_blue_arena:${SCRIPT_DIR}/../../00_core_infrastructure/self_healing_hub/src:${PYTHONPATH:-}"
export TERM="${TERM:-xterm-256color}"
export COLORTERM="${COLORTERM:-truecolor}"

echo "=============================================================================="
echo "⚡ LAUNCHING CANONICAL PORT LIVE TUI & AI DEBATE SYNCHRONIZER"
echo "• Protocol: Unyielding Consensus (>0.98 Accord)"
echo "• Council: Kimi 88B Titan | Qwen 3.8 Max | Abliterated Llama 70B | Gemini 3.7 Flash"
echo "• Path: ${SCRIPT_DIR}"
echo "• Virtual Env: ${VENV_PYTHON}"
echo "=============================================================================="

# 1. Start background AI Debate Live Sync Daemon if not already running
SYNC_PID=""
if ! pgrep -f "ai_debate_tui_sync.py" >/dev/null 2>&1; then
    echo "▶ Starting background AI Debate Sync Daemon..."
    ${VENV_PYTHON} "${SYNC_DAEMON}" > "/tmp/canonical_ai_debate_sync.log" 2>&1 &
    SYNC_PID=$!
    echo "✔ AI Debate Sync Daemon running in background (PID: ${SYNC_PID}). Log: /tmp/canonical_ai_debate_sync.log"
else
    echo "✔ AI Debate Sync Daemon already active."
fi

# Cleanup handler on TUI exit
cleanup() {
    echo ""
    echo "Shutting down Canonical Port TUI..."
    if [ -n "${SYNC_PID}" ] && kill -0 "${SYNC_PID}" 2>/dev/null; then
        echo "Stopping background sync daemon (PID: ${SYNC_PID})..."
        kill -TERM "${SYNC_PID}" 2>/dev/null || true
    fi
    echo "✔ Clean exit complete."
}
trap cleanup EXIT INT TERM

# 2. Launch Textual TUI
cd "${SCRIPT_DIR}"
${VENV_PYTHON} "${TUI_APP}"
