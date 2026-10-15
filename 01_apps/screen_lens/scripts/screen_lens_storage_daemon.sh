#!/usr/bin/env bash
# ==============================================================================
# Screen Lens Sovereign: Multi-Tier Storage Background Daemon
# Governed by Rule 3 (Host Sanctuary), Rule 9 (Zero-Waste Daemon), Rule 10 (Linux Offload)
# ==============================================================================

LOG_FILE="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/screen_lens_storage_daemon.log"
ORCHESTRATOR_SCRIPT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/scripts/screen_lens_storage_orchestrator.py"
INTERVAL_SECONDS=14400  # Run every 4 hours

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [DAEMON_START] Screen Lens Storage Daemon initialized." >> "$LOG_FILE"

while true; do
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [RUN] Invoking Screen Lens Storage Orchestrator..." >> "$LOG_FILE"
    
    python3 "$ORCHESTRATOR_SCRIPT" >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
    
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [COMPLETE] Orchestrator run finished with Exit Code: $EXIT_CODE" >> "$LOG_FILE"
    
    # Sleep until next scheduled iteration
    sleep "$INTERVAL_SECONDS"
done
