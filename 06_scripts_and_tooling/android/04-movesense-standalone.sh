#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Movesense Standalone Daemon Boot Script for Pixel 10 Pro XL
# Ensures Movesense Biometrics & TinyML Engine run standalone by default at the gym
# ==============================================================================

export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export PATH=$PREFIX/bin:$PATH

# 1. Acquire Android Wake Lock to prevent OS Doze mode
termux-wake-lock 2>/dev/null || true

# 2. Start Movesense Readiness & TinyML Standalone Engine on Port 8086
if ! nc -z 127.0.0.1 8086 >/dev/null 2>&1 && ! pgrep -f "movesense-readiness/main.py" >/dev/null 2>&1; then
    cd "$HOME/movesense-readiness" 2>/dev/null || cd "$HOME"
    if command -v tmux >/dev/null 2>&1; then
        tmux has-session -t movesense-hub 2>/dev/null || tmux new-session -d -s movesense-hub "python3 $HOME/movesense-readiness/main.py"
    else
        nohup python3 "$HOME/movesense-readiness/main.py" > "$HOME/movesense-readiness/movesense_daemon.log" 2>&1 &
    fi
fi

# 3. Ensure Lauburu Headless Background Worker (Port 4051 & biometrics pipe) is active
if ! pgrep -f "lauburu worker" >/dev/null 2>&1 && ! pgrep -f "lauburu bt-daemon" >/dev/null 2>&1; then
    nohup "$PREFIX/bin/lauburu" worker > "$PREFIX/tmp/lauburu_worker.log" 2>&1 &
fi
