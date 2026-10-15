#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Lauburu Sovereign Mesh: 3-Tier Storage, Syncthing & Local AI Model Orchestrator
================================================================================
Subsystem: 06_scripts_and_tooling/storage/mesh_storage_and_syncthing_orchestrator.py
Version: 1.0.0-MESH-STORAGE-ORCHESTRATOR

Enforces the Canonical 3-Pillar Lauburu Storage Architecture:
1. Pillar 1 — L1b (Mac Mini M2 Pro, 2 TB NVMe SSD, 40 Gbps TB4):
   - Canonical Master Project Hub (/Volumes/AI_Projects/Lauburu_Master/Lauburu-Monorepo)
   - Master LoRA & Gemini Antigravity Telemetry Vault (/Volumes/AI_Projects/Lauburu_Master/lora_datasets)
   - Master Local AI Model Library (/Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault)
   - Offloaded L1 Archive (/Volumes/AI_Projects/L1_Offload_Archive)
2. Pillar 2 — Syncthing P2P Block Federation (Native APFS/ext4 Speed):
   - Synchronizes 06_scripts_and_tooling (including /lens CLI), obsidian_vault,
     00_core_infrastructure, lora_datasets, and architecture-safe deps_vault
     across L1b (Introducer), L1, L5, L3, L6, and L7.
3. Pillar 3 — Dedicated Local AI Model Shards (POSIX mmap() Ready):
   - Remaining SSD space on L1, L5, L2, L8, and L3 is strictly reserved for
     local .gguf / .safetensors / .npz model weights.
================================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if not (REPO_ROOT / "06_scripts_and_tooling").exists():
    for cand in [Path("/Volumes/Lauburu-Monorepo"), Path("/Volumes/Lauburu-Monorepo")]:
        if cand.exists():
            REPO_ROOT = cand
            break

STORAGE_NODES = [
    {
        "id": "L1b",
        "name": "Mac Mini M2 Pro (2TB Master Hub)",
        "ssh": "l1b",
        "mount": "/System/Volumes/Data",
        "role": "Canonical Project Hub + Syncthing Introducer + 2TB Model Vault",
        "model_dir": "/Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault",
    },
    {
        "id": "L1",
        "name": "Mac Mini M4 Pro (Sovereign Host)",
        "ssh": "l1",
        "mount": "/System/Volumes/Data",
        "role": "Pinned Qwen 3.8 Max Master (:8082) + Screen Lens SQLite",
        "model_dir": "/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference",
    },
    {
        "id": "L5",
        "name": "MacBook Air M4 (MLX Metal Trainer)",
        "ssh": "l5",
        "mount": "/System/Volumes/Data",
        "role": "MLX Gemini Telemetry Trainer + Active Monorepo + /lens CLI",
        "model_dir": "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/adapters",
    },
    {
        "id": "L8",
        "name": "Linux Mini Hub (lauburu TB4)",
        "ssh": "l8",
        "mount": "/",
        "role": "Pinned Qwen 3.8 Red-Team (:8083) + Math-72B + Qdrant (:6333)",
        "model_dir": "/home/linuxmini/model_vault_gguf",
    },
    {
        "id": "L2",
        "name": "MacBook Pro Intel (Model Vault)",
        "ssh": "l2",
        "mount": "/System/Volumes/Data",
        "role": "Secondary GGUF RPC Shard Vault (:50052)",
        "model_dir": "/Users/aaronmaher",
    },
    {
        "id": "L3",
        "name": "Linux Head Node (Ryzen 7)",
        "ssh": "l3",
        "mount": "/",
        "role": "Syncthing Linux Replica + Ray/Docker Compute",
        "model_dir": "/home/linux/lauburu_sync",
    },
]


