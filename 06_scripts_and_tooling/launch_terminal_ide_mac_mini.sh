#!/usr/bin/env bash
# ==============================================================================
# launch_terminal_ide_mac_mini.sh
# 🚀 Master Omniterminal & Canonical TUI Launcher for Apple Mac Mini M4 Pro
#
# Matrix Windows in 'lauburu_tuis' tmux session:
#   [0] Command_Center   : 9-Screen Textual AGI Command Center & Code Editor
#   [1] Omniterminal_IDE : Resilient Multi-Transport Console with 8 Topic Tabs
#   [2] Pixel_Stream     : Google Pixel 10 Pro XL Bluetooth Live Telemetry
#   [3] Arena_TUI        : Dual-Sandbox NPU vs GPU MLX Arena & ELO Leaderboard
#
# Governed by: /tui, /goal, /loop, Rule 0 Zero-Mock, Rule 3 Host Sanctuary
# ==============================================================================
set -euo pipefail

TMUX_BIN="$(command -v tmux || echo "/Users/aaron/.local/bin/tmux")"
SESSION="lauburu_tuis"
REPO_ROOT="/Volumes/Lauburu-Monorepo"
CANONICAL_PORT="${REPO_ROOT}/01_apps/canonical_port"
OMNITERMINAL_DIR="${REPO_ROOT}/teamwork_projects/unified_resilient_serial_terminal_ide"

echo "=============================================================================="
echo "🖥️  LAUNCHING UNIFIED LAUBURU TERMINAL IDE ON MAC MINI"
echo "• Session:  ${SESSION}"
echo "• Tmux:     ${TMUX_BIN}"
echo "• Host RAM: $(vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages free:\s+(\d+)/ and printf "%.2f GB free", $1*$size/1073741824')"
echo "=============================================================================="

# Check if session already exists
if $TMUX_BIN has-session -t "$SESSION" 2>/dev/null; then
    echo "✔ Active session '${SESSION}' found. Attaching..."
else
    echo "▶ Building fresh 4-window Terminal IDE workspace..."

    # Window 0: Canonical Port TUI Command Center
    $TMUX_BIN new-session -d -s "$SESSION" -n "Command_Center" -c "$CANONICAL_PORT"
    $TMUX_BIN send-keys -t "${SESSION}:0" "./run_live_tui.sh" C-m

    # Window 1: Omniterminal Console with 8 Topic Tabs
    $TMUX_BIN new-window -t "${SESSION}:1" -n "Omniterminal_IDE" -c "$OMNITERMINAL_DIR"
    $TMUX_BIN send-keys -t "${SESSION}:1" "python3 -m src.console.cli --live" C-m

    # Window 2: Pixel 10 Pro XL Bluetooth Stream
    $TMUX_BIN new-window -t "${SESSION}:2" -n "Pixel_Stream" -c "$REPO_ROOT"
    $TMUX_BIN send-keys -t "${SESSION}:2" "python3 06_scripts_and_tooling/bluetooth_pixel_terminal_bridge.py --loop 2" C-m

    # Window 3: Dual-Sandbox Arena TUI
    $TMUX_BIN new-window -t "${SESSION}:3" -n "Arena_TUI" -c "$REPO_ROOT"
    $TMUX_BIN send-keys -t "${SESSION}:3" "python3 01_apps/screen_lens/sandbox_evolution/bluetooth_terminal_arena/bluetooth_arena_tui.py" C-m

    # Select main Command Center window
    $TMUX_BIN select-window -t "${SESSION}:0"
    echo "✔ All 4 Terminal IDE workspace windows spawned."
fi

# Attach via Apple Terminal on macOS if interactive desktop is available
if [ -n "${TERM_PROGRAM:-}" ] || pgrep -f "Terminal" >/dev/null 2>&1; then
    echo "▶ Attaching window via Terminal.app..."
    osascript -e 'tell application "Terminal"
        do script "'"$TMUX_BIN"' attach -t '"$SESSION"'"
        activate
    end tell' 2>/dev/null || true
fi

echo "=============================================================================="
echo "✅ LAUBURU TERMINAL IDE RUNNING ON MAC MINI"
echo "• To attach manually:  ${TMUX_BIN} attach -t ${SESSION}"
echo "• Window Navigation:   Ctrl-B 0 (Command Center) | Ctrl-B 1 (Omniterminal)"
echo "                       Ctrl-B 2 (Pixel Stream)   | Ctrl-B 3 (Arena TUI)"
echo "=============================================================================="
