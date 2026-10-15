#!/bin/bash
set -e
echo "🌿 Deploying Syncthing for Lauburu DFS_UNIFIED over Thunderbolt 4..."
if ! command -v syncthing &> /dev/null; then
    echo "Syncthing not found. Installing via Homebrew..."
    brew install syncthing
fi
echo "Starting Syncthing daemon..."
brew services start syncthing
sleep 3
echo "Opening Syncthing Web UI on http://localhost:8384"
open http://localhost:8384
echo "=========================================================="
echo "✅ Syncthing deployed locally."
echo "ACTION REQUIRED: Run this exact script on the Mac Mini M2."
echo "Then, in the Web UI on the M2, click 'Add Folder', point it to:"
echo "   /Users/Shared/aaron/DFS_UNIFIED"
echo "and share it with this Mac Mini (M4) over the Thunderbolt IP (169.254.x.x)."
echo "=========================================================="
