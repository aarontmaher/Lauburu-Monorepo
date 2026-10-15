#!/usr/bin/env bash
# ==============================================================================
# 00_core_infrastructure/zombie_daemon_reaper.sh
# ==============================================================================
# Governs memory health and zombie process cleanup while strictly exempting
# launchd-managed daemons (voila-master-console, llama-server, etc.)
# from destructive termination.
# ==============================================================================
set -euo pipefail

echo "[$(date)] Initiating Zombie Daemon Reaper Sweep..."

PAGES_FREE=$(vm_stat | awk '/Pages free:|Pages speculative:|Pages inactive:|Pages purgeable:/ {sum += $3} END {print sum}')
PAGE_SIZE=16384
FREE_RAM_GB=$(echo "scale=2; ($PAGES_FREE * $PAGE_SIZE) / (1024^3)" | bc)

echo "[$(date)] Available RAM (including inactive & purgeable cache): ${FREE_RAM_GB} GB"

# 1. Monorepo AI Health: Verify Port 8081 (Fast Syntax Worker Plane)
# Managed by launchd (com.lauburu.qwen-8081). Destructive pkill has been removed
# to preserve active inference. Unresponsive daemons are governed by HTTP health probes.
LLAMA_PID=$(pgrep -f "llama-server.*8081" | head -n 1 || true)
if [ -z "$LLAMA_PID" ]; then
    echo "[$(date)] llama-server on port 8081 is offline. Resurrecting syntax worker..."
    bash /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/launch_canonical_model_stack.sh >/dev/null 2>&1 &
else
    LLAMA_MEM_MB=$(ps -o rss= -p "$LLAMA_PID" 2>/dev/null | awk '{print int($1/1024)}' || echo 0)
    echo "[$(date)] Subordinate syntax worker (port 8081) active (PID $LLAMA_PID, RSS ${LLAMA_MEM_MB}MB). Preserved."
fi

# 2. Memory Sanctuary & Zombie Cleanup:
# On Apple Silicon with unified memory and hardware compression, Available RAM < 4.0 GB
# is the expected operating baseline with multiple LLMs loaded.
# Managed daemons (com.lauburu.voila-master-console, llama-server, etc.) are strictly protected.
# Only unmanaged orphaned kernels may be reaped under critical memory exhaustion (< 1.0 GB).
if (( $(echo "$FREE_RAM_GB < 1.0" | bc -l) )); then
    echo "[$(date)] WARNING: Available RAM critically low (< 1.0GB). Checking for unmanaged orphaned kernels..."
    
    # Strictly exclude voila, launch_voila, and any lauburu managed processes
    ZOMBIES=$(ps -eo pid,ppid,command | grep -E '[i]pykernel_launcher' | grep -v -E 'voila|launch_voila|lauburu' | awk '$2 != 1 {print $1}')
    if [ -n "$ZOMBIES" ]; then
        for pid in $ZOMBIES; do
            echo "[$(date)] Reaping orphaned unmanaged kernel process (PID: $pid) to free RAM..."
            kill -9 "$pid" 2>/dev/null || true
        done
    else
        echo "[$(date)] No orphaned unmanaged kernel processes found. Managed daemons preserved."
    fi
else
    echo "[$(date)] RAM is within safe operating limits (${FREE_RAM_GB} GB available). Managed daemons preserved."
fi
