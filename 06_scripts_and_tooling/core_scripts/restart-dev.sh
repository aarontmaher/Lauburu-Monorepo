#!/usr/bin/env bash
# restart-dev.sh — kill the "lauburu" tmux session if running, then
# re-create it via start-dev.sh. Useful when the Expo dev server
# wedges or chat-app needs a clean restart after a config change.
set -euo pipefail

SESSION="lauburu"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Killing existing tmux session '$SESSION'…"
  tmux kill-session -t "$SESSION"
fi

exec "$SCRIPT_DIR/start-dev.sh"
