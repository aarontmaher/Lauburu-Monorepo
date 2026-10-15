#!/usr/bin/env python3
"""
Training Protocol: Human-Centric Adaptive RAM Governor
======================================================
Subsystem: 02_ai_models_and_inference/train_human_adaptive_governor.py

Compiles live telemetry pairs into Direct Preference Optimization (DPO) and
Supervised Fine-Tuning (SFT) formats for in-process micro-models (SmolLM2-135M / Qwen-0.5B).
"""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATASET_DIR = REPO_ROOT / "04_data_and_memory" / "lora_datasets" / "human_adaptive_governor"
TELEMETRY_LOG = DATASET_DIR / "adaptive_governor_telemetry.jsonl"
DPO_TRAIN_FILE = DATASET_DIR / "governor_dpo_train.jsonl"


def compile_dpo_pairs():
    if not TELEMETRY_LOG.exists():
        print("No telemetry logged yet. Generating baseline synthetic anchor pairs...")
        anchors = [
            {
                "prompt": "Host RAM 24GB, user actively typing in Google Chrome, idle_sec=2, compressor_mb=4200. Recommend AI RAM cap and offload route.",
                "chosen": "CAP: 50% (12.0 GB). Action: Offload training batch to L2 MacBook Pro over 40Gbps TB4 DMA. System headroom preserved.",
                "rejected": "CAP: 90% (21.6 GB). Action: Keep all training on L1. (Result: UI stutter and page compressor thrashing)."
            },
            {
                "prompt": "Host RAM 24GB, user idle for 600s, screen locked, night mode active. Recommend AI RAM cap and offload route.",
                "chosen": "CAP: 90% (21.6 GB). Action: Maximize local M4 Pro GPU inference and batch LoRA distillation. Peak tensor throughput.",
                "rejected": "CAP: 50% (12.0 GB). Action: Throttle AI to 50% unnecessarily while host is completely unused."
            }
        ]
        with open(DPO_TRAIN_FILE, "w", encoding="utf-8") as f:
            for a in anchors:
                f.write(json.dumps(a) + "\n")
        print(f"Written {len(anchors)} DPO training pairs to {DPO_TRAIN_FILE}")
        return

    pairs = []
    with open(TELEMETRY_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
                prompt = (
                    f"Host RAM {record['total_ram_gb']}GB, user active={record['is_human_active']} in "
                    f"{record['frontmost_application']}, idle={record['idle_seconds']:.0f}s, "
                    f"compressor={record['compressor_ram_gb']:.1f}GB, cpu={record['cpu_usage_pct']:.1f}%."
                )
                chosen = (
                    f"CAP: {record['dynamic_ai_cap_pct']}%. "
                    f"Action: Route to {record['offload_target']}. {record['rationale']}"
                )
                rejected = (
                    f"CAP: {90.0 if record['dynamic_ai_cap_pct'] < 70 else 40.0}%. "
                    f"Action: Static static unadaptive allocation without human context."
                )
                pairs.append({"prompt": prompt, "chosen": chosen, "rejected": rejected})
            except Exception:
                continue

    with open(DPO_TRAIN_FILE, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")

    print(f"Successfully compiled {len(pairs)} live DPO training pairs to {DPO_TRAIN_FILE}")


if __name__ == "__main__":
    compile_dpo_pairs()
