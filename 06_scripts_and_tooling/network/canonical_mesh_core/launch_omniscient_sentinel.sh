#!/usr/bin/env bash
# ==============================================================================
# Omniscient Mesh Sentinel Lifecycle Controller
# ==============================================================================
# Usage:
#   ./launch_omniscient_sentinel.sh start [--interval SEC]
#   ./launch_omniscient_sentinel.sh stop
#   ./launch_omniscient_sentinel.sh status
#   ./launch_omniscient_sentinel.sh test
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="/Users/aaron/primary_workstation_venv/bin/python"
SENTINEL_SCRIPT="$SCRIPT_DIR/omniscient_mesh_sentinel.py"
PID_FILE="/tmp/omniscient_mesh_sentinel.pid"
LOG_FILE="/Volumes/Lauburu-Monorepo/logs/omniscient_mesh_sentinel.log"

mkdir -p "$(dirname "$LOG_FILE")"

case "$1" in
    start)
        INTERVAL="${2:-3.0}"
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "⚠️ Omniscient Mesh Sentinel is already running (PID: $(cat "$PID_FILE"))."
            exit 0
        fi
        echo "🚀 Starting Omniscient Mesh Sentinel (Interval: ${INTERVAL}s)..."
        nohup "$PYTHON_EXEC" "$SENTINEL_SCRIPT" --interval "$INTERVAL" >> "$LOG_FILE" 2>&1 &
        PID=$!
        echo "$PID" > "$PID_FILE"
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ Omniscient Mesh Sentinel started successfully (PID: $PID)."
            echo "   Log: $LOG_FILE"
        else
            echo "❌ Failed to start sentinel. Check logs: $LOG_FILE"
            exit 1
        fi
        ;;

    stop)
        echo "🛑 Stopping Omniscient Mesh Sentinel..."
        if [ -f "$PID_FILE" ]; then
            PID="$(cat "$PID_FILE")"
            kill "$PID" 2>/dev/null || true
            rm -f "$PID_FILE"
        fi
        pkill -f "omniscient_mesh_sentinel.py" 2>/dev/null || true
        sleep 1
        echo "✅ Sentinel stopped."
        ;;

    status)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "🟢 Omniscient Mesh Sentinel is RUNNING (PID: $(cat "$PID_FILE"))."
            echo "--- Recent Telemetry ---"
            cat "/Volumes/Lauburu-Monorepo/04_data_and_memory/omniscient_mesh_telemetry.json" 2>/dev/null | head -n 25 || true
        else
            echo "🔴 Omniscient Mesh Sentinel is STOPPED."
        fi
        ;;

    test)
        echo "🧪 Running one-shot test sweep..."
        "$PYTHON_EXEC" "$SENTINEL_SCRIPT" --once
        ;;

    *)
        echo "Usage: $0 {start|stop|status|test} [interval_seconds]"
        exit 1
        ;;
esac
