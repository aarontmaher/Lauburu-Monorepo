#!/bin/bash
export PATH="/Users/aaron/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
pkill -f "mesh_multiport_bridge.py" 2>/dev/null || true
exec /usr/bin/python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/mesh_multiport_bridge.py
