#!/usr/bin/env bash
# Autonomous background daemon loop for netmon LoRA distillation
# Complying with Rule 9: Native Silent Execution Invariant

while true; do
    /Volumes/Lauburu-Monorepo/.venv/bin/python3 "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/netmon_lora_distillation.py"
    sleep 300
done
