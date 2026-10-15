#!/usr/bin/env bash

# tmux IDE startup script for Lauburu-Monorepo
# This script mirrors the behavior of zellij_ide.kdl

SESSION="ide_workspace"
REPO_DIR="/Volumes/Lauburu-Monorepo"

# Check if session exists
tmux has-session -t $SESSION 2>/dev/null
if [ $? -ne 0 ]; then
    # Create new detached session with name $SESSION
    tmux new-session -d -s $SESSION -n "IDE_Workspace" -c "$REPO_DIR"

    # Window 1: IDE & Workspace
    # Pane 0 (left): nvim
    tmux send-keys -t $SESSION:0.0 "nvim ." C-m
    
    # Split pane horizontally (creates right pane 1)
    tmux split-window -h -t $SESSION:0 -c "$REPO_DIR"
    
    # In the right pane, split vertically twice to make 3 panes total on the right
    tmux split-window -v -t $SESSION:0.1 -c "$REPO_DIR"
    tmux split-window -v -t $SESSION:0.2 -c "$REPO_DIR"
    
    # Resize the left pane (nvim) to take ~60% of the screen width
    tmux resize-pane -t $SESSION:0.0 -x 60%

    # Right pane 1 (top): JupyterLab / Cyber Studio
    tmux send-keys -t $SESSION:0.1 "uv run jupyter lab --no-browser" C-m
    
    # Right pane 2 (middle): Orchestrator Logs
    tmux send-keys -t $SESSION:0.2 "tail -f obsidian_vault/04_ANALYTICS/lens_telemetry.md" C-m
    
    # Right pane 3 (bottom): System Telemetry
    tmux send-keys -t $SESSION:0.3 "glances" C-m

    # Select pane 0
    tmux select-pane -t $SESSION:0.0

    # Window 2: Local AI CLIs & Jules
    tmux new-window -t $SESSION -n "AI_CLIs" -c "$REPO_DIR"
    
    # Pane 0 (left): Multiplexed AI Terminal Orchestrator
    tmux send-keys -t $SESSION:1.0 "python3 06_scripts_and_tooling/automation/multiplexed_ai_terminal_orchestrator.py --status" C-m
    
    # Split horizontally (creates pane 1)
    tmux split-window -h -t $SESSION:1 -c "$REPO_DIR"
    
    # Split right pane vertically (creates pane 2)
    tmux split-window -v -t $SESSION:1.1 -c "$REPO_DIR"
    
    # Right pane 1 (top): Google Jules API Client
    tmux send-keys -t $SESSION:1.1 "python3 06_scripts_and_tooling/automation/jules_api_client.py --status" C-m
    
    # Right pane 2 (bottom): Pi & Junie Terminal Runner
    tmux send-keys -t $SESSION:1.2 "# Pi & Junie Terminal Runner" C-m

    # Select the first window again
    tmux select-window -t $SESSION:0
fi

# Attach to session
tmux attach-session -t $SESSION
