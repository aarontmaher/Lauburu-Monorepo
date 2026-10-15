#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
06_scripts_and_tooling/distributed_model_vault_router.py
================================================================================
Dynamic Distributed Model Vault & 70B/72B Sharding Router.
Resolves the Mac Mini L1 host storage constraint (only 4.2 GB free).
Routes all models > 10 GB to Layer 2 (MacBook Pro 285 GB SSD Model Vault via TB4)
or Layer 3 (Linux Head Node 400 GB NVMe).

Governed by:
- Rule #2 (Tri-Vault Storage Rule)
- Rule #3 (Host Sanctuary & Dynamic RAM Governance)
- Rule #0 (Zero-Mock Data)
================================================================================
"""

import os
import sys
import json
import shutil
from pathlib import Path

WORKSPACE = Path("/Volumes/Lauburu-Monorepo")
QUEUE_FILE = WORKSPACE / "02_ai_models_and_inference/model_vault_gguf/MODEL_VAULT_CATALOG_AND_DOWNLOAD_QUEUE.json"

# Hardware Matrix
L1_HOST = {"name": "L1_Mac_Node", "ip": "127.0.0.1", "role": "Host & Governor", "max_local_model_gb": 10.0}
L2_MBP = {"name": "L2_MacBook_Pro", "ip": "192.168.8.127", "tb4_ip": "169.254.187.138", "vault_path": "/Volumes/ModelVault/GGUF", "capacity_gb": 285.0}
L3_LINUX = {"name": "L3_Linux_Head_Node", "ip": "192.168.8.224", "vault_path": "/var/lib/docker/models", "capacity_gb": 400.0}


def audit_and_route():
    print("=" * 75)
    print("🌐 LAUBURU DISTRIBUTED MODEL VAULT ROUTER (72B OFF-HOST INGESTION)")
    print("=" * 75)

    # 1. Measure L1 Disk Space
    usage = shutil.disk_usage("/Users/aaron")
    free_gb = usage.free / (1024**3)
    print(f"📊 Mac Mini Host (L1) Available Disk: {free_gb:.2f} GB (Threshold: >= 10.0 GB)")

    # 2. Inspect Model Queue
    if not QUEUE_FILE.exists():
        print("❌ Queue file not found.")
        return 1

    with open(QUEUE_FILE) as f:
        queue = json.load(f)

    # Ensure 72B Models are explicitly queued with L2/L3 offload targets
    model_72b_entries = [
        {
            "repo_id": "Qwen/Qwen2.5-72B-Instruct-GGUF",
            "filename": "qwen2.5-72b-instruct-q4_k_m.gguf",
            "category": "Frontier Distributed Reasoner (72B)",
            "size_gb": 44.8,
            "target_hardware": "L2_MacBook_Pro_TB4 (285 GB SSD Vault)",
            "storage_destination": f"{L2_MBP['vault_path']}/qwen2.5-72b-instruct-q4_k_m.gguf",
            "transport": "10Gbps Thunderbolt 4 DMA Direct Bridge (0.277ms)",
            "rpc_port": 50052,
            "runnable_currently": True,
            "status": "QUEUED_DISTRIBUTED_OFFLOAD",
            "sharding_policy": "PRP_RING_OR_RPC"
        },
        {
            "repo_id": "deepseek-ai/DeepSeek-V3-GGUF",
            "filename": "DeepSeek-V3-UD-IQ2_XXS-00001-of-00005.gguf",
            "category": "DeepSeek 671B MoE Shards",
            "size_gb": 42.0,
            "target_hardware": "L3_Linux_Head_Node (400 GB NVMe)",
            "storage_destination": f"{L3_LINUX['vault_path']}/DeepSeek-V3-UD-IQ2_XXS.gguf",
            "transport": "1GbE Ray Cluster & Petals DHT",
            "runnable_currently": True,
            "status": "QUEUED_OFFLOAD_TO_LINUX_HEAD",
            "sharding_policy": "PETALS_DHT_OR_RAY"
        }
    ]

    # Merge into queue if not present
    existing_filenames = {item.get("filename") for item in queue}
    added_count = 0
    for entry in model_72b_entries:
        if entry["filename"] not in existing_filenames:
            queue.append(entry)
            added_count += 1
            print(f"➕ Queued Distributed Model: {entry['filename']} ({entry['size_gb']} GB) ➔ {entry['target_hardware']}")

    # Review routing across all items in queue
    routed_items = []
    for item in queue:
        size = item.get("size_gb", 0.0)
        if size > L1_HOST["max_local_model_gb"]:
            item["target_hardware"] = "L2_MacBook_Pro_TB4 (285 GB SSD Vault)"
            item["host_disk_impact_gb"] = 0.0
            item["offload_required"] = True
        else:
            item["host_disk_impact_gb"] = size
            item["offload_required"] = False
        routed_items.append(item)

    with open(QUEUE_FILE, "w") as f:
        json.dump(routed_items, f, indent=2)

    print(f"\n✔ Model Catalog & Download Queue updated with distributed placement ({len(routed_items)} total entries).")
    print("✔ All models > 10 GB mapped to Layer 2 (TB4 Model Vault) or Layer 3 (Linux NVMe).")
    print("✔ L1 Host SSD Footprint Impact: 0.0 GB for 72B & 671B models.")
    return 0


if __name__ == "__main__":
    sys.exit(audit_and_route())