def query_node_storage(node: Dict[str, str]) -> Dict[str, Any]:
    cmd = (
        f"df -h {node['mount']} | tail -n 1; "
        f"echo '---MODELS---'; "
        f"find {node['model_dir']} -maxdepth 3 \\( -name '*.gguf' -o -name '*.safetensors' -o -name '*.npz' \\) 2>/dev/null | wc -l"
    )
    try:
        res = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", node["ssh"], cmd],
            capture_output=True, text=True, timeout=10.0
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = res.stdout.split("---MODELS---")
            df_line = parts[0].strip().split()
            model_count = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip().isdigit() else 0
            # df -h columns: Filesystem Size Used Avail Capacity ...
            size = df_line[1] if len(df_line) > 1 else "?"
            used = df_line[2] if len(df_line) > 2 else "?"
            avail = df_line[3] if len(df_line) > 3 else "?"
            cap = df_line[4] if len(df_line) > 4 else "?"
            return {
                "id": node["id"],
                "name": node["name"],
                "status": "ONLINE",
                "size": size,
                "used": used,
                "avail": avail,
                "capacity": cap,
                "models_count": model_count,
                "role": node["role"],
            }
    except Exception:
        pass
    return {
        "id": node["id"],
        "name": node["name"],
        "status": "OFFLINE",
        "size": "--",
        "used": "--",
        "avail": "--",
        "capacity": "--",
        "models_count": 0,
        "role": node["role"],
    }


def sync_project_and_federation() -> None:
    from concurrent.futures import ThreadPoolExecutor
    print("🔄 [1/3] Syncing active /lens CLI, Storage, Training & Network modules to L1 (Host) and L1b (2TB Master Hub)...")
    base = REPO_ROOT / "06_scripts_and_tooling"
    targets = [
        str(base / "lens_cli.py"),
        str(base / "speculative_cli_data_engine.py"),
        str(base / "storage"),
        str(base / "training"),
        str(base / "network" / "syncthing_mesh_federation.py"),
    ]
    cmds = [
        ["rsync", "-a", "--exclude=__pycache__", *targets, "l1:/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/"],
        ["rsync", "-a", "--exclude=__pycache__", *targets, "l1b:/Volumes/AI_Projects/Lauburu_Master/Lauburu-Monorepo/06_scripts_and_tooling/"],
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda c: subprocess.run(c, capture_output=True, timeout=12.0), cmds))

    print("🔄 [2/3] Running Syncthing P2P Mesh Federation Engine (L1b 2TB Introducer)...")
    fed_script = REPO_ROOT / "06_scripts_and_tooling" / "network" / "syncthing_mesh_federation.py"
    subprocess.run([sys.executable, str(fed_script)], timeout=25.0)

    print("🔄 [3/3] Auditing 3-Tier Mesh Storage & Local AI Model Vault Matrix...")


