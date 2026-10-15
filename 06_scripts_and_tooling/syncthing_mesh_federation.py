#!/usr/bin/env python3
"""
================================================================================
Syncthing Mesh Federation Engine v2.0 — Lauburu Sovereign Ecosystem
================================================================================
Subsystem: 06_scripts_and_tooling/network/syncthing_mesh_federation.py

Architecture:
- Establishes L1b (Mac Mini M2 Pro, 2 TB NVMe SSD, 845 GiB Free, 40 Gbps TB4)
  as the Canonical Master Introducer Seed for all project folders, /lens CLI
  tooling, Obsidian knowledge vault, LoRA/Gemini telemetry datasets, and
  architecture-safe dependencies.
- Peers L1b (M2 Pro 2TB), L1 (M4 Pro Host), L5 (M4 Air), L3 (Linux Ryzen),
  L6 (Pixel 10 Pro XL), and L7 (Samsung S20+) over 40Gbps TB4 (10.0.0.x:22000),
  LAN (192.168.8.x:22000), and Tailscale (100.x.y.z:22000).
- Enforces .stignore rules so OS/CPU-specific virtualenvs (.venv, node_modules,
  target/, __pycache__) never collide across darwin-arm64 and linux-x86_64.
================================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

NODES: Dict[str, Dict[str, Any]] = {
    "l1b": {
        "name": "Mac-Mini-M2-Pro-2TB-Master (L1b)",
        "ssh": "l1b",
        "is_local": False,
        "introducer": True,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "Uuy5Mj6vNJGdXE2VSroybcmzSAmHyXww",
        "device_id": "PYQIT6T-A662YKN-ZZA4YZO-XWJHQZK-KD3AKFS-IERB4WI-VP7FT6Q-P4DNFAN",
        "addresses": [
            "tcp://10.0.0.3:22000",
            "tcp://192.168.8.114:22000",
            "tcp://100.104.128.34:22000",
            "dynamic",
        ],
        "paths": {
            "lauburu-scripts": "/Volumes/AI_Projects/Lauburu_Master/Lauburu-Monorepo/06_scripts_and_tooling",
            "lauburu-obsidian": "/Volumes/AI_Projects/Lauburu_Master/Lauburu-Monorepo/obsidian_vault",
            "lauburu-core-infra": "/Volumes/AI_Projects/Lauburu_Master/Lauburu-Monorepo/00_core_infrastructure",
            "lauburu-lora-telemetry": "/Volumes/AI_Projects/Lauburu_Master/lora_datasets",
            "lauburu-deps-vault": "/Volumes/AI_Projects/Lauburu_Master/deps_vault",
        },
    },
    "l1": {
        "name": "Mac-Mini-M4-Pro-Host (L1)",
        "ssh": "l1",
        "is_local": False,
        "introducer": True,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "Gz6WJUd9GdCWUR3oYpQGYrgTHT4hDZy5",
        "device_id": "W5KWZRZ-ZCIMXNW-4DL46C2-MRJLB24-L6LXIEX-GO4FNOX-QYLASSN-YHIHDA3",
        "addresses": [
            "tcp://10.0.0.2:22000",
            "tcp://192.168.8.143:22000",
            "tcp://100.119.199.76:22000",
            "dynamic",
        ],
        "paths": {
            "lauburu-scripts": "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling",
            "lauburu-obsidian": "/Volumes/Lauburu-Monorepo/obsidian_vault",
            "lauburu-core-infra": "/Volumes/Lauburu-Monorepo/00_core_infrastructure",
            "lauburu-lora-telemetry": "/Volumes/Lauburu-Monorepo/04_data_and_memory/data",
            "lauburu-deps-vault": "/Volumes/Lauburu-Monorepo/deps_vault",
        },
    },
    "l5": {
        "name": "MacBook-Air-M4-Worker (L5)",
        "ssh": "l5",
        "is_local": Path("/Volumes/Lauburu-Monorepo").exists(),
        "introducer": False,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "mibq9XMsW3GjZDQ5UqDrXXFpTtV57Rd5",
        "device_id": "TOZX7SM-D424PUU-ANLAOF4-DVZSOFG-BW46NSE-67OEM6R-QTWJFMZ-TFYNDA3",
        "addresses": [
            "tcp://192.168.8.248:22000",
            "tcp://100.121.202.34:22000",
            "dynamic",
        ],
        "paths": {
            "lauburu-scripts": "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling",
            "lauburu-obsidian": "/Volumes/Lauburu-Monorepo/obsidian_vault",
            "lauburu-core-infra": "/Volumes/Lauburu-Monorepo/00_core_infrastructure",
            "lauburu-lora-telemetry": "/Volumes/Lauburu-Monorepo/04_data_and_memory/data",
            "lauburu-deps-vault": "/Volumes/Lauburu-Monorepo/deps_vault",
        },
    },
    "l3": {
        "name": "Linux-Head-Node-Ryzen (L3)",
        "ssh": "l3",
        "is_local": False,
        "introducer": False,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "F6ToKVTkoU3MVJF5jNRh5zWPhkdhocZP",
        "device_id": "C4LVDFV-WU52UP7-ZBFEJHJ-K6WRXYB-SG3CW3O-Y7JFF25-JM6HUM7-XQ223AD",
        "addresses": [
            "tcp://192.168.8.225:22000",
            "tcp://100.101.39.98:22000",
            "dynamic",
        ],
        "paths": {
            "lauburu-scripts": "/home/linux/lauburu_sync/06_scripts_and_tooling",
            "lauburu-obsidian": "/home/linux/lauburu_sync/obsidian_vault",
            "lauburu-core-infra": "/home/linux/lauburu_sync/00_core_infrastructure",
            "lauburu-lora-telemetry": "/home/linux/lauburu_sync/lora_datasets",
            "lauburu-deps-vault": "/home/linux/lauburu_sync/deps_vault",
        },
    },
}

MOBILE_PEERS = [
    {
        "deviceID": "LNVQC7N-35SA4QV-PF3QUTH-4SE2ZSX-NAXP5SW-DYDM2E5-MACM7OE-CIXAEAY",
        "name": "Pixel-10-Pro-XL (L6)",
        "addresses": ["tcp://192.168.8.213:22000", "tcp://100.114.215.68:22000", "dynamic"],
    },
    {
        "deviceID": "BF6KFOQ-URV74DS-PXCLYCU-A34NV3T-4WJV4IJ-EWQGS4I-K3SQLIQ-5R2ZWA2",
        "name": "Samsung-Galaxy-S20 (L7)",
        "addresses": ["tcp://192.168.8.101:22000", "tcp://100.78.206.96:22000", "dynamic"],
    },
]

FOLDER_LABELS = {
    "lauburu-scripts": "Lauburu Scripts, /lens CLI & Tooling",
    "lauburu-obsidian": "Lauburu Obsidian Knowledge Vault",
    "lauburu-core-infra": "Lauburu Core Infrastructure",
    "lauburu-lora-telemetry": "Lauburu Gemini/LoRA Telemetry & Adapters",
    "lauburu-deps-vault": "Lauburu Shared Dependencies & Wheelhouse",
}

STIGNORE_CONTENT = """// Architecture-safe Syncthing ignore rules
__pycache__
*.pyc
*.pyo
.pytest_cache
.DS_Store
.git/index.lock
.venv
venv
node_modules
target
"""


def _node_curl(node_key: str, endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    node = NODES[node_key]
    api_key = node["api_key"]
    url = f"{node['api_url']}{endpoint}"

    if method == "GET":
        cmd = f"curl -s -H 'X-API-Key: {api_key}' {url}"
        if node["is_local"]:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        else:
            res = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", node["ssh"], cmd],
                                 capture_output=True, text=True, timeout=12)
        if res.returncode == 0 and res.stdout.strip():
            try:
                return json.loads(res.stdout)
            except Exception:
                return None
        return None

    body_str = json.dumps(payload)
    cmd = f"curl -s -X {method} -H 'Content-Type: application/json' -H 'X-API-Key: {api_key}' --data-binary @- {url}"
    if node["is_local"]:
        res = subprocess.run(cmd, shell=True, input=body_str, capture_output=True, text=True, timeout=15)
    else:
        res = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", node["ssh"], cmd],
                             input=body_str, capture_output=True, text=True, timeout=15)
    if res.returncode == 0:
        return {"status": "OK"}
    return None


def _ensure_paths_and_stignore(node_key: str) -> None:
    node = NODES[node_key]
    dirs = list(node["paths"].values())
    escaped_ignore = STIGNORE_CONTENT.replace("'", "'\\''")
    cmds = []
    for d in dirs:
        cmds.append(f"mkdir -p '{d}' && printf '{escaped_ignore}' > '{d}/.stignore'")
    full_cmd = " && ".join(cmds)
    if node["is_local"]:
        subprocess.run(full_cmd, shell=True, capture_output=True, timeout=10)
    else:
        subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", node["ssh"], full_cmd],
                       capture_output=True, timeout=12)


def federate_node(node_key: str) -> bool:
    node = NODES[node_key]
    print(f"🔄 Configuring Syncthing on {node['name']}...")
    _ensure_paths_and_stignore(node_key)

    cfg = _node_curl(node_key, "/rest/config")
    if not cfg:
        print(f"  ❌ Could not fetch Syncthing config on {node_key}")
        return False

    existing_devs = {d["deviceID"]: d for d in cfg.get("devices", [])}

    # Add/update all mesh nodes
    all_peer_ids = []
    for peer_key, peer_info in NODES.items():
        pid = peer_info["device_id"]
        all_peer_ids.append(pid)
        if pid in existing_devs:
            existing_devs[pid]["addresses"] = peer_info["addresses"]
            existing_devs[pid]["introducer"] = peer_info["introducer"]
            existing_devs[pid]["autoAcceptFolders"] = True
        else:
            cfg.setdefault("devices", []).append({
                "deviceID": pid,
                "name": peer_info["name"],
                "addresses": peer_info["addresses"],
                "compression": "metadata",
                "introducer": peer_info["introducer"],
                "autoAcceptFolders": True,
                "paused": False,
            })

    for mp in MOBILE_PEERS:
        pid = mp["deviceID"]
        all_peer_ids.append(pid)
        if pid not in existing_devs:
            cfg.setdefault("devices", []).append({
                "deviceID": pid,
                "name": mp["name"],
                "addresses": mp["addresses"],
                "compression": "metadata",
                "introducer": False,
                "autoAcceptFolders": True,
                "paused": False,
            })

    # Add/update federated folders
    existing_folders = {f["id"]: f for f in cfg.get("folders", [])}
    folder_dev_list = [{"deviceID": pid, "introducedBy": ""} for pid in all_peer_ids]

    for f_id, f_path in node["paths"].items():
        if f_id in existing_folders:
            existing_folders[f_id]["path"] = f_path
            existing_folders[f_id]["devices"] = folder_dev_list
            existing_folders[f_id]["fsWatcherEnabled"] = True
            existing_folders[f_id]["rescanIntervalS"] = 60
        else:
            cfg.setdefault("folders", []).append({
                "id": f_id,
                "label": FOLDER_LABELS.get(f_id, f_id),
                "path": f_path,
                "type": "sendreceive",
                "devices": folder_dev_list,
                "rescanIntervalS": 60,
                "fsWatcherEnabled": True,
                "fsWatcherDelayS": 5,
                "ignorePerms": True,
                "autoNormalize": True,
            })

    put_res = _node_curl(node_key, "/rest/config", method="PUT", payload=cfg)
    if put_res:
        print(f"  ✅ {node['name']} federated across {len(node['paths'])} folders & {len(all_peer_ids)} peers.")
        return True
    print(f"  ❌ Failed to PUT config on {node['name']}")
    return False


def _fetch_node_status(nk: str) -> str:
    ninfo = NODES[nk]
    st = _node_curl(nk, "/rest/system/status")
    conn = _node_curl(nk, "/rest/system/connections")
    if not st:
        return f"  🔴 {ninfo['name']:38s} | OFFLINE"
    conns = (conn or {}).get("connections", {})
    active_peers = sum(1 for c in conns.values() if c.get("connected"))
    uptime = st.get("uptime", 0)
    role = "MASTER INTRODUCER (2TB)" if nk == "l1b" else ("HOST INTRODUCER" if nk == "l1" else "MESH WORKER")
    return f"  🟢 {ninfo['name']:38s} | {role:23s} | Peers: {active_peers} | Uptime: {uptime}s"


def print_cluster_status() -> None:
    from concurrent.futures import ThreadPoolExecutor
    print("\n" + "=" * 78)
    print("🌐 LAUBURU SYNCTHING P2P MESH FEDERATION STATUS (L1b 2TB MASTER SEED)")
    print("=" * 78)
    keys = list(NODES.keys())
    with ThreadPoolExecutor(max_workers=4) as pool:
        lines = list(pool.map(_fetch_node_status, keys))
    for line in lines:
        print(line)
    print("=" * 78)


def main():
    from concurrent.futures import ThreadPoolExecutor
    parser = argparse.ArgumentParser(description="Lauburu Syncthing Mesh Federation Engine v2.0")
    parser.add_argument("--status", action="store_true", help="Show cluster status only")
    args = parser.parse_args()

    if not args.status:
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(federate_node, ["l1b", "l1", "l5", "l3"]))

    print_cluster_status()


if __name__ == "__main__":
    main()

