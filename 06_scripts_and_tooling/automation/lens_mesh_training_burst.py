import json
import time
import os

DATASET_PATH = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl"

def append_training(instruction, input_data, output_data, reward):
    entry = {
        "instruction": instruction,
        "input": input_data,
        "output": output_data,
        "reward": reward
    }
    with open(DATASET_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    print(f"[LENS MESH TRAINING] Synthesized LoRA Pair -> {instruction[:60]}...")

print("=== Starting Lens Canonical Mesh Orchestration Training Burst ===")

# 1. Training on Multi-Transport Failover Hierarchy
append_training(
    "Orchestrate a multi-transport SSH connection failover cascade to the L2 MacBook Pro Vault, adhering to the Canonical Mesh Orchestration Tier hierarchy.",
    "Target: MacBook_Pro (L2). Goal: Validate uptime. Ports: 22.",
    "Executing Transport Priority Matrix:\n1. TB4 DMA (169.254.187.138:22) - TIMEOUT\n2. Local LAN (192.168.8.127:22) - TIMEOUT\n3. Tailscale (100.103.212.21:22) - SUCCESS (0.8ms RTT)\n[nomad_courier] Executing: ssh -p 22 aaronmaher@100.103.212.21 'uptime && pmset -g assertions'",
    "High (+15 ELO)"
)

# 2. Training on Android Termux Port Separation and ADB Healing
append_training(
    "Perform a Nomad Courier self-healing sequence for the Android Pixel 10 Pro XL edge node that has fallen off the Tailscale matrix due to Doze mode.",
    "Target: Pixel_10_Pro_XL (L6). Tailscale IP: 100.73.38.87. Port: 8022.",
    "Detection: Port 8022 SSH connection refused. Diagnosis: Android Termux process killed or Doze active.\n[nomad_courier] Executing ADB USB/TCP Injection via Shizuku Bridge (rish):\nadb shell \"am start -n com.termux/.app.TermuxActivity && input text 'sshd' && input keyevent 66\"\nAction: termux-wake-lock applied. Phantom Process Killer disabled. Port 8022 verified UP.",
    "High (+20 ELO)"
)

# 3. Training on Dynamic Tensor Routing & Host Sanctuary
append_training(
    "Execute Continuous Mesh Self-Optimization to reroute llama.cpp RPC sharding traffic away from Tailscale to preserve Mac Mini Host RAM limits.",
    "Telemetry: Mac Mini RAM headroom < 4.8GB. Tailscale bandwidth saturated. L1 <-> L2 link active.",
    "Dynamic Tensor Reroute Initiated:\n1. Terminating Tailscale llama-server RPC endpoints.\n2. Rebinding prima.cpp Pipelined-Ring Parallelism to bridge0 (TB4: 169.254.x.x).\nResult: RTT reduced to 0.27ms. 40Gbps DMA enabled. Host RAM stabilized at 5.2GB headroom (Rule 3 Host Sanctuary Preserved).",
    "High (+25 ELO)"
)

print("[LENS MESH TRAINING] Burst complete. 3 high-density mesh orchestration pairs injected into continuous_lora_dataset.jsonl.")
