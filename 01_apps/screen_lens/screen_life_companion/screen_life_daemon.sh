#!/usr/bin/env bash
# ==============================================================================
# Lauburu Screen Life Companion: Standalone Daemon Control
# Subsystem: 01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh
# Lauburu Mesh Ecosystem — 2026
# ==============================================================================

set -euo pipefail

DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion"
SCRIPT="$DIR/screen_life_companion.py"
PID_DIR="$HOME/.lauburu"
PID_FILE="$PID_DIR/screen_life_companion.pid"
LOG_FILE="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs/screen_life_companion.log"
LENS_BIN="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/bin/lauburu-lens"

mkdir -p "$PID_DIR" "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs"

case "${1:-status}" in
    start)
        echo "========================================================================"
        echo "🧠 Starting Lauburu Screen Life Companion Daemon..."
        echo "========================================================================"

        # 1. Ensure native lauburu-lens daemon is running
        if [ -x "$LENS_BIN" ]; then
            if "$LENS_BIN" status | grep -q "STOPPED"; then
                echo "👁️  Activating native macOS Screen Lens capture engine..."
                "$LENS_BIN" start --daemon --interval 2.0
            else
                echo "👁️  Native macOS Screen Lens capture engine is ALIVE."
            fi
        fi

        # 2. Start Screen Life Companion Service
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "ℹ️  Screen Life Companion is already running (PID: $(cat "$PID_FILE"))"
        else
            PYTHON_EXEC="/Users/aaron/.lauburu/companion_venv/bin/python"
            if [ ! -f "$PYTHON_EXEC" ]; then
                PYTHON_EXEC="python3"
            fi
            nohup "$PYTHON_EXEC" -u "$SCRIPT" > "$LOG_FILE" 2>&1 &
            echo $! > "$PID_FILE"
            echo "✅ Started Screen Life Companion Daemon (PID: $(cat "$PID_FILE"))"
            echo "   Dashboard: http://127.0.0.1:3036"
            echo "   Log File : $LOG_FILE"
        fi
        ;;

    stop)
        echo "🛑 Stopping Lauburu Screen Life Companion..."
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                echo "✅ Stopped Screen Life Companion (PID: $PID)"
            fi
            rm -f "$PID_FILE"
        else
            echo "ℹ️  No active PID file found."
        fi
        pkill -f "screen_life_companion.py" 2>/dev/null || true
        lsof -ti :3036 | xargs kill -9 2>/dev/null || true
        ;;

    status)
        echo "========================================================================"
        echo "📊 Lauburu Screen Life Companion Status"
        echo "========================================================================"
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "🟢 Service Status: RUNNING (PID: $(cat "$PID_FILE"))"
            echo "🌐 Web Dashboard: http://127.0.0.1:3036"
            echo "📄 Log Output:"
            tail -n 5 "$LOG_FILE" 2>/dev/null || true
        else
            echo "🔴 Service Status: STOPPED"
        fi
        echo "========================================================================"
        ;;

    restart)
        $0 stop
        sleep 1
        $0 start
        ;;

    open-ui)
        open "http://127.0.0.1:3036"
        ;;

    *)
        echo "Usage: $0 {start|stop|status|restart|open-ui}"
        exit 1
        ;;
esac

# Start the Continuous Priority Training Governor
GOV_SCRIPT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/scripts/lens_training_governor.py"
GOV_LOG="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs/lens_training_governor.log"
if pgrep -f "lens_training_governor.py" > /dev/null; then
    echo "🧠 Training Governor is already running."
else
    echo "🚀 Starting 24/7 Priority Training Governor..."
    nohup python3 -u "$GOV_SCRIPT" > "$GOV_LOG" 2>&1 &
fi
