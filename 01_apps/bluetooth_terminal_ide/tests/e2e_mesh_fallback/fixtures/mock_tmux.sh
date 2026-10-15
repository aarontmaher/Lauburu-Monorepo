#!/bin/bash
# Authentic Executable Script Fixture: mock_tmux.sh
# Emulates tmux CLI (specifically split-window) without python mocks.

if [ -n "$TMUX_AUDIT_LOG" ]; then
    echo "$(date +%s%N) [TMUX_INVOKED] ARGS=$*" >> "$TMUX_AUDIT_LOG"
fi

if [ "$1" = "split-window" ]; then
    # Successful split-window emulation
    exit 0
fi

exit 0
