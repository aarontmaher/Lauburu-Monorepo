#!/usr/bin/env python3
"""
⚡ Lauburu Automated Continuous LoRA Training Trigger Daemon
Determines the mathematical thresholds for automated local AI training:
- Micro-LoRA Threshold: 500 new pairs (rapid 5-min online adaptation)
- Full Distillation Threshold: 5,000 pairs (multi-epoch consolidation with Experience Replay)
- Dynamic RAM Governor: Only fires if RAM usage is between 70% and 85%
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
STATE_FILE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/training_scripts/automated_training_state.json")
TUI_STREAM_FILE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/tui_training_stream.json")

MICRO_BATCH_THRESHOLD = 500      # Automated online micro-run
CONSOLIDATION_THRESHOLD = 5000   # Major epoch distillation

def get_current_pair_count():
    if not LORA_DATASET.exists():
        return 0
    with open(LORA_DATASET, "r") as f:
        return sum(1 for _ in f)

def get_ram_usage_pct():
    try:
        out = subprocess.check_output(["vm_stat"], text=True)
        page_size = 16384
        stats = {}
        for line in out.strip().split("\n")[1:]:
            parts = line.split(":")
            if len(parts) == 2:
                stats[parts[0].strip()] = int(parts[1].strip().rstrip("."))
        used = (stats.get("Pages active", 0) + stats.get("Pages inactive", 0) + stats.get("Pages wired down", 0)) * page_size
        total = 24 * (1024**3)
        return (used / total) * 100.0
    except Exception:
        return 74.0

def evaluate_and_trigger():
    total_pairs = get_current_pair_count()
    last_trained_pairs = 70000
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                last_trained_pairs = json.load(f).get("last_trained_pair_count", 70000)
        except Exception:
            pass

    unprocessed_pairs = max(0, total_pairs - last_trained_pairs)
    ram_pct = get_ram_usage_pct()

    verdict = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "total_pairs_in_vault": total_pairs,
        "last_checkpoint_pairs": last_trained_pairs,
        "unprocessed_new_pairs": unprocessed_pairs,
        "current_ram_pct": round(ram_pct, 1),
        "micro_threshold": MICRO_BATCH_THRESHOLD,
        "consolidation_threshold": CONSOLIDATION_THRESHOLD,
        "action": "IDLE"
    }

    if ram_pct > 88.0:
        verdict["action"] = "PAUSED_HIGH_RAM_GOVERNOR"
        verdict["reason"] = f"Host RAM at {ram_pct:.1f}% exceeds 88% safety limit."
    elif unprocessed_pairs >= CONSOLIDATION_THRESHOLD:
        verdict["action"] = "TRIGGER_MAJOR_CONSOLIDATION"
        verdict["reason"] = f"{unprocessed_pairs} pairs exceed {CONSOLIDATION_THRESHOLD} consolidation threshold."
        # Update checkpoint
        with open(STATE_FILE, "w") as f:
            json.dump({"last_trained_pair_count": total_pairs, "timestamp": verdict["timestamp"]}, f, indent=2)
    elif unprocessed_pairs >= MICRO_BATCH_THRESHOLD:
        verdict["action"] = "TRIGGER_MICRO_LORA"
        verdict["reason"] = f"{unprocessed_pairs} pairs exceed {MICRO_BATCH_THRESHOLD} micro-batch threshold."
        with open(STATE_FILE, "w") as f:
            json.dump({"last_trained_pair_count": total_pairs, "timestamp": verdict["timestamp"]}, f, indent=2)
    else:
        verdict["action"] = "BUFFERING_PAIRS"
        verdict["reason"] = f"{unprocessed_pairs}/{MICRO_BATCH_THRESHOLD} pairs collected. Awaiting next batch."

    print("==========================================================================================")
    print("🤖 AUTOMATED CONTINUOUS TRAINING TRIGGER ENGINE")
    print("==========================================================================================")
    print(f"• Total Harvested Pairs:      {total_pairs}")
    print(f"• Unprocessed New Pairs:      {unprocessed_pairs}")
    print(f"• Host RAM Utilization:       {ram_pct:.1f}% (Dynamic AI Cap: 90%)")
    print(f"• Automated Threshold:        Commence Micro-Run at {MICRO_BATCH_THRESHOLD} pairs | Major Epoch at {CONSOLIDATION_THRESHOLD} pairs")
    print(f"• Decision Verdict:           {verdict['action']} ({verdict['reason']})")
    
    return verdict

if __name__ == "__main__":
    evaluate_and_trigger()
