#!/bin/bash
# Lauburu Cable & Mesh Analyzer Server Launcher (Port 4007)
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/../../"

echo "⚡ Starting Lauburu Cable & Mesh Analyzer on Port 4007..."
export PYTHONPATH="$DIR/../../:$PYTHONPATH"
python3 -m uvicorn "01_apps.network_cable_analyzer.backend.server:app" --host 0.0.0.0 --port 4007
