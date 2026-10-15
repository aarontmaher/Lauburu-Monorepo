#!/bin/bash
TARGET_IP="100.81.92.125"
echo "Orchestrating 24/7 --dev Training on Linux Tablet ($TARGET_IP)..."

# Wait for the Linux Tablet to finish booting and join Tailscale
MAX_RETRIES=30
RETRY_COUNT=0
while ! nc -z -w 2 $TARGET_IP 22; do
    echo "Waiting for SSH on $TARGET_IP... (Attempt $RETRY_COUNT / $MAX_RETRIES)"
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Linux Tablet failed to come online."
        exit 1
    fi
    sleep 3
done

echo "✅ SSH is active. Launching isolated tmux training session on Linux Tablet..."

# SSH into the Linux Tablet and launch the training script in a detached tmux session
ssh -o StrictHostKeyChecking=no aaron@$TARGET_IP << 'SSH_EOF'
    # Ensure Termux/Debian environment is loaded
    source ~/.bashrc || true
    
    # Path is unified via SeaweedFS DFS
    cd /Volumes/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/dual_tui_swarm_arena/
    
    # Kill existing session if it exists to prevent overlap
    tmux kill-session -t lens_dev_training 2>/dev/null || true
    
    # Launch new detached session
    tmux new-session -d -s lens_dev_training "./run_dual_tui_live.sh 247_mode"
    
    echo "🚀 24/7 --dev training successfully launched on Linux Tablet in tmux session 'lens_dev_training'"
SSH_EOF

echo "Orchestration Complete."
