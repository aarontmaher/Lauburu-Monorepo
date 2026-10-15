#!/usr/bin/env bash
# ==============================================================================
# Unified Lauburu TUI Ecosystem Matrix Launcher
# Launches all 3 canonical TUIs tiled/windowed inside a persistent tmux session:
#   Window 0: Canonical Port TUI (Textual, 17 Tabs, Live Consensus Sync)
#   Window 1: Rust Project Monitor (Ratatui, Full-Height 2-Tier Layouts)
#   Window 2: Swarm Health Monitor (Ratatui, Continuous Training ELO)
# Attaches via macOS Terminal.app per tui/SKILL.md protocol.
# ==============================================================================
set -euo pipefail

TMUX_BIN="/Users/aaron/.local/bin/tmux"
if [ ! -x "$TMUX_BIN" ]; then
    TMUX_BIN="$(command -v tmux)"
fi

echo "=============================================================================="
echo "⚡ LAUNCHING UNIFIED LAUBURU TUI ECOSYSTEM MATRIX"
echo "• Session: lauburu_tuis"
echo "• Window 0: canonical-port (Textual TUI on Port 4000 / AI Debate Sync)"
echo "• Window 1: rust-monitor (lauburu-monitor Ratatui)"
echo "• Window 2: swarm-health (lauburu-health Ratatui)"
echo "• Window 3: go-trainer-hud (continuous_polyglot_go_trainer Bubble Tea)"
echo "=============================================================================="

# 1. Kill stale session if present
"$TMUX_BIN" kill-session -t lauburu_tuis 2>/dev/null || true
sleep 0.5

# 2. Window 0: Canonical Port Live TUI
"$TMUX_BIN" new-session -d -s lauburu_tuis -n "canonical-port" -c /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port
"$TMUX_BIN" send-keys -t lauburu_tuis:0 "./run_live_tui.sh" C-m

# 3. Window 1: Rust Project Monitor
"$TMUX_BIN" new-window -t lauburu_tuis:1 -n "rust-monitor" -c /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
"$TMUX_BIN" send-keys -t lauburu_tuis:1 "/Users/aaron/.local/bin/lauburu-monitor" C-m

# 4. Window 2: Swarm Health Monitor
"$TMUX_BIN" new-window -t lauburu_tuis:2 -n "swarm-health" -c /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
"$TMUX_BIN" send-keys -t lauburu_tuis:2 "/Users/aaron/.local/bin/lauburu-health" C-m

# 5. Window 3: Go Bubble Tea HUD
"$TMUX_BIN" new-window -t lauburu_tuis:3 -n "go-trainer-hud" -c /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/continuous_polyglot_go_trainer
"$TMUX_BIN" send-keys -t lauburu_tuis:3 "/Users/aaron/.local/bin/continuous_polyglot_go_trainer -tui" C-m

# 6. Default focus on Window 0
"$TMUX_BIN" select-window -t lauburu_tuis:0

echo "✔ tmux session 'lauburu_tuis' initialized with 4 windows (Python, Rust, Rust, Go)."

# 6. Launch Terminal.app and attach to session
osascript -e "tell application \"Terminal\"
    do script \"${TMUX_BIN} attach -t lauburu_tuis\"
    activate
end tell" 2>/dev/null && echo "✔ macOS Terminal window created and attached to 'lauburu_tuis'." || echo "ℹ️ Attach manually with: tmux attach -t lauburu_tuis"
