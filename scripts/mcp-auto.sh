#!/usr/bin/env bash
set -euo pipefail

# Start/attach the local MCP automation bundle in one tmux session.
# This starts three repo-only loops:
#   1. bridge:watch       terminal heartbeat + bridge snapshots
#   2. watcher:mcp        MCP freshness poll + stale auto-refresh
#   3. prompt:dispatch    approved prompt dispatcher
#
# Default dispatcher mode is dry-run. Pass --dispatch to enable
# actual tmux paste/send into idle lanes.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="${MCP_AUTO_SESSION:-mcp-auto}"
POLL_INTERVAL="${MCP_AUTO_POLL_INTERVAL:-10}"
PROMPT_INTERVAL="${MCP_AUTO_PROMPT_INTERVAL:-10}"
DISPATCH_MODE="dry-run"
ATTACH=1

for arg in "$@"; do
  case "$arg" in
    --dispatch) DISPATCH_MODE="dispatch" ;;
    --dry-run) DISPATCH_MODE="dry-run" ;;
    --no-attach) ATTACH=0 ;;
    --help|-h)
      cat <<'EOF'
Usage: scripts/mcp-auto.sh [--dry-run|--dispatch] [--no-attach]

Starts one tmux session with:
  - npm run bridge:watch
  - npm run watcher:mcp -- --interval 10 --auto-refresh
  - npm run prompt:dispatch -- --watch --interval 10

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

tmux new-session -d -s "$SESSION" -n bridge-watch -c "$ROOT" 'npm run bridge:watch'
tmux new-window -t "$SESSION" -n mcp-poll -c "$ROOT" "npm run watcher:mcp -- --interval $POLL_INTERVAL --auto-refresh"

if [[ "$DISPATCH_MODE" == "dispatch" ]]; then
  tmux new-window -t "$SESSION" -n prompt-dispatch -c "$ROOT" "npm run prompt:dispatch -- --watch --interval $PROMPT_INTERVAL --dispatch --bridge-snapshot"
else
  tmux new-window -t "$SESSION" -n prompt-dry-run -c "$ROOT" "npm run prompt:dispatch -- --watch --interval $PROMPT_INTERVAL"
fi

tmux select-window -t "$SESSION:bridge-watch"

if [[ "$ATTACH" == "1" ]]; then
  exec tmux attach -t "$SESSION"
fi

echo "started $SESSION ($DISPATCH_MODE)"
