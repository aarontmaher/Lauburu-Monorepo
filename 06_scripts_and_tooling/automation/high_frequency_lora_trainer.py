#!/usr/bin/env python3
"""
================================================================================
Lauburu: High-Frequency Intra-Day LoRA Distillation Engine
================================================================================
Goal: Abandons the 2:00 AM overnight batch training. Replaces it with rapid,
high-frequency micro-training (MLX LoRA) executing constantly. As soon as a 
model fails an IDE routing task, it is immediately corrected and trained.
================================================================================
"""

import os
import json
import logging
import shutil
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (Intra-Day-LoRA) %(message)s")
logger = logging.getLogger("Intra-Day-LoRA")

MONOREPO_ROOT = os.environ.get("LAUBURU_MONOREPO_ROOT", "/Volumes/Lauburu-Monorepo")
DPO_QUEUE_FILE = os.path.join(MONOREPO_ROOT, "04_data_and_memory/data/dpo_distillation_queue.jsonl")
CHECKPOINT_DIR = os.path.join(MONOREPO_ROOT, "02_ai_models_and_inference/model_vault_gguf/adapters")

def count_real_dpo_pairs(queue_path: str) -> int:
    if not os.path.exists(queue_path):
        return 0
    count = 0
    try:
        with open(queue_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
    except Exception as exc:
        logger.warning(f"Failed reading DPO queue {queue_path}: {exc}")
        return 0
    return count

def run_high_frequency_training():
    logger.info("Initializing High-Frequency Intra-Day LoRA Distillation (Zero-Mock Mode)...")
    failure_count = count_real_dpo_pairs(DPO_QUEUE_FILE)

    if failure_count == 0:
        logger.info("No pending DPO failure pairs found in queue. Status: IDLE (start_loss=None, end_loss=None).")
        return {
            "status": "IDLE",
            "harvested_failures": 0,
            "start_loss": None,
            "end_loss": None
        }

    logger.info(f"Harvested {failure_count} real routing failure records from {DPO_QUEUE_FILE}.")
    if shutil.which("mlx_lm.lora") is None:
        logger.warning("mlx_lm runtime not installed on this host. Returning status=DISCONNECTED without fake loss metrics.")
        return {
            "status": "DISCONNECTED",
            "harvested_failures": failure_count,
            "start_loss": None,
            "end_loss": None
        }

    mlx_cmd = [
        "python3", "-m", "mlx_lm.lora", "--train",
        "--model", os.path.join(MONOREPO_ROOT, "02_ai_models_and_inference/model_vault_gguf/SmolLM2-360M-Instruct"),
        "--data", os.path.dirname(DPO_QUEUE_FILE),
        "--iters", "50", "--batch-size", "4",
        "--adapter-path", os.path.join(CHECKPOINT_DIR, "smollm_router_latest.npz")
    ]
    logger.info(f"Executing: {' '.join(mlx_cmd)}")
    proc = subprocess.run(mlx_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error(f"MLX training exited with code {proc.returncode}: {proc.stderr.strip()}")
        return {
            "status": "ERROR",
            "harvested_failures": failure_count,
            "start_loss": None,
            "end_loss": None
        }

    logger.info("✅ Intra-Day Training Cycle Complete.")
    return {
        "status": "COMPLETED",
        "harvested_failures": failure_count,
        "stdout": proc.stdout[-500:]
    }

if __name__ == "__main__":
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    run_high_frequency_training()