ROOTED_PODMAN_STORAGE_SPEC = {
    "architecture_version": "2.0.0-ROOTED-PODMAN-UNIFIED-STORAGE",
    "canonical_project_holder": {
        "node_id": "L1b",
        "device": "Mac Mini M2 Pro (2TB NVMe SSD)",
        "thunderbolt_ip": "10.0.0.3",
        "lan_ip": "192.168.8.114",
        "role": "Overall Canonical Project Files & Folder Holder + Syncthing Introducer + 2TB Model Vault",
        "canonical_paths": {
            "monorepo_master": "/Volumes/AI_Projects/Lauburu_Master/Lauburu-Monorepo",
            "lora_datasets_master": "/Volumes/AI_Projects/Lauburu_Master/lora_datasets",
            "ai_models_vault": "/Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault",
            "deps_vault": "/Volumes/AI_Projects/Lauburu_Master/deps_vault",
            "offload_archive": "/Volumes/AI_Projects/L1_Offload_Archive",
        },
    },
    "other_devices_role": {
        "description": "Hold local AI models (.gguf/.safetensors/.npz for POSIX mmap) + Syncthing P2P Federation for project dependencies",
        "syncthing_federated_folders": [
            "06_scripts_and_tooling",
            "obsidian_vault",
            "00_core_infrastructure",
            "lora_datasets",
            "deps_vault",
        ],
        "network_smb_storage": {
            "gateway_ip": "192.168.8.1",
            "mount_points": ["/Volumes/seaweed_network", "/Volumes/lauburu_storage"],
            "mount_script": str(REPO_ROOT / "06_scripts_and_tooling/storage/mount_router_network_storage.sh"),
        },
    },
    "rooted_podman_container_layout": {
        "runtime_flags": [
            "--userns=host",
            "--privileged",
            "--security-opt", "label=disable",
            "--network=host",
            "--ipc=host",
            "--shm-size=4g",
        ],
        "bind_mounts": [
            {
                "container_path": "/workspace/monorepo",
                "host_source_linux": "/home/linux/lauburu_sync/Lauburu-Monorepo",
                "host_source_l8": "/home/linuxmini/lauburu_sync/Lauburu-Monorepo",
                "host_source_mac": "/Volumes/Lauburu-Monorepo",
                "mode": "rw,Z",
                "purpose": "Canonical project code & scripts federated from L1b 2TB M2 Pro via Syncthing",
            },
            {
                "container_path": "/workspace/models",
                "host_source_linux": "/home/linux/model_vault_gguf",
                "host_source_l8": "/home/linuxmini/model_vault_gguf",
                "host_source_mac": "/Users/aaronmaher/DFS_UNIFIED/AI_Models_Vault",
                "mode": "ro,Z",
                "purpose": "Read-only local AI model shards (.gguf/.safetensors/.npz) for zero-copy POSIX mmap() inference",
            },
            {
                "container_path": "/workspace/lora_datasets",
                "host_source_linux": "/home/linux/lauburu_sync/lora_datasets",
                "host_source_l8": "/home/linuxmini/lauburu_sync/lora_datasets",
                "host_source_mac": "/Volumes/AI_Projects/Lauburu_Master/lora_datasets",
                "mode": "rw,Z",
                "purpose": "24/7 Continuous LoRA JSONL datasets & checkpoints synced back to L1b 2TB Hub",
            },
            {
                "container_path": "/workspace/obsidian_vault",
                "host_source_linux": "/home/linux/lauburu_sync/Lauburu-Monorepo/obsidian_vault",
                "host_source_l8": "/home/linuxmini/lauburu_sync/Lauburu-Monorepo/obsidian_vault",
                "host_source_mac": "/Volumes/Lauburu-Monorepo/obsidian_vault",
                "mode": "rw,Z",
                "purpose": "Obsidian Markdown knowledge vault federated across all nodes",
            },
            {
                "container_path": "/workspace/deps_vault",
                "host_source_linux": "/home/linux/lauburu_sync/deps_vault",
                "host_source_l8": "/home/linuxmini/lauburu_sync/deps_vault",
                "host_source_mac": "/Volumes/AI_Projects/Lauburu_Master/deps_vault",
                "mode": "rw,Z",
                "purpose": "Offline wheelhouse, Go module cache, and npm tarballs for air-gapped container builds",
            },
        ],
        "isolated_native_volumes": [
            {
                "volume_name": "lauburu_neo4j_data",
                "container_path": "/var/lib/neo4j/data",
                "filesystem": "native ext4 / APFS (NEVER SMB/FUSE/Syncthing)",
                "purpose": "Neo4j 5.26.32 transactional store & Lucene HNSW indexes (prevents network lock corruption)",
            },
            {
                "volume_name": "lauburu_qdrant_storage",
                "container_path": "/var/lib/qdrant/storage",
                "filesystem": "native ext4 / APFS (NEVER SMB/FUSE/Syncthing)",
                "purpose": "Qdrant MRL vector segments & WAL (prevents mmap page-fault stalls)",
            },
            {
                "volume_name": "lauburu_pyspark_warehouse",
                "container_path": "/var/lib/pyspark/warehouse",
                "filesystem": "native ext4 / APFS with Parquet snapshot export to /workspace/lora_datasets",
                "purpose": "PySpark Delta/Parquet analytical scratchpad",
            },
        ],
    },
}


