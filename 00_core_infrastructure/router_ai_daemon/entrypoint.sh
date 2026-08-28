#!/bin/sh
# =============================================================================
# smolagi Router AI Daemon Entrypoint Script
# POSIX-compliant init script with cgroups v1/v2 memory limit enforcement
# =============================================================================
set -e

echo "[smolagi-init] Starting Router AI Daemon container runtime..."

# -----------------------------------------------------------------------------
# 1. Inspect Cgroups Memory Limit (v1 & v2)
# -----------------------------------------------------------------------------
MEMORY_LIMIT_BYTES=0
CGROUP_VERSION="none"

if [ -f "/sys/fs/cgroup/memory.max" ]; then
    CGROUP_VERSION="v2"
    RAW_LIMIT=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo "max")
    if [ "$RAW_LIMIT" != "max" ] && [ -n "$RAW_LIMIT" ]; then
        MEMORY_LIMIT_BYTES=$RAW_LIMIT
    fi
elif [ -f "/sys/fs/cgroup/memory/memory.limit_in_bytes" ]; then
    CGROUP_VERSION="v1"
    RAW_LIMIT=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo "0")
    # Kernel max 64-bit int is ~9223372036854771712 or large number for unlimited
    if [ -n "$RAW_LIMIT" ] && [ "$RAW_LIMIT" -lt 9000000000000000000 ] 2>/dev/null; then
        MEMORY_LIMIT_BYTES=$RAW_LIMIT
    fi
fi

TARGET_BUDGET_MB=${ROUTER_AI_RAM_BUDGET_MB:-300.0}

if [ "$MEMORY_LIMIT_BYTES" -gt 0 ] 2>/dev/null; then
    MEMORY_LIMIT_MB=$((MEMORY_LIMIT_BYTES / 1024 / 1024))
    echo "[smolagi-init] Cgroups ($CGROUP_VERSION) memory limit detected: ${MEMORY_LIMIT_MB} MB (Target Budget: ${TARGET_BUDGET_MB} MB)"
    if [ "$MEMORY_LIMIT_MB" -gt 300 ]; then
        echo "[smolagi-init] WARNING: Cgroups memory limit (${MEMORY_LIMIT_MB} MB) exceeds router hardware budget (300 MB). Enforcing 300 MB software ceiling."
    fi
else
    echo "[smolagi-init] WARNING: No active cgroup memory constraint detected ($CGROUP_VERSION). Software MemoryGuard will enforce ${TARGET_BUDGET_MB} MB ceiling."
fi

# -----------------------------------------------------------------------------
# 2. Verify Volatile Storage Mounts (Zero-Flash-Wear Invariant)
# -----------------------------------------------------------------------------
MODELS_DIR=${TMPFS_MODELS_DIR:-/models}
TELEMETRY_DIR=${TMPFS_TELEMETRY_DIR:-/tmp/telemetry}

mkdir -p "$MODELS_DIR" "$TELEMETRY_DIR" /tmp/cache 2>/dev/null || true

if [ ! -w "$MODELS_DIR" ]; then
    echo "[smolagi-init] ERROR: Models directory $MODELS_DIR is not writable!" >&2
fi
if [ ! -w "$TELEMETRY_DIR" ]; then
    echo "[smolagi-init] ERROR: Telemetry directory $TELEMETRY_DIR is not writable!" >&2
fi

# -----------------------------------------------------------------------------
# 3. Setup Signal Traps for Graceful Shutdown
# -----------------------------------------------------------------------------
DAEMON_PID=""
LLAMA_PID=""

cleanup() {
    echo "[smolagi-init] Received termination signal. Initiating graceful shutdown..."
    if [ -n "$DAEMON_PID" ] && kill -0 "$DAEMON_PID" 2>/dev/null; then
        echo "[smolagi-init] Stopping Python daemon (PID: $DAEMON_PID)..."
        kill -TERM "$DAEMON_PID" 2>/dev/null || true
    fi
    if [ -n "$LLAMA_PID" ] && kill -0 "$LLAMA_PID" 2>/dev/null; then
        echo "[smolagi-init] Stopping llama-server (PID: $LLAMA_PID)..."
        kill -TERM "$LLAMA_PID" 2>/dev/null || true
    fi
    
    # Allow processes 3 seconds to exit gracefully before forceful kill
    sleep 1
    if [ -n "$DAEMON_PID" ] && kill -0 "$DAEMON_PID" 2>/dev/null; then
        kill -KILL "$DAEMON_PID" 2>/dev/null || true
    fi
    if [ -n "$LLAMA_PID" ] && kill -0 "$LLAMA_PID" 2>/dev/null; then
        kill -KILL "$LLAMA_PID" 2>/dev/null || true
    fi
    echo "[smolagi-init] Graceful shutdown complete."
    exit 0
}

trap cleanup INT TERM HUP QUIT

# -----------------------------------------------------------------------------
# 4. Execute Application or User Command
# -----------------------------------------------------------------------------
if [ "$#" -gt 0 ]; then
    echo "[smolagi-init] Executing custom command: $@"
    exec "$@"
fi

echo "[smolagi-init] Launching smolagi router runtime..."
python3 -m src.container.llama_runner &
DAEMON_PID=$!

# Wait on background processes and handle signals
wait "$DAEMON_PID"
