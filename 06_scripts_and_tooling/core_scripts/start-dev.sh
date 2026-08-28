#!/usr/bin/env bash
# start-dev.sh — start the mobile + chat-app dev servers inside a
# named tmux session ("lauburu") so the run survives a Termius
# disconnect. Re-attach with `tmux attach -t lauburu`.
#
# Idempotent: if the session already exists, attaches instead of
# creating a new one.
#
# Layout:
#   window 0 "mobile"   — `npx expo start` from apps/mobile
#   window 1 "chat-app" — `npm run dev` from chat-app
#   window 2 "logs"     — empty shell for ad-hoc tail / curl
#
# Does NOT start native builds, deploy, or trigger workflows.
set -euo pipefail

SESSION="lauburu"
ROOT="${LAUBURU_ROOT:-$HOME/LauburuGrapplingMap-mobile}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not installed — install via: brew install tmux"
  exit 1
fi

if [ ! -d "$ROOT/apps/mobile" ]; then
  echo "Mobile app dir not found at $ROOT/apps/mobile"
  echo "Set LAUBURU_ROOT env var if your repo lives elsewhere."
  exit 1
fi

# If session already exists, attach.
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Attaching to existing tmux session '$SESSION'…"
  exec tmux attach -t "$SESSION"
fi

echo "Creating tmux session '$SESSION'…"

tmux new-session -d -s "$SESSION" -n mobile -c "$ROOT/apps/mobile"
tmux send-keys -t "$SESSION:mobile" 'npx expo start' C-m

tmux new-window -t "$SESSION" -n chat-app -c "$ROOT/chat-app"
tmux send-keys -t "$SESSION:chat-app" 'npm run dev' C-m

tmux new-window -t "$SESSION" -n logs -c "$ROOT"

echo "Started. Attach with: tmux attach -t $SESSION"
echo "Read-only attach (observe only): tmux attach -r -t $SESSION"
