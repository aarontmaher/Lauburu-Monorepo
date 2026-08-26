#!/bin/zsh
# ============================================================
# LAUBURU MESH — LAUNCH ALL LOCALHOST SERVICES
# ============================================================
set -e

echo "🚀 Launching Lauburu Mesh Services..."
echo ""

# Kill any stale processes on our ports
for port in 18800 18888 4005; do
  pid=$(lsof -ti:$port 2>/dev/null | head -1)
  if [ -n "$pid" ]; then
    kill $pid 2>/dev/null && echo "  Cleared port :$port (PID $pid)"
  fi
done
sleep 1

# 1. AI Sharding Daemon — port 18800
echo "  [1/4] AI Sharding Daemon → http://localhost:18800"
cd ~/teamwork_projects/ai_sharding_daemon
nohup uv run python -m src.main --host 127.0.0.1 --port 18800 > /tmp/sharding_daemon.log 2>&1 &
SHARD_PID=$!
sleep 3

# 2. Termius TUI API — port 18888
echo "  [2/4] Termius TUI API → http://localhost:18888"
cd ~/teamwork_projects/termius_tui_dashboard
nohup uv run python -c "
import asyncio, sys
sys.path.insert(0, '.')
from termius_tui.api.server import APIServer
from termius_tui.core.state import MeshStateManager
async def main():
    srv = APIServer(MeshStateManager(), host='0.0.0.0', port=18888)
    await srv.start()
    while True: await asyncio.sleep(5)
asyncio.run(main())
" > /tmp/termius_api.log 2>&1 &
TUI_PID=$!
sleep 2

# 3. Software Dev Training Game — port 4005
echo "  [3/4] Software Dev Training Game → http://localhost:4005"
cd ~/teamwork_projects/software_dev_training_game
nohup uv run python -c "
from src.web.server import start_dashboard_server
import time
start_dashboard_server(port=4005)
while True: time.sleep(10)
" > /tmp/softdev_game.log 2>&1 &
GAME_PID=$!
sleep 2

# 4. AI Strengthening Game — continuous training loop
echo "  [4/4] AI Strengthening Game → headless training loop"
cd ~/teamwork_projects/ai_strengthening_training_game
nohup uv run python run_game.py --rounds 999 --headless > /tmp/ai_strengthening.log 2>&1 &
AI_PID=$!

echo ""
echo "✅ All services launched!"
echo ""
echo "  AI Sharding Daemon:      http://localhost:18800/v1/health"
echo "  Termius TUI API:         http://localhost:18888/api/v1/health"
echo "  Software Dev Game:       http://localhost:4005"
echo "  AI Strengthening Game:   tail -f /tmp/ai_strengthening.log"
echo ""
echo "  Termius TUI (terminal):  cd ~/teamwork_projects/termius_tui_dashboard && uv run termius-tui"
