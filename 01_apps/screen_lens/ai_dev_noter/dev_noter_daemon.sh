#!/usr/bin/env bash
# ==============================================================================
# Lauburu AI Project Development Historian Daemon Control Script
# ==============================================================================

DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/ai_dev_noter"
SCRIPT="$DIR/lauburu_dev_historian.py"
PID_FILE="$HOME/.lauburu/dev_historian.pid"
LOG_FILE="$HOME/.lauburu/dev_historian.log"

mkdir -p "$HOME/.lauburu"

case "$1" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "⚠️  Lauburu Development Historian is already running (PID: $(cat "$PID_FILE"))"
            exit 0
        fi
        echo "🚀 Starting Lauburu Development Historian Daemon..."
        nohup python3 "$SCRIPT" --daemon --interval 15.0 > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        echo "✅ Started background Historian Daemon (PID: $(cat "$PID_FILE"))"
        echo "   Log: $LOG_FILE"
        ;;
    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                echo "🛑 Stopped Lauburu Development Historian (PID: $PID)"
            else
                echo "ℹ️  Daemon process not active."
            fi
            rm -f "$PID_FILE"
        else
            echo "ℹ️  No PID file found."
        fi
        ;;
    status)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "🟢 Lauburu Development Historian is RUNNING (PID: $(cat "$PID_FILE"))"
            echo "   Log File: $LOG_FILE"
            tail -n 10 "$LOG_FILE"
        else
            echo "🔴 Lauburu Development Historian is STOPPED"
        fi
        ;;
    sync|once)
        echo "⚡ Triggering immediate AI development structuring pass..."
        python3 "$SCRIPT" --once
        ;;
    *)
        echo "Usage: $0 {start|stop|status|sync}"
        exit 1
        ;;
esac
