#!/bin/bash
while true; do
    echo "Running Tri-Vault Storage Pre-Flight Self-Healing..."
    # 1. Self-Heal Missing Vault Directories
    mkdir -p /Volumes/Lauburu-Monorepo/obsidian_vault /Volumes/Lauburu-Monorepo/04_data_and_memory/data /Volumes/Lauburu-Monorepo/04_data_and_memory
    
    # 2. Self-Heal Stale Git Locks
    [ -f "/Volumes/Lauburu-Monorepo/.git/index.lock" ] && rm -f "/Volumes/Lauburu-Monorepo/.git/index.lock"
    
    # 3. Self-Heal Disk Headroom (If < 5.0 GB Free)
    FREE_SPACE=$(df -g /Users/aaron | awk 'NR==2 {print $4}')
    if [ "$FREE_SPACE" -lt 5 ]; then
        echo "Disk space < 5GB ($FREE_SPACE GB). Pruning pycache..."
        find /Users/aaron/teamwork_projects -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    fi
    
    # 4. Self-Heal Obsidian Master Index (If missing)
    if [ ! -s "/Volumes/Lauburu-Monorepo/obsidian_vault/Index.md" ]; then
      cat << 'INNER_EOF' > /Volumes/Lauburu-Monorepo/obsidian_vault/Index.md
---
title: "Lauburu AI Monorepo - Master Knowledge Graph"
tags: [lauburu, root, master_index, swarm, ai_debate]
---
# 🧠 Lauburu AI Monorepo - Master Knowledge Vault
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[Index]]
INNER_EOF
      echo "Healed Obsidian Master Index."
    fi
    
    echo "Healing complete. Sleeping 900s."
    sleep 900
done
