#!/usr/bin/env bash
# ==============================================================================
# 🧹 Automated Docker Storage Hygiene Daemon
# Subsystem: 00_core_infrastructure/docker/docker_storage_hygiene_daemon.sh
# Prevents APFS container disk starvation by pruning Docker build caches & images.
# ==============================================================================

set -euo pipefail

LOG_FILE="/tmp/docker_storage_hygiene.log"
MIN_FREE_GB=15
CHECK_INTERVAL_SEC=1800 # 30 minutes

function log_msg() {
    echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [DockerHygiene] $1" | tee -a "$LOG_FILE"
}

function run_hygiene_check() {
    # 1. Check free disk space in GB on root mount
    local free_kb
    free_kb=$(df -k / | awk 'NR==2 {print $4}')
    local free_gb=$((free_kb / 1024 / 1024))

    log_msg "Current APFS root available space: ${free_gb} GB (Threshold: ${MIN_FREE_GB} GB)"

    if ! command -v docker >/dev/null 2>&1; then
        return 0
    fi

    if ! docker info >/dev/null 2>&1; then
        return 0
    fi

    # 2. If free space is below threshold or cache is high, trigger prune
    if [ "$free_gb" -lt "$MIN_FREE_GB" ]; then
        log_msg "⚠️ Available space (${free_gb} GB) below threshold (${MIN_FREE_GB} GB)! Executing emergency Docker prune..."
        docker builder prune -f >> "$LOG_FILE" 2>&1 || true
        docker image prune -f >> "$LOG_FILE" 2>&1 || true
        log_msg "✅ Emergency prune complete."
    else
        # Routine check: prune build cache if older than 7 days
        docker builder prune -f --filter "until=168h" >> "$LOG_FILE" 2>&1 || true
    fi
}

# If run with --once or -1, execute single pass and exit
if [[ "${1:-}" == "--once" || "${1:-}" == "-1" ]]; then
    run_hygiene_check
    exit 0
fi

log_msg "Starting Docker storage hygiene watchdog loop (interval: ${CHECK_INTERVAL_SEC}s)..."
while true; do
    run_hygiene_check
    sleep "$CHECK_INTERVAL_SEC"
done
