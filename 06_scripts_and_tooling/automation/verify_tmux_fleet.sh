#!/bin/bash
# verify_tmux_fleet.sh

SESSION_NAME="mesh_agy_fleet"

echo "Verifying tmux session: $SESSION_NAME..."

if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "ERROR: Session $SESSION_NAME does not exist."
    exit 1
fi

PANE_COUNT=$(tmux list-panes -t "$SESSION_NAME" | wc -l | tr -d ' ')
if [ "$PANE_COUNT" -lt 3 ]; then
    echo "ERROR: Expected at least 3 panes, found $PANE_COUNT."
    tmux list-panes -t "$SESSION_NAME"
    exit 1
fi

echo "SUCCESS: $SESSION_NAME is active with $PANE_COUNT panes."
exit 0
