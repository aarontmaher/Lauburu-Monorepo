#!/usr/bin/env bash
# ==============================================================================
# 🌐 mesh_multiplex_terminal.sh — 7-Layer Mesh Multiplexed Swarm Terminal
# ==============================================================================
# Spawns and manages a persistent multiplexed tmux cluster across all Lauburu
# physical nodes for real-time swarm orchestration, continuous LoRA harvesting,
# and hardware-level telemetry monitoring.
#
# Governed by:
# - Rule #0 & #1: Zero-Mock Empirical Truth
# - Rule #3 & #10: Mac Mini Sanctuary & Linux Mini First-Offload Invariant
# ==============================================================================

set -euo pipefail

SESSION_NAME="mesh_swarms"
PROJECT_DIR="/Volumes/Lauburu-Monorepo"

test_connections() {
    echo "=== 🌐 Probing Lauburu Mesh SSH Fleet ==="
    printf "%-25s %-20s %-10s\n" "NODE" "HOST ALIAS" "STATUS"
    echo "--------------------------------------------------------"

    nodes=(
        "L1 Mac Mini Host:localhost:ssh localhost id"
        "L8 Linux Mini (TB3):linuxmini-tb:ssh linuxmini-tb id"
        "GW GL.iNet Router:router:ssh router id"
        "L7 Samsung S20+ Termux:s20:ssh s20 id"
        "L6 Pixel 10 Pro XL:pixel:ssh pixel id"
    )

    all_ok=0
    for entry in "${nodes[@]}"; do
        IFS=":" read -r name alias cmd <<< "$entry"
        if eval "$cmd" >/dev/null 2>&1; then
            printf "%-25s %-20s \033[0;32m[ONLINE]\033[0m\n" "$name" "$alias"
        else
            printf "%-25s %-20s \033[0;31m[FAILED]\033[0m\n" "$name" "$alias"
            all_ok=1
        fi
    done

    echo "--------------------------------------------------------"
    return $all_ok
}

launch_multiplex() {
    echo "🚀 Initializing tmux session: ${SESSION_NAME}..."

    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo "Tmux session '${SESSION_NAME}' already exists. Reconnecting/attaching..."
        if [ -t 0 ]; then
            tmux attach-session -t "$SESSION_NAME"
        else
            echo "Session active in background. Attach via: tmux attach-session -t ${SESSION_NAME}"
        fi
        return 0
    fi

    # Create new session starting in L1 Mac Mini
    tmux new-session -d -s "$SESSION_NAME" -n "mesh_cluster" -c "$PROJECT_DIR"

    # Pane 0 (Top Left): L1 Host Swarm Orchestrator & Screen Lens HUD
    tmux send-keys -t "$SESSION_NAME:0.0" "echo '👑 L1 Mac Mini Host (Sovereign Orchestrator)' && python3 01_apps/screen_lens/src/scrcpy/screen_lens_scrcpy_manager.py --list" C-m

    # Split horizontally -> Pane 1 (Top Right): L8 Linux Mini (Neo ML & LoRA Engine)
    tmux split-window -h -t "$SESSION_NAME:0"
    tmux send-keys -t "$SESSION_NAME:0.1" "ssh linuxmini-tb 'echo \"🐧 L8 Linux Mini [32GB RAM Neo Engine]\" && free -h'" C-m

    # Split Pane 0 vertically -> Pane 2 (Bottom Left): GW GL.iNet Router
    tmux select-pane -t "$SESSION_NAME:0.0"
    tmux split-window -v -t "$SESSION_NAME:0.0"
    tmux send-keys -t "$SESSION_NAME:0.1" "ssh router 'echo \"🛰️ GW GL-BE14000 Sovereign Gateway\" && free -m && cat /proc/swaps'" C-m

    # Split Pane 2 vertically -> Pane 3 (Bottom Mid): L7 Samsung S20+ Router Control Center
    tmux select-pane -t "$SESSION_NAME:0.2"
    tmux split-window -v -t "$SESSION_NAME:0.2"
    tmux send-keys -t "$SESSION_NAME:0.3" "ssh s20 'echo \"📱 L7 Samsung S20+ [Router Control Center / Shizuku rish]\" && uname -a'" C-m

    # Split Pane 1 vertically -> Pane 4 (Bottom Right): L6 Pixel 10 Pro XL Edge Vision
    tmux select-pane -t "$SESSION_NAME:0.3"
    tmux split-window -v -t "$SESSION_NAME:0.3"
    tmux send-keys -t "$SESSION_NAME:0.4" "ssh pixel 'echo \"📱 L6 Pixel 10 Pro XL [Tensor G5 Edge TPU]\" && uname -a'" C-m

    # Select master orchestrator pane
    tmux select-pane -t "$SESSION_NAME:0.0"

    echo "✓ 5-Node Multiplexed Cluster initialized successfully in tmux session '${SESSION_NAME}'!"
    if [ -t 0 ] && [ "${TERM:-dumb}" != "dumb" ]; then
        tmux attach-session -t "$SESSION_NAME"
    fi
}

case "${1:-launch}" in
    --test)
        test_connections
        ;;
    --launch|launch)
        test_connections
        launch_multiplex
        ;;
    *)
        echo "Usage: $0 [--test | --launch]"
        exit 1
        ;;
esac
