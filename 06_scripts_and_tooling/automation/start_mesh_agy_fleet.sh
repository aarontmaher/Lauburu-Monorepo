#!/bin/bash
# start_mesh_agy_fleet.sh
# Initializes the mesh_agy_fleet tmux session for the Lauburu AI 7-Layer Mesh.
# Handles Screen Lens Sovereign, Android CLI/SSH keepalives, and Frontier Swarm Consensus.

SESSION_NAME="mesh_agy_fleet"

# 1. API Key & Security Handler (Extract to env if needed)
# Assumes keys are handled via sovereign local extraction (Port 8082) and placed in .env
ENV_FILE="/Volumes/Lauburu-Monorepo/04_data_and_memory/.env"
if [ -f "$ENV_FILE" ]; then
    export set -a
    source "$ENV_FILE"
    export set +a
fi

# Check if session already exists
tmux has-session -t "$SESSION_NAME" 2>/dev/null

if [ $? != 0 ]; then
    echo "Creating new tmux session: $SESSION_NAME"

    # Create new session (detached) with the first window named 'dashboard'
    tmux new-session -d -s "$SESSION_NAME" -n 'dashboard'

    # Pane 0: Screen Lens Sovereign Telemetry & Control
    # Uses the canonical automation script
    tmux send-keys -t "$SESSION_NAME:dashboard.0" "echo 'Starting Screen Lens Sovereign...'" C-m
    tmux send-keys -t "$SESSION_NAME:dashboard.0" "python3 /Volumes/Lauburu-Monorepo/01_apps/screen_lens/src/mesh_universal_remote_hid_server.py" C-m

    # Split window horizontally for the Android Termux bridge
    tmux split-window -h -t "$SESSION_NAME:dashboard"
    
    # Pane 1: Android Termux/ADB bridge (Pixel 10 Pro XL)
    # Using pixel-remote-ssh identity and Tailscale IP
    tmux send-keys -t "$SESSION_NAME:dashboard.1" "echo 'Establishing Pixel 10 Pro XL SSH Bridge...'" C-m
    tmux send-keys -t "$SESSION_NAME:dashboard.1" "ssh -p 8022 -i ~/.ssh/id_ed25519 u0_a363@100.73.38.87 '~/keepalive.sh; bash'" C-m

    # Split the first pane vertically for Frontier Swarm Consensus
    tmux split-window -v -t "$SESSION_NAME:dashboard.0"
    
    # Pane 2: Frontier Swarm Consensus Execution Engine
    tmux send-keys -t "$SESSION_NAME:dashboard.2" "echo 'Initializing Frontier Swarm Consensus...'" C-m
    tmux send-keys -t "$SESSION_NAME:dashboard.2" "python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/ai/frontier_swarm_consensus.py --prompt 'Monitor and Debate Mesh State'" C-m

    # Arrange panes neatly
    tmux select-layout -t "$SESSION_NAME:dashboard" main-vertical

    # Window 1: Local AI CLIs & Jules API Autonomous Orchestration
    tmux new-window -t "$SESSION_NAME" -n 'local_ai_clis'
    
    # Pane 0: Multiplexed AI Terminal Orchestrator & Trajectory Harvester
    tmux send-keys -t "$SESSION_NAME:local_ai_clis.0" "echo 'Starting Multiplexed AI Terminal Orchestrator...'" C-m
    tmux send-keys -t "$SESSION_NAME:local_ai_clis.0" "python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/multiplexed_ai_terminal_orchestrator.py --status" C-m

    # Split for Jules API Monitor & Harvester
    tmux split-window -h -t "$SESSION_NAME:local_ai_clis"
    tmux send-keys -t "$SESSION_NAME:local_ai_clis.1" "echo 'Starting Google Jules API Monitor...'" C-m
    tmux send-keys -t "$SESSION_NAME:local_ai_clis.1" "python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/jules_api_client.py --status" C-m
else
    echo "Session $SESSION_NAME already exists. Attaching..."
fi

# Attach to the session if not running in headless daemon mode
if [ -z "$TMUX" ]; then
    tmux attach-session -t "$SESSION_NAME"
fi

