#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Lauburu Mesh Worker Android 24/7 Keepalive Script (Termux Edge Layer)
# Governed by Rule 0 (Zero-Mock), Rule 3 (Host Sanctuary), and Rule 4 (Keepalive)
# ==============================================================================

# 1. Acquire Android wakelock to prevent CPU deep sleep
termux-wake-lock

# 2. Setup Termux environment
export PREFIX="/data/data/com.termux/files/usr"
export PATH="$PREFIX/bin:$PREFIX/bin/applets:$PATH"
export TMPDIR="$PREFIX/tmp"
mkdir -p "$TMPDIR" "$PREFIX/var/log"

WORKER_BIN="$PREFIX/bin/lauburu"
if [ ! -f "$WORKER_BIN" ]; then
    WORKER_BIN="/data/data/com.termux/files/home/lauburu_android"
fi

if [ ! -f "$WORKER_BIN" ]; then
    echo "❌ Lauburu worker binary not found in Termux."
    exit 1
fi

chmod +x "$WORKER_BIN"

echo "⚡ Starting Lauburu Autonomous Headless Mesh Worker on Android..."
echo "• Movesense BLE: 0x180D Scanner & Pan-Tompkins QRS Active"
echo "• IP-less Link: Layer 0 Bluetooth Radio MAC (0.0.0.0)"
echo "• TCP Bridge: :4050 / :4051"

# Launch under tmux or nohup in the background
if command -v tmux &> /dev/null; then
    tmux has-session -t lauburu-worker 2>/dev/null
    if [ $? != 0 ]; then
        tmux new-session -d -s lauburu-worker "$WORKER_BIN worker"
        echo "✅ Worker running in tmux session 'lauburu-worker'."
    else
        echo "ℹ️ Session 'lauburu-worker' already running."
    fi
else
    nohup "$WORKER_BIN" worker > "$PREFIX/var/log/lauburu_worker.log" 2>&1 &
    echo "✅ Worker launched via nohup (PID: $!)."
fi