def get_rooted_podman_storage_spec() -> Dict[str, Any]:
    """Returns the canonical Rooted Podman & Multi-Device Storage specification."""
    return ROOTED_PODMAN_STORAGE_SPEC


def print_storage_matrix(records: List[Dict[str, Any]]) -> None:
    print("=" * 108)
    print("🗄️  LAUBURU 3-TIER MESH STORAGE & LOCAL AI MODEL VAULT TOPOLOGY (L1b 2TB HUB + TB4 + PODMAN)")
    print("=" * 108)
    print(f"{'Node':<5} {'Device Name':<32} {'Size':<7} {'Used':<7} {'Free':<8} {'Use%':<6} {'Models':<7} {'Canonical Role'}")
    print("-" * 108)
    for r in records:
        icon = "🟢" if r["status"] == "ONLINE" else "🔴"
        print(
            f"{icon} {r['id']:<3} {r['name']:<32} {r['size']:<7} {r['used']:<7} "
            f"{r['avail']:<8} {r['capacity']:<6} {r['models_count']:<7} {r['role']}"
        )
    print("=" * 108)


def print_podman_storage_spec() -> None:
    spec = ROOTED_PODMAN_STORAGE_SPEC
    print("=" * 108)
    print("🐳 ROOTED PODMAN CONTAINER STORAGE STRUCTURE & L1b 2TB MASTER HUB TOPOLOGY")
    print("=" * 108)
    holder = spec["canonical_project_holder"]
    print(f"• Master Project Holder : {holder['node_id']} — {holder['device']} (TB4: {holder['thunderbolt_ip']} | LAN: {holder['lan_ip']})")
    for k, v in holder["canonical_paths"].items():
        print(f"    - {k:<22}: {v}")
    print("-" * 108)
    print("• Rooted Podman Container Bind Mounts (--userns=host --privileged --security-opt label=disable):")
    for bm in spec["rooted_podman_container_layout"]["bind_mounts"]:
        print(f"    - {bm['container_path']:<28} [{bm['mode']}] -> {bm['purpose']}")
    print("• Isolated Native Block Volumes (Never Syncthing/SMB-mounted to prevent DB lock corruption):")
    for vol in spec["rooted_podman_container_layout"]["isolated_native_volumes"]:
        print(f"    - {vol['volume_name']:<24} -> {vol['container_path']:<24} ({vol['purpose']})")
    print("=" * 108)


def main():
    from concurrent.futures import ThreadPoolExecutor
    parser = argparse.ArgumentParser(description="Lauburu 3-Tier Mesh Storage, Syncthing & Rooted Podman Orchestrator")
    parser.add_argument("--status", action="store_true", help="Audit and display mesh storage & model vault matrix")
    parser.add_argument("--podman-spec", action="store_true", help="Display exact Rooted Podman container storage structure")
    parser.add_argument("--sync", action="store_true", help="Sync project tooling to L1b 2TB Hub, federate Syncthing, and show status")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.podman_spec:
        if args.json:
            print(json.dumps(ROOTED_PODMAN_STORAGE_SPEC, indent=2))
        else:
            print_podman_storage_spec()
        return

    if args.sync:
        sync_project_and_federation()

    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(query_node_storage, STORAGE_NODES))
    if args.json:
        print(json.dumps({"storage_nodes": records, "rooted_podman_spec": ROOTED_PODMAN_STORAGE_SPEC}, indent=2))
        return

    print_storage_matrix(records)
    print_podman_storage_spec()
    if not args.sync:
        fed_script = REPO_ROOT / "06_scripts_and_tooling" / "network" / "syncthing_mesh_federation.py"
        if fed_script.exists():
            subprocess.run([sys.executable, str(fed_script), "--status"], timeout=20.0)


if __name__ == "__main__":
    main()


