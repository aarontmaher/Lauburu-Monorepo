#!/bin/bash
# ==============================================================================
# Lauburu Mesh Ecosystem — Live Red/Blue Arena & Device Settings --dev Launcher
# ==============================================================================

PROJECT_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
cd "$PROJECT_DIR"

echo "======================================================================"
echo "🚀 LAUNCHING LAUBURU LIVE --DEV ARENA & DEVICE SETTINGS COCKPIT"
echo "======================================================================"

# Ensure real Movesense BLE daemon is running
if ! ps aux | grep "run_real_movesense_daemon.py" | grep -v grep > /dev/null; then
    echo "Starting Movesense 261030002013 BLE daemon..."
    nohup /Users/aaron/DFS_UNIFIED/lora_datasets/.venv/bin/python 03_biometrics_and_telemetry/run_real_movesense_daemon.py > /tmp/movesense_ble.log 2>&1 &
fi

# Execute one clean-room device sandbox mutation
python3 05_agents_and_swarms/red_blue_arena/device_settings_sandbox.py

# Launch the live interactive Textual --dev Cockpit
python3 01_apps/canonical_port/tui/tui_live_arena_dev.py "$@"
