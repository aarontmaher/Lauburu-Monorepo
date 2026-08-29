#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apple Silicon Metal QLoRA Training Engine with Dynamic RAM Governance
====================================================================
Subsystem: 04_data_and_memory / fast_train_agentworld_mac.py
Version: 2.0.0-CANONICAL-M2

Re-exports and runs Apple Silicon Metal QLoRA fine-tuning for Qwen-AgentWorld / Qwen 2.5 / DeepSeek.
"""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
TRAIN_DIR = REPO_ROOT / "06_scripts_and_tooling" / "training"

if str(TRAIN_DIR) not in sys.path:
    sys.path.insert(0, str(TRAIN_DIR))

from fast_train_agentworld_mac import (
    check_hardware_capabilities,
    check_dynamic_ram_governance,
    prepare_training_dataset,
    stream_training_loss_to_obsidian,
    run_mlx_qlora_training,
    run_mps_qlora_training,
    main,
)

if __name__ == "__main__":
    main()
