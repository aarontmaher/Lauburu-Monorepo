#!/usr/bin/env python3
"""
================================================================================
Syncthing Mesh Federation Engine v3.1 — Lauburu Sovereign Ecosystem
================================================================================
Subsystem: 06_scripts_and_tooling/network/syncthing_mesh_federation.py

Architecture:
- Full 8-Node Autonomous P2P Block Federation + Zero-Prompt Auto-Acceptor:
  1. L1b (Mac Mini M2 Pro, 2 TB NVMe SSD, 40 Gbps TB4 `10.0.0.3`) — Master Introducer
  2. L1  (Mac Mini M4 Pro Host, 40 Gbps TB4 `10.0.0.2`) — Host Introducer
  3. L1a (MacBook Air M4 Worker, 40 Gbps TB4 `10.0.0.5`) — Metal Worker
  4. L2  (MacBook Pro Intel, 40 Gbps TB4 `10.0.0.4`) — Secondary Vault & Teacher Target
  5. L8  (Linux Mini Hub `lauburu`, 40 Gbps TB4 `10.0.0.8`) — Linux TB4 Hub
  6. L3  (Linux Head Node Ryzen, LAN `192.168.8.225` / TS `100.101.39.98`) — Linux Replica
  7. L6  (Pixel 10 Pro XL Termux Daemon, `:8385` / `:22001`) — Mobile Storage Pool
  8. L4  (Pixel AVF Debian 13 microVM, `10.64.219.53:22000`) — Edge Linux Container
- Enforces Deletion-Safe Topology:
  - Code & Vault folders (`lauburu-scripts`, `lauburu-obsidian`, `lauburu-core-infra`,
    `lauburu-deps-vault`) are `sendreceive` on Master Introducers (`L1`, `L1b`) with
    `/rest/db/override` authority, and `receiveonly` (with `/rest/db/revert`) on
    worker replicas (`L1a`, `L2`, `L8`, `L3`, `L6`, `L4`) so an empty worker directory
    can never propagate accidental deletions back to `L1`.
  - Telemetry folder (`lauburu-lora-telemetry`) is `sendreceive` across all 8 nodes.
- Sets `autoAcceptFolders = True` on every peer AND in `defaults.device` so
  newly introduced devices never trigger manual confirmation banners.
================================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

HOSTNAME = socket.gethostname().lower()

NODES: Dict[str, Dict[str, Any]] = {
    "l1b": {
        "name": "Mac-Mini-M2-Pro-2TB-Master (L1b)",
        "ssh_cmd": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", "aaronmaher@10.0.0.3"],
        "is_local": HOSTNAME.startswith("aarons-mac-mini"),
        "introducer": True,
        "is_master_seed": True,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "Uuy5Mj6vNJGdXE2VSroybcmzSAmHyXww",
        "device_id": "PYQIT6T-A662YKN-ZZA4YZO-XWJHQZK-KD3AKFS-IERB4WI-VP7FT6Q-P4DNFAN",
        "addresses": [
            "tcp://10.0.0.3:22000",
            "tcp://192.168.8.114:22000",
            "tcp://100.104.128.34:22000",
            "dynamic",
        ],
        "default_folder_path": "/Volumes/AI_Projects/Lauburu_Master",
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
        "ssh_cmd": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", "aaron@10.0.0.2"],
        "is_local": HOSTNAME.startswith("mac-mini"),
        "introducer": True,
        "is_master_seed": True,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "Gz6WJUd9GdCWUR3oYpQGYrgTHT4hDZy5",
        "device_id": "W5KWZRZ-ZCIMXNW-4DL46C2-MRJLB24-L6LXIEX-GO4FNOX-QYLASSN-YHIHDA3",
        "addresses": [
            "tcp://10.0.0.2:22000",
            "tcp://192.168.8.143:22000",
            "tcp://192.168.8.230:22000",
            "tcp://100.119.199.76:22000",
            "dynamic",
        ],
        "default_folder_path": "/Users/aaron/DFS_UNIFIED",
        "paths": {
            "lauburu-scripts": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling",
            "lauburu-obsidian": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault",
            "lauburu-core-infra": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure",
            "lauburu-lora-telemetry": "/Users/aaron/DFS_UNIFIED/lora_datasets",
            "lauburu-deps-vault": "/Users/aaron/DFS_UNIFIED/deps_vault",
        },
    },
    "l5": {
        "name": "MacBook-Air-M4-Worker (L1a)",
        "ssh_cmd": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", "aaronmaher@10.0.0.5"],
        "is_local": HOSTNAME.startswith("mac-air"),
        "introducer": False,
        "is_master_seed": False,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "mibq9XMsW3GjZDQ5UqDrXXFpTtV57Rd5",
        "device_id": "TOZX7SM-D424PUU-ANLAOF4-DVZSOFG-BW46NSE-67OEM6R-QTWJFMZ-TFYNDA3",
        "addresses": [
            "tcp://10.0.0.5:22000",
            "tcp://192.168.8.176:22000",
            "tcp://100.121.202.34:22000",
            "dynamic",
        ],
        "default_folder_path": "/Users/aaronmaher/DFS_UNIFIED",
        "paths": {
            "lauburu-scripts": "/Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling",
            "lauburu-obsidian": "/Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault",
            "lauburu-core-infra": "/Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure",
            "lauburu-lora-telemetry": "/Users/aaronmaher/DFS_UNIFIED/lora_datasets",
            "lauburu-deps-vault": "/Users/aaronmaher/DFS_UNIFIED/deps_vault",
        },
    },
    "l2": {
        "name": "MacBook-Pro-Intel (L2)",
        "ssh_cmd": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", "aaronmaher@10.0.0.4"],
        "is_local": HOSTNAME.startswith("l2-macbook") or HOSTNAME.startswith("mac-intel"),
        "introducer": False,
        "is_master_seed": False,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "WaV5n5DVW3aUkExQVGDEt7XqD4HJeey4",
        "device_id": "EES54ZD-5KBNY7R-6OXQXU2-JRR5WSS-PFZ2XOG-SHHAPJ7-PE22VAC-ZTIOQA6",
        "addresses": [
            "tcp://10.0.0.4:22000",
            "tcp://192.168.8.127:22000",
            "tcp://100.103.212.21:22000",
            "dynamic",
        ],
        "default_folder_path": "/Users/aaronmaher/DFS_UNIFIED",
        "paths": {
            "lauburu-scripts": "/Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling",
            "lauburu-obsidian": "/Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault",
            "lauburu-core-infra": "/Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure",
            "lauburu-lora-telemetry": "/Users/aaronmaher/DFS_UNIFIED/lora_datasets",
            "lauburu-deps-vault": "/Users/aaronmaher/DFS_UNIFIED/deps_vault",
        },
    },
    "l8": {
        "name": "Linux-Mini-Hub-TB4 (L8)",
        "ssh_cmd": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", "linuxmini@10.0.0.8"],
        "is_local": HOSTNAME == "lauburu",
        "introducer": False,
        "is_master_seed": False,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "95pJhvKY7tzjRyxwJwtx9FA3Srrr5UeM",
        "device_id": "ZUBQOCL-Y3GIN2L-I5A3MZ4-FXU6DWH-YG5375A-XWLEXG2-JULQGGZ-E7GRXAE",
        "addresses": [
            "tcp://10.0.0.8:22000",
            "tcp://192.168.8.242:22000",
            "tcp://100.121.247.8:22000",
            "dynamic",
        ],
        "default_folder_path": "/home/linuxmini/lauburu_sync",
        "paths": {
            "lauburu-scripts": "/home/linuxmini/lauburu_sync/06_scripts_and_tooling",
            "lauburu-obsidian": "/home/linuxmini/lauburu_sync/obsidian_vault",
            "lauburu-core-infra": "/home/linuxmini/lauburu_sync/00_core_infrastructure",
            "lauburu-lora-telemetry": "/home/linuxmini/lauburu_sync/lora_datasets",
            "lauburu-deps-vault": "/home/linuxmini/lauburu_sync/deps_vault",
        },
    },
    "l3": {
        "name": "Linux-Head-Node-Ryzen (L3)",
        "ssh_cmd": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", "linux@192.168.8.225"],
        "is_local": HOSTNAME == "linux",
        "introducer": False,
        "is_master_seed": False,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "F6ToKVTkoU3MVJF5jNRh5zWPhkdhocZP",
        "device_id": "C4LVDFV-WU52UP7-ZBFEJHJ-K6WRXYB-SG3CW3O-Y7JFF25-JM6HUM7-XQ223AD",
        "addresses": [
            "tcp://192.168.8.225:22000",
            "tcp://100.101.39.98:22000",
            "dynamic",
        ],
        "default_folder_path": "/home/linux/lauburu_sync",
        "paths": {
            "lauburu-scripts": "/home/linux/lauburu_sync/06_scripts_and_tooling",
            "lauburu-obsidian": "/home/linux/lauburu_sync/obsidian_vault",
            "lauburu-core-infra": "/home/linux/lauburu_sync/00_core_infrastructure",
            "lauburu-lora-telemetry": "/home/linux/lauburu_sync/lora_datasets",
            "lauburu-deps-vault": "/home/linux/lauburu_sync/deps_vault",
        },
    },
    "l6": {
        "name": "Pixel-10-Pro-XL-Termux (L6)",
        "ssh_cmd": ["ssh", "-p", "8022", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "100.114.215.68"],
        "is_local": False,
        "introducer": False,
        "is_master_seed": False,
        "api_url": "http://127.0.0.1:8385",
        "api_key": "F79Qtwd4fx73NKZFfdp9y3MnEQQgwCc2",
        "device_id": "KC3BJDO-K3UD5SQ-BCTSP7L-CEWTRTM-6OC67OJ-ZCHLBX4-H7ROJ3I-FQNYXQ2",
        "addresses": [
            "tcp://192.168.8.213:22001",
            "tcp://100.114.215.68:22001",
            "tcp://10.64.219.136:22001",
            "dynamic",
        ],
        "default_folder_path": "/sdcard/Lauburu_Storage_Pool",
        "paths": {
            "lauburu-scripts": "/sdcard/Lauburu_Storage_Pool/06_scripts_and_tooling",
            "lauburu-obsidian": "/sdcard/Lauburu_Storage_Pool/obsidian_vault",
            "lauburu-core-infra": "/sdcard/Lauburu_Storage_Pool/00_core_infrastructure",
            "lauburu-lora-telemetry": "/sdcard/Lauburu_Storage_Pool/lora_datasets",
            "lauburu-deps-vault": "/sdcard/Lauburu_Storage_Pool/deps_vault",
        },
    },
    "l4": {
        "name": "Pixel-AVF-Debian-13 (L4)",
        "ssh_cmd": [
            "ssh", "-p", "8022", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
            "100.114.215.68", "ssh -o BatchMode=yes -o ConnectTimeout=3 droid@10.64.219.53"
        ],
        "is_local": HOSTNAME == "debian",
        "introducer": False,
        "is_master_seed": False,
        "api_url": "http://127.0.0.1:8384",
        "api_key": "LMDJeCzfMMYYX75h2kovKiDWjNhjeo6i",
        "device_id": "XF3ZCZR-G4LGSG4-X5MI3QP-H557BSO-PSRVZ2J-FTA2CHX-JAXKSX6-UBZOHAU",
        "addresses": [
            "tcp://10.64.219.53:22000",
            "tcp://100.80.64.5:22000",
            "dynamic",
        ],
        "default_folder_path": "/home/droid/lauburu_sync",
        "paths": {
            "lauburu-scripts": "/home/droid/lauburu_sync/06_scripts_and_tooling",
            "lauburu-obsidian": "/home/droid/lauburu_sync/obsidian_vault",
            "lauburu-core-infra": "/home/droid/lauburu_sync/00_core_infrastructure",
            "lauburu-lora-telemetry": "/home/droid/lauburu_sync/lora_datasets",
            "lauburu-deps-vault": "/home/droid/lauburu_sync/deps_vault",
        },
    },
}

# Mobile GUI peers:
# LNVQC7N is the Android WebView GUI wrapper on L6 (:22000). We only share its
# already-accepted folders with LNVQC7N so it never shows yellow "Add new folder?"
# banners, while KC3BJDO (L6 Termux daemon on :22001) syncs ALL 5 folders onto
# /sdcard/Lauburu_Storage_Pool automatically with autoAcceptFolders=True.
MOBILE_PEERS = [
    {
        "deviceID": "LNVQC7N-35SA4QV-PF3QUTH-4SE2ZSX-NAXP5SW-DYDM2E5-MACM7OE-CIXAEAY",
        "name": "Pixel-10-Pro-XL-GUI (L6)",
        "addresses": ["tcp://192.168.8.213:22000", "tcp://100.114.215.68:22000", "dynamic"],
        "accepted_folders": {"default", "lauburu-core-infra", "lauburu-obsidian", "lauburu-scripts", "screen-lens-plugin"},
    },
    {
        "deviceID": "BF6KFOQ-URV74DS-PXCLYCU-A34NV3T-4WJV4IJ-EWQGS4I-K3SQLIQ-5R2ZWA2",
        "name": "Samsung-Galaxy-S20 (L7)",
        "addresses": ["tcp://192.168.8.101:22000", "tcp://100.124.199.15:22000", "dynamic"],
        "accepted_folders": {"default", "lauburu-core-infra", "lauburu-obsidian", "lauburu-scripts", "lauburu-deps-vault", "lauburu-lora-telemetry"},
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


def _run_remote(node_key: str, shell_cmd: str, input_str: Optional[str] = None, timeout: int = 12) -> subprocess.CompletedProcess:
    node = NODES[node_key]
    if node["is_local"]:
        return subprocess.run(shell_cmd, shell=True, input=input_str, capture_output=True, text=True, timeout=timeout)
    return subprocess.run([*node["ssh_cmd"], shell_cmd], input=input_str, capture_output=True, text=True, timeout=timeout)


def _node_curl(node_key: str, endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    node = NODES[node_key]
    api_key = node["api_key"]
    url = f"{node['api_url']}{endpoint}"

    try:
        if method == "GET":
            cmd = f"curl -sk -H X-API-Key:{api_key} {url}"
            res = _run_remote(node_key, cmd, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
            return None

        body_str = json.dumps(payload) if payload is not None else ""
        cmd = f"curl -sk --max-time 8 -X {method} -H Content-Type:application/json -H X-API-Key:{api_key} --data-binary @- {url}"
        res = _run_remote(node_key, cmd, input_str=body_str, timeout=12)
        if res.returncode in (0, 28):
            return {"status": "OK"}
    except Exception:
        pass
    return None


def _ensure_paths_and_stignore(node_key: str) -> None:
    node = NODES[node_key]
    dirs = list(node["paths"].values())
    escaped_ignore = STIGNORE_CONTENT.replace("'", "'\\''")
    cmds = []
    for d in dirs:
        cmds.append(f"mkdir -p '{d}/.stfolder' && printf '{escaped_ignore}' > '{d}/.stignore'")
    full_cmd = " && ".join(cmds)
    try:
        _run_remote(node_key, full_cmd, timeout=12)
    except Exception:
        pass


def federate_node(node_key: str) -> bool:
    node = NODES[node_key]
    print(f"🔄 Configuring Syncthing on {node['name']}...")
    _ensure_paths_and_stignore(node_key)

    cfg = _node_curl(node_key, "/rest/config")
    if not cfg:
        print(f"  ❌ Could not fetch Syncthing config on {node_key}")
        return False

    # 1. Enforce global defaults so any future device/folder auto-accepts without GUI prompts
    defaults = cfg.setdefault("defaults", {})
    dev_defaults = defaults.setdefault("device", {})
    dev_defaults["autoAcceptFolders"] = True
    folder_defaults = defaults.setdefault("folder", {})
    folder_defaults["path"] = node.get("default_folder_path", "~")
    folder_defaults["ignorePerms"] = True
    folder_defaults["autoNormalize"] = True
    folder_defaults["rescanIntervalS"] = 60
    folder_defaults["fsWatcherEnabled"] = True

    existing_devs = {d["deviceID"]: d for d in cfg.get("devices", []) if d.get("deviceID")}

    # 2. Add/update all 8 controllable mesh nodes with autoAcceptFolders=True
    controllable_peer_ids: List[str] = []
    for peer_key, peer_info in NODES.items():
        pid = peer_info["device_id"]
        controllable_peer_ids.append(pid)
        if pid in existing_devs:
            existing_devs[pid]["name"] = peer_info["name"]
            existing_devs[pid]["addresses"] = peer_info["addresses"]
            existing_devs[pid]["introducer"] = peer_info["introducer"]
            existing_devs[pid]["autoAcceptFolders"] = True
            existing_devs[pid]["paused"] = False
            existing_devs[pid]["ignoredFolders"] = []
        else:
            cfg.setdefault("devices", []).append({
                "deviceID": pid,
                "name": peer_info["name"],
                "addresses": peer_info["addresses"],
                "compression": "metadata",
                "introducer": peer_info["introducer"],
                "autoAcceptFolders": True,
                "paused": False,
                "ignoredFolders": [],
            })

    # 3. Add/update mobile GUI peers with autoAcceptFolders=True
    for mp in MOBILE_PEERS:
        pid = mp["deviceID"]
        if pid in existing_devs:
            existing_devs[pid]["name"] = mp["name"]
            existing_devs[pid]["addresses"] = mp["addresses"]
            existing_devs[pid]["autoAcceptFolders"] = True
            existing_devs[pid]["paused"] = False
        else:
            cfg.setdefault("devices", []).append({
                "deviceID": pid,
                "name": mp["name"],
                "addresses": mp["addresses"],
                "compression": "metadata",
                "introducer": False,
                "autoAcceptFolders": True,
                "paused": False,
            })

    # Ensure any other pre-existing devices on this node have autoAcceptFolders=True
    for d in cfg.get("devices", []):
        d["autoAcceptFolders"] = True

    # 4. Add/update federated folders with deletion-safe folder types
    existing_folders = {f["id"]: f for f in cfg.get("folders", []) if f.get("id")}
    is_master = bool(node.get("is_master_seed"))

    for f_id, f_path in node["paths"].items():
        folder_peer_ids = list(controllable_peer_ids)
        for mp in MOBILE_PEERS:
            if f_id in mp["accepted_folders"]:
                folder_peer_ids.append(mp["deviceID"])
        folder_dev_list = [{"deviceID": pid, "introducedBy": ""} for pid in dict.fromkeys(folder_peer_ids)]

        # Telemetry folder is bidirectional everywhere; code/vault folders are
        # sendreceive on Master Seeds (L1, L1b) and receiveonly on replicas so
        # an empty replica directory can never propagate deletions back to L1.
        folder_type = "sendreceive" if (is_master or f_id == "lauburu-lora-telemetry") else "receiveonly"

        if f_id in existing_folders:
            existing_folders[f_id]["label"] = FOLDER_LABELS.get(f_id, f_id)
            existing_folders[f_id]["path"] = f_path
            existing_folders[f_id]["type"] = folder_type
            existing_folders[f_id]["devices"] = folder_dev_list
            existing_folders[f_id]["fsWatcherEnabled"] = True
            existing_folders[f_id]["rescanIntervalS"] = 60
            existing_folders[f_id]["ignorePerms"] = True
            existing_folders[f_id]["paused"] = False
        else:
            cfg.setdefault("folders", []).append({
                "id": f_id,
                "label": FOLDER_LABELS.get(f_id, f_id),
                "path": f_path,
                "type": folder_type,
                "devices": folder_dev_list,
                "rescanIntervalS": 60,
                "fsWatcherEnabled": True,
                "fsWatcherDelayS": 5,
                "ignorePerms": True,
                "autoNormalize": True,
                "paused": False,
            })

    # 5. Auto-accept any pending folders announced by peers in /rest/cluster/pending/folders
    pending_folders = _node_curl(node_key, "/rest/cluster/pending/folders") or {}
    if isinstance(pending_folders, dict):
        for pf_id, pf_info in pending_folders.items():
            if pf_id not in existing_folders and pf_id not in node["paths"]:
                offered_by = list((pf_info.get("offeredBy") or {}).keys())
                label = pf_id
                for ob in (pf_info.get("offeredBy") or {}).values():
                    if ob.get("label"):
                        label = ob["label"]
                        break
                auto_path = f"{node.get('default_folder_path', '~')}/{pf_id}"
                _run_remote(node_key, f"mkdir -p '{auto_path}/.stfolder'", timeout=6)
                dev_ids = list(dict.fromkeys([node["device_id"], *offered_by]))
                cfg.setdefault("folders", []).append({
                    "id": pf_id,
                    "label": label,
                    "path": auto_path,
                    "type": "receiveonly" if not is_master else "sendreceive",
                    "devices": [{"deviceID": pid, "introducedBy": ""} for pid in dev_ids],
                    "rescanIntervalS": 60,
                    "fsWatcherEnabled": True,
                    "ignorePerms": True,
                    "autoNormalize": True,
                })

    put_res = _node_curl(node_key, "/rest/config", method="PUT", payload=cfg)
    if put_res:
        # On master seeds, scan & override; on replicas, revert receiveonly local state so they pull cleanly
        for f_id in node["paths"]:
            if not is_master and f_id != "lauburu-lora-telemetry":
                _node_curl(node_key, f"/rest/db/revert?folder={f_id}", method="POST")
            elif is_master:
                _node_curl(node_key, f"/rest/db/scan?folder={f_id}", method="POST")
        print(f"  ✅ {node['name']} federated across {len(node['paths'])} folders & {len(controllable_peer_ids) + len(MOBILE_PEERS)} peers.")
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
    print("\n" + "=" * 86)
    print("🌐 LAUBURU SYNCTHING P2P MESH FEDERATION STATUS (8-NODE FULL MESH + AUTO-ACCEPT)")
    print("=" * 86)
    keys = list(NODES.keys())
    with ThreadPoolExecutor(max_workers=8) as pool:
        lines = list(pool.map(_fetch_node_status, keys))
    for line in lines:
        print(line)
    print("=" * 86)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lauburu Syncthing Mesh Federation Engine v3.1")
    parser.add_argument("--status", action="store_true", help="Show cluster status only")
    args = parser.parse_args()

    if not args.status:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(federate_node, list(NODES.keys())))

    print_cluster_status()


if __name__ == "__main__":
    main()
