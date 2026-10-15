#!/usr/bin/env bash
LIVE_FILE="/Volumes/Lauburu-Monorepo/obsidian_vault/05_AGENTS/PROVEN_MATRIX_SWARM_LIVE.md"
if [ -f "$LIVE_FILE" ]; then
    cat "$LIVE_FILE"
else
    echo "Proven Matrix Swarm state not found."
fi
