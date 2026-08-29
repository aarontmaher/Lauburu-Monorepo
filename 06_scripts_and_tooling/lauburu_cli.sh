#!/bin/bash
# ==============================================================================
# Lauburu Mesh Ecosystem — Master Unified Global CLI
# ==============================================================================
# Single-word global commands:
#   lauburu           -> Launch full Canonical 9-Screen TUI Command Center
#   lauburu dev       -> Launch Live Side-by-Side Dual Graphical Arena (--dev)
#   lauburu arena     -> Launch Live Side-by-Side Dual Graphical Arena (--dev)
#   lauburu map       -> Run Unified 3D Spatial Fusion Engine
#   lauburu movesense -> Check / restart Movesense BLE GATT 128Hz daemon
#   tui               -> Fast alias for 'lauburu'
#   arena             -> Fast alias for 'lauburu dev'
# ==============================================================================

MONOREPO_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
TUI_DIR="$MONOREPO_DIR/01_apps/canonical_port"

# Detect invoked command name
INVOKED_CMD=$(basename "$0")

if [ "$INVOKED_CMD" = "arena" ]; then
    CMD="arena"
elif [ "$INVOKED_CMD" = "tui" ]; then
    CMD="tui"
else
    CMD="${1:-tui}"
    shift || true
fi

case "$CMD" in
    tui|"")
        echo "🚀 Launching Lauburu Canonical TUI Command Center (Live --dev Mode)..."
        cd "$TUI_DIR"
        exec ./run_live_tui.sh --dev "$@"
        ;;
    --dev|dev|arena)
        echo "🚀 Launching Lauburu Live Side-by-Side Dual Graphical Arena (--dev)..."
        cd "$TUI_DIR"
        exec ./run_live_arena_dev.sh "$@"
        ;;
    map)
        echo "🌐 Running Unified 3D Spatial Fusion Engine..."
        cd "$MONOREPO_DIR"
        python3 00_core_infrastructure/self_healing_hub/src/spatial_3d_unified_fusion.py
        ;;
    movesense)
        echo "💓 Checking Movesense 261030002013 BLE daemon status..."
        if ps aux | grep "run_real_movesense_daemon.py" | grep -v grep > /dev/null; then
            echo "✅ Movesense BLE daemon is ACTIVE and streaming live packets."
        else
            echo "⚠️ Movesense daemon not running. Starting background streamer..."
            nohup /Users/aaron/DFS_UNIFIED/lora_datasets/.venv/bin/python "$MONOREPO_DIR/03_biometrics_and_telemetry/run_real_movesense_daemon.py" > /tmp/movesense_ble.log 2>&1 &
            echo "✅ Started Movesense BLE daemon."
        fi
        ;;
    help|--help|-h)
        echo "======================================================================"
        echo "🌟 LAUBURU MESH UNIFIED GLOBAL CLI"
        echo "======================================================================"
        echo "Usage: lauburu [command] [options]"
        echo ""
        echo "Commands:"
        echo "  lauburu (or tui)     Launch full Canonical 9-Screen TUI Command Center"
        echo "  lauburu dev (or arena) Launch Live Side-by-Side Dual Graphical Arena"
        echo "  lauburu map          Run Unified 3D Spatial Fusion Engine"
        echo "  lauburu movesense    Check / Start Physical Movesense 128Hz BLE daemon"
        echo "  lauburu help         Show this help message"
        echo "======================================================================"
        ;;
    *)
        echo "Unknown command: $CMD"
        echo "Run 'lauburu help' for available commands."
        exit 1
        ;;
esac
