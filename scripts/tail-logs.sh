#!/usr/bin/env bash
# tail-logs.sh — quick read-only attach to the lauburu tmux session
# specifically on the most-relevant window. Defaults to the
# `mobile` window so the Metro/Expo bundler output is in front.
#
# Usage:
#   ./scripts/tail-logs.sh             # mobile window (default)
#   ./scripts/tail-logs.sh chat-app    # chat-app window
#   ./scripts/tail-logs.sh logs        # ad-hoc shell window
set -euo pipefail

SESSION="lauburu"
WINDOW="${1:-mobile}"

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session '$SESSION' not running. Start it with: ./scripts/start-dev.sh"
  exit 1
fi

# -r is "read-only attach" — observe without typing into the
# session. Aaron can still drive the session from another attach
# elsewhere; this one is for quick log peeking from a phone /
# Termius without disturbing the running processes.
exec tmux attach -r -t "$SESSION:$WINDOW"
