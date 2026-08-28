#!/usr/bin/env bash
# start_hub_pixel.sh - Startup script for the Self-Healing Hub on Termux (Pixel 10)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

echo "========================================="
echo " Starting Self-Healing Hub (Termux Edge)"
echo "========================================="

# Termux doesn't need .venv by default as its Python is already isolated
echo "[*] Installing Python dependencies..."
pip install flask requests

echo "[*] Starting API Server (port 5001)..."
python3 src/api_server.py &
API_PID=$!

echo "[*] Starting Frontend Dashboard..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "[*] Starting Orchestrator State Machine..."
python3 src/orchestrator.py

# Cleanup
echo "[*] Orchestrator stopped. Shutting down API and Frontend..."
kill $API_PID
kill $FRONTEND_PID
echo "[*] Hub cleanly shut down."
