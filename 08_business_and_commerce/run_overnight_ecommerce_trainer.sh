#!/bin/bash
# ==============================================================================
# 🌙 Sovereign Overnight E-Commerce Continuous Training Daemon
# Governed by: Rule #3 (Host Sanctuary), Rule #9 (Zero-Waste Background Daemon)
# ==============================================================================

PROJECT_DIR="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
TRAINER_SCRIPT="$PROJECT_DIR/08_business_and_commerce/sovereign_ecommerce_integrated_trainer.py"
LOG_FILE="$PROJECT_DIR/08_business_and_commerce/overnight_training.log"
TELEMETRY_MD="$PROJECT_DIR/obsidian_vault/APPS_AND_FEATURES/ECOMMERCE_TRAINING_TELEMETRY.md"
PID_FILE="/tmp/lauburu_ecommerce_trainer.pid"

echo $$ > "$PID_FILE"
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Sovereign Overnight E-Commerce Daemon Started (PID: $$)" >> "$LOG_FILE"

CYCLE=1

while true; do
    # Check RAM headroom via psutil (accurate Darwin memory calculation)
    FREE_RAM_MB=$(python3 -c "import psutil; print(int(psutil.virtual_memory().available / 1024 / 1024))" 2>/dev/null || echo 2000)
    if [ "$FREE_RAM_MB" -lt 1500 ]; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Low host RAM (${FREE_RAM_MB}MB available). Pacing 120s for sanctuary..." >> "$LOG_FILE"
        sleep 120
        continue
    fi

    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] === Starting Overnight Cycle #$CYCLE (Host Available RAM: ${FREE_RAM_MB}MB) ===" >> "$LOG_FILE"
    
    # Run single training cycle with lowered priority
    nice -n 10 python3 "$TRAINER_SCRIPT" >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
    
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Cycle #$CYCLE Finished with Exit Code $EXIT_CODE" >> "$LOG_FILE"

    # Update Obsidian Telemetry file
    if [ -f "$PROJECT_DIR/08_business_and_commerce/continuous_trainer_telemetry.json" ]; then
        TELEMETRY_CONTENT=$(cat "$PROJECT_DIR/08_business_and_commerce/continuous_trainer_telemetry.json")
        cat << TELEM_EOF > "$TELEMETRY_MD"
---
title: "E-Commerce Overnight Continuous Training Telemetry"
timestamp: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
tags: [ecommerce, overnight_training, lora_distillation, rule_9, rule_3]
status: "ACTIVE_DAEMON_RUNNING"
---

# 🌙 E-Commerce Overnight Continuous Training Telemetry
*Daemon PID: $$, Active Cycle: $CYCLE, Updated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")*

\`\`\`json
$TELEMETRY_CONTENT
\`\`\`

- [[Index]]
- [[APPS_AND_FEATURES/GROK_BOT_DEEP_REVERSE_ENGINEERING]]
- [[04_ANALYTICS/AI_DEBATES/2026-09-19_ECOMMERCE_OVERNIGHT_INTEGRATION_DEBATE]]
TELEM_EOF
    fi

    CYCLE=$((CYCLE + 1))
    
    # Adaptive sleep interval between cycles (75 seconds)
    sleep 75
done
