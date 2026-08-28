#!/usr/bin/env bash
set -euo pipefail

# Start/attach the local MCP automation bundle in one tmux dashboard.
# This starts repo-only loops:
#   1. bridge:watch       terminal heartbeat + bridge snapshots
#   2. watcher:mcp        MCP freshness poll + stale auto-refresh
#   3. prompt:dispatch    approved prompt dispatcher
#   4. bridge:verify      periodic local artifact contract check
#
# Default dispatcher mode is dry-run. Pass --dispatch to enable
# actual tmux paste/send into idle lanes.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="${MCP_AUTO_SESSION:-mcp-auto}"
POLL_INTERVAL="${MCP_AUTO_POLL_INTERVAL:-10}"
PROMPT_INTERVAL="${MCP_AUTO_PROMPT_INTERVAL:-10}"
VERIFY_INTERVAL="${MCP_AUTO_VERIFY_INTERVAL:-300}"
DISPATCH_MODE="dry-run"
VERIFY_LOOP=1
ATTACH=1

for arg in "$@"; do
  case "$arg" in
    --dispatch) DISPATCH_MODE="dispatch" ;;
    --dry-run) DISPATCH_MODE="dry-run" ;;
    --no-verify) VERIFY_LOOP=0 ;;
    --no-attach) ATTACH=0 ;;
    --help|-h)
      cat <<'EOF'
Usage: scripts/mcp-auto.sh [--dry-run|--dispatch] [--no-verify] [--no-attach]

Starts one tmux session with one tiled window:
  - npm run bridge:watch
  - npm run watcher:mcp -- --interval 10 --auto-refresh
  - npm run prompt:dispatch -- --watch --interval 10 --generate-queue
  - npm run bridge:verify every 300s

Defaults to dry-run prompt dispatch. Use --dispatch only after
the local prompt queue is populated and reviewed.
EOF
      exit 0
      ;;
    *) echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done

if tmux has-session -t "$SESSION" 2>/dev/null; then
  if [[ "$ATTACH" == "1" ]]; then
    exec tmux attach -t "$SESSION"
  fi
  echo "$SESSION already running"
  exit 0
fi

tmux new-session -d -s "$SESSION" -n mcp-all -c "$ROOT" 'npm run bridge:watch'
tmux split-window -h -t "$SESSION:0" -c "$ROOT" "npm run watcher:mcp -- --interval $POLL_INTERVAL --auto-refresh"

if [[ "$DISPATCH_MODE" == "dispatch" ]]; then
  tmux split-window -v -t "$SESSION:0.0" -c "$ROOT" "npm run prompt:dispatch -- --watch --interval $PROMPT_INTERVAL --generate-queue --dispatch --bridge-snapshot"
else
  tmux split-window -v -t "$SESSION:0.0" -c "$ROOT" "npm run prompt:dispatch -- --watch --interval $PROMPT_INTERVAL --generate-queue"
fi

if [[ "$VERIFY_LOOP" == "1" ]]; then
  tmux split-window -v -t "$SESSION:0.1" -c "$ROOT" "while true; do date -u '+[%Y-%m-%dT%H:%M:%SZ] bridge:verify'; npm run bridge:verify; sleep $VERIFY_INTERVAL; done"
fi

tmux select-layout -t "$SESSION:0" tiled
tmux select-pane -t "$SESSION:0.0"

if [[ "$ATTACH" == "1" ]]; then
  exec tmux attach -t "$SESSION"
fi

echo "started $SESSION ($DISPATCH_MODE)"
