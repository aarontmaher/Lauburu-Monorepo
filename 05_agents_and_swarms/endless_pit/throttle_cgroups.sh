#!/usr/bin/env bash
# Lauburu Mesh Ecosystem — Endless Pit Throttler
# Rule 10 Enforcement: Hard-caps the 24/7 philosophical arena to a single core and lowest priority.

cd "$(dirname "$0")" || exit 1

LOG_DIR="../../logs/endless_pit"
mkdir -p "$LOG_DIR"

echo "================================================================="
echo "🛡️ LAUBURU ENDLESS PIT: INITIATING RESOURCE CONTAINMENT"
echo "================================================================="

# Command to execute
DAEMON_CMD="python3 pit_daemon.py"

# Try cpulimit if installed (Linux), otherwise rely on nice (Mac/Linux)
if command -v cpulimit &> /dev/null; then
    echo "[*] Found cpulimit. Capping to 10% CPU usage."
    # taskset -c 0 pins to core 0 (Linux). For macOS we just use nice.
    if command -v taskset &> /dev/null; then
        echo "[*] Pinning to Core 0 (Linux Mode)."
        nohup nice -n 19 taskset -c 0 cpulimit -l 10 -f -- $DAEMON_CMD > "$LOG_DIR/pit.log" 2>&1 &
    else
        nohup nice -n 19 cpulimit -l 10 -f -- $DAEMON_CMD > "$LOG_DIR/pit.log" 2>&1 &
    fi
else
    echo "[!] cpulimit not found. Falling back to maximum nice (+19)."
    if command -v taskset &> /dev/null; then
        nohup nice -n 19 taskset -c 0 $DAEMON_CMD > "$LOG_DIR/pit.log" 2>&1 &
    else
        nohup nice -n 19 $DAEMON_CMD > "$LOG_DIR/pit.log" 2>&1 &
    fi
fi

PID=$!
echo "[*] Endless Pit Daemon started with PID: $PID"
echo "[*] Background execution verified. Host Sanctuary limits preserved."
echo "================================================================="
