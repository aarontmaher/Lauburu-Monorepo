#!/bin/bash
# ==============================================================================
# 🌐 Lauburu Mesh: Universal Docker AI Orchestrator
# ==============================================================================
# Deploys the TinyML/Router AI Docker container across the entire 7-Layer Mesh.
# Uses Tailscale IPs to ensure global, long-distance reachability regardless of
# physical location, OS, or connectivity.

# The 7-Layer Mesh IPs (Tailscale / Local)
NODES=(
    "localhost"                     # L1: Mac Host
    "10.1.0.11"                # L2: MacBook Pro (Metal RPC)
    "10.1.0.12"                 # L3: Linux Head Node
    "100.81.92.125"                 # L4: Linux Tablet
    "100.93.158.96"                 # L5: MacBook Air
    # L6 and L7 (Android Pixel/Samsung) run native Termux scripts rather than Docker,
    # but they pull from the same DFS_UNIFIED codebase.
)

COMPOSE_FILE="/Volumes/Lauburu-Monorepo/00_core_infrastructure/docker-compose.mesh-universal.yml"

echo "🚀 Igniting Universal Docker Orchestrator across all Mesh Nodes..."

for NODE in "${NODES[@]}"; do
    echo "--------------------------------------------------------"
    echo "📡 Targeting Node: $NODE"
    
    if [ "$NODE" == "localhost" ]; then
        echo "💻 Deploying locally..."
        docker-compose -f "$COMPOSE_FILE" up -d --build
    else
        echo "🌐 Deploying remotely via SSH..."
        # Using BatchMode to skip nodes that are offline or unreachable
        ssh -o BatchMode=yes -o ConnectTimeout=3 -o StrictHostKeyChecking=no "$NODE" \
            "cd /Volumes/Lauburu-Monorepo/00_core_infrastructure && docker-compose -f docker-compose.mesh-universal.yml up -d --build"
        
        if [ $? -eq 0 ]; then
            echo "✅ Successfully ignited container on $NODE"
        else
            echo "⚠️ Node $NODE is offline or unreachable. Skipping."
        fi
    fi
done

echo "--------------------------------------------------------"
echo "🌐 Global Mesh Deployment Sequence Complete."
