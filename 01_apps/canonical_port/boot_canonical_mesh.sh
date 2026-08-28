#!/usr/bin/env bash
# ==============================================================================
# Lauburu Mesh - Canonical Port Resilient Multiplexer Bootstrapper (2-Window)
# Version: 4.2.0-CANONICAL
# ==============================================================================
set -euo pipefail

SESSION_NAME="lauburu-canonical"

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
MONOREPO_ROOT="$(cd -P "${SCRIPT_DIR}/../.." && pwd)"

ACTION="${1:-boot}"
if [ "$ACTION" == "--kill" ] || [ "$ACTION" == "-k" ]; then
    echo "Stopping Tmux session: $SESSION_NAME..."
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || echo "No active session found."
    exit 0
elif [ "$ACTION" == "--restart" ] || [ "$ACTION" == "-r" ]; then
    echo "Restarting Tmux session: $SESSION_NAME..."
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
fi

# Pre-flight dependencies
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is not installed. Please run: brew install tmux" >&2
    exit 1
fi
if ! command -v uv &> /dev/null; then
    echo "Error: uv package manager not found on PATH." >&2
    exit 1
fi

# Clean stale Port 4000 processes
if lsof -i :4000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Warning: Port 4000 in use by PID $(lsof -ti :4000). Terminating stale instance..."
    kill -9 $(lsof -ti :4000) 2>/dev/null || true
    sleep 1
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Session '$SESSION_NAME' is already active. Attaching..."
    tmux attach-session -t "$SESSION_NAME"
    exit 0
fi

# Inject safe credentials from ~/.env if it exists
if [ -f "$HOME/.env" ]; then
    echo "Automating credential injection from ~/.env..."
    export $(grep -v '^#' "$HOME/.env" | xargs)
    tmux set-environment -t "$SESSION_NAME" CLOUDFLARE_API_KEY "${CLOUDFLARE_API_KEY:-}"
    tmux set-environment -t "$SESSION_NAME" CLOUDFLARE_ACCOUNT_ID "${CLOUDFLARE_ACCOUNT_ID:-}"
    tmux set-environment -t "$SESSION_NAME" HF_TOKEN "${HF_TOKEN:-}"
fi

# 1. Create Session with Window 0: Dedicated Full-Screen Command Center (Textual TUI)
tmux new-session -d -s "$SESSION_NAME" -n "Command Center"
tmux set-environment -t "$SESSION_NAME" PYTHONPATH "${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${MONOREPO_ROOT}/05_agents_and_swarms/red_blue_arena:${MONOREPO_ROOT}/00_core_infrastructure/self_healing_hub/src"
tmux set-environment -t "$SESSION_NAME" COLORTERM "truecolor"
tmux set-environment -t "$SESSION_NAME" TERM "xterm-256color"

# 2. Window 1: Background Services & Mesh
tmux new-window -t "$SESSION_NAME:1" -n "Services"

# Pane 1.0: FastAPI Backend (:4000) + CronScheduler
tmux send-keys -t "$SESSION_NAME:1.0" "cd '${SCRIPT_DIR}'" C-m
tmux send-keys -t "$SESSION_NAME:1.0" "uv run uvicorn backend.app:app --host 0.0.0.0 --port 4000" C-m

# Pane 1.1: Movesense BLE Bridge
tmux split-window -h -t "$SESSION_NAME:1.0"
tmux send-keys -t "$SESSION_NAME:1.1" "cd '${SCRIPT_DIR}'" C-m
tmux send-keys -t "$SESSION_NAME:1.1" "until curl -s -f http://127.0.0.1:4000/ >/dev/null 2>&1; do sleep 0.5; done; uv run python '${MONOREPO_ROOT}/03_biometrics_and_telemetry/movesense_to_4000_bridge.py'" C-m

# Pane 1.2: AI Debate TUI Live Sync
tmux split-window -v -t "$SESSION_NAME:1.1"
tmux send-keys -t "$SESSION_NAME:1.2" "cd '${SCRIPT_DIR}'" C-m
tmux send-keys -t "$SESSION_NAME:1.2" "until curl -s -f http://127.0.0.1:4000/ >/dev/null 2>&1; do sleep 0.5; done; uv run python '${SCRIPT_DIR}/tui/services/ai_debate_tui_sync.py'" C-m

# 3. Launch Textual TUI in Window 0 (100% viewport) with HTTP Readiness Probing
tmux select-window -t "$SESSION_NAME:0"
tmux send-keys -t "$SESSION_NAME:0.0" "cd '${SCRIPT_DIR}'" C-m
tmux send-keys -t "$SESSION_NAME:0.0" "until curl -s -f http://127.0.0.1:4000/ >/dev/null 2>&1; do sleep 0.5; done; uv run textual run tui/canonical_tui.py" C-m

# Focus Window 0 and attach
tmux select-window -t "$SESSION_NAME:0"
if [ "${ACTION}" != "--detached" ] && [ "${ACTION}" != "-d" ]; then
    tmux attach-session -t "$SESSION_NAME"
fi
