#!/bin/bash
# ==============================================================================
# Lauburu Mesh Ecosystem — Live Red/Blue Arena & Device Settings --dev Launcher
# ==============================================================================

PROJECT_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
cd "$PROJECT_DIR"

export PYTHONPATH="$PROJECT_DIR/01_apps/canonical_port/tui:$PROJECT_DIR/01_apps/canonical_port:$PROJECT_DIR/05_agents_and_swarms/red_blue_arena:$PROJECT_DIR/00_core_infrastructure/self_healing_hub/src:${PYTHONPATH:-}"

echo "======================================================================"
echo "🚀 LAUNCHING LAUBURU LIVE --DEV ARENA & DEVICE SETTINGS COCKPIT"
echo "======================================================================"

# Ensure real Movesense BLE daemon is running
if ! ps aux | grep "run_real_movesense_daemon.py" | grep -v grep > /dev/null; then
    echo "Starting Movesense 261030002013 BLE daemon..."
    nohup /Users/aaron/DFS_UNIFIED/lora_datasets/.venv/bin/python 03_biometrics_and_telemetry/run_real_movesense_daemon.py > /tmp/movesense_ble.log 2>&1 &
fi

# Execute initial clean-room device sandbox mutation & 3D fusion
python3 05_agents_and_swarms/red_blue_arena/device_settings_sandbox.py >/dev/null 2>&1 || true
python3 00_core_infrastructure/self_healing_hub/src/spatial_3d_unified_fusion.py >/dev/null 2>&1 || true

VENV_PYTHON="$PROJECT_DIR/01_apps/canonical_port/.venv/bin/python"
VENV_TEXTUAL="$PROJECT_DIR/01_apps/canonical_port/.venv/bin/textual"
PYTHON_BIN="$([ -f "$VENV_PYTHON" ] && echo "$VENV_PYTHON" || echo "python3")"
TEXTUAL_BIN="$([ -f "$VENV_TEXTUAL" ] && echo "$VENV_TEXTUAL" || echo "textual")"

# Launch the live interactive Textual --dev Cockpit
if [ "$1" = "--dev" ] || [ "$1" = "dev" ]; then
    echo "⚡ Starting in Textual v8 --dev live reload mode..."
    shift || true
    exec "$TEXTUAL_BIN" run --dev 01_apps/canonical_port/tui/tui_live_arena_dev.py "$@"
else
    exec "$PYTHON_BIN" 01_apps/canonical_port/tui/tui_live_arena_dev.py "$@"
fi
