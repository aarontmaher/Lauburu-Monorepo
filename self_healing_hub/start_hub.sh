#!/usr/bin/env bash
# start_hub.sh - Unified startup script for the Self-Healing Hub

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "========================================="
echo " Starting Self-Healing Hub Orchestrator"
echo "========================================="

# 1. Activate Virtual Environment
if [ -d ".venv" ]; then
    echo "[*] Activating virtual environment..."
    source .venv/bin/activate
else
    echo "[!] Virtual environment not found. Please run 'uv venv' and install dependencies."
    exit 1
fi

# 2. Start API Server (Background)
echo "[*] Starting API Server (port 5000)..."
python3 src/api_server.py &
API_PID=$!

# 3. Start Frontend Dashboard (Background)
echo "[*] Starting Frontend Dashboard..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# 4. Start Python Orchestrator (Foreground)
echo "[*] Starting Orchestrator State Machine..."
python3 src/orchestrator.py

# Cleanup if orchestrator stops
echo "[*] Orchestrator stopped. Shutting down API and Frontend..."
kill $API_PID
kill $FRONTEND_PID
echo "[*] Hub cleanly shut down."
