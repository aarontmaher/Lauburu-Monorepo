#!/bin/bash
export PATH="/Users/aaron/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
# Port 8082 is governed by mesh_multiport_bridge.py routing to linuxmini:8083
if ! pgrep -f "mesh_multiport_bridge.py" >/dev/null 2>&1; then
    exec /usr/bin/python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/mesh_multiport_bridge.py
fi
while true; do sleep 60; done
