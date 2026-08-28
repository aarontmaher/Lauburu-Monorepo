#!/usr/bin/env bash
# start_hub_headless.sh - Startup script for the Self-Healing Hub on Headless Linux

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "========================================="
echo " Starting Self-Healing Hub (Headless)"
echo "========================================="

if [ -d ".venv" ]; then
    echo "[*] Activating virtual environment..."
    source .venv/bin/activate
else
    echo "[!] Virtual environment not found. Please run 'uv venv' and install dependencies."
    exit 1
fi

echo "[*] Starting API Server (port 5001)..."
python3 src/api_server.py &
API_PID=$!

echo "[*] Starting Frontend Dashboard (Exposed on 0.0.0.0:5173)..."
cd frontend
# Using --host exposes the dashboard to the local network / Tailscale mesh
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

echo "[*] Starting Orchestrator State Machine..."
python3 src/orchestrator.py

echo "[*] Orchestrator stopped. Shutting down API and Frontend..."
kill $API_PID
kill $FRONTEND_PID
echo "[*] Hub cleanly shut down."
