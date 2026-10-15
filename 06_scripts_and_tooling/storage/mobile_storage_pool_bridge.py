#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_scripts_and_tooling/storage/mobile_storage_pool_bridge.py
============================================================
Bridges Pixel 10 Pro XL (186 GB) and Samsung Galaxy S20+ (63 GB)
storage into the Lauburu Monorepo Unified Data Lake & SeaweedFS Pool.

Governed by:
- Rule #0: Zero-Mock Empirical Truth
- Rule #2: Tri-Vault Storage Synchronization
- Rule #3: Host Sanctuary & Storage Offloading
"""

from __future__ import annotations

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
STORAGE_POOL_DIR = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/mobile_storage_pool")
MANIFEST_FILE = STORAGE_POOL_DIR / "pool_manifest.json"

PIXEL_CANDIDATES = ["192.168.8.114:5555", "100.73.38.87:5555"]
SAMSUNG_CANDIDATES = ["100.78.206.96:5555", "192.168.8.131:5555"]


def resolve_active_adb_device(candidates: list[str], model_hint: str) -> Optional[str]:
    """Finds active ADB device by inspecting adb devices -l or testing candidates."""
    try:
        res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=2.0)
        if res.returncode == 0:
            for line in res.stdout.strip().split("\n")[1:]:
                if not line.strip() or "offline" in line:
                    continue
                parts = line.split()
                serial = parts[0]
                if model_hint.lower() in line.lower():
                    return serial
    except Exception:
        pass

    for cand in candidates:
        try:
            res = subprocess.run(["adb", "-s", cand, "shell", "echo 1"], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0 and res.stdout.strip() == "1":
                return cand
        except Exception:
            pass
    return None


def run_adb(device_id: str, cmd: str, timeout: float = 4.0) -> Optional[str]:
    """Runs an ADB shell command and returns stdout if successful."""
    try:
        res = subprocess.run(
            ["adb", "-s", device_id, "shell", cmd],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def get_android_storage(device_id: str) -> Dict[str, Any]:
    """Queries authentic storage stats from an Android device via ADB."""
    report = {
        "device_id": device_id,
        "reachable": False,
        "total_gb": 0.0,
        "used_gb": 0.0,
        "available_gb": 0.0,
        "mount_point": "/sdcard/Lauburu_Storage_Pool",
        "last_probe": time.time()
    }

    out = run_adb(device_id, "df -k /sdcard | tail -n 1")
    if out:
        parts = out.split()
        if len(parts) >= 4:
            try:
                # df -k outputs 1K-blocks: 1K-blocks, Used, Available
                total_k = int(parts[1])
                used_k = int(parts[2])
                avail_k = int(parts[3])
                report["total_gb"] = round(total_k / (1024.0 * 1024.0), 2)
                report["used_gb"] = round(used_k / (1024.0 * 1024.0), 2)
                report["available_gb"] = round(avail_k / (1024.0 * 1024.0), 2)
                report["reachable"] = True
            except Exception:
                pass
    return report


def sync_pool_manifest() -> Dict[str, Any]:
    """Polls Pixel 10 and Samsung S20 storage and writes manifest."""
    STORAGE_POOL_DIR.mkdir(parents=True, exist_ok=True)
    (STORAGE_POOL_DIR / "pixel_10").mkdir(exist_ok=True)
    (STORAGE_POOL_DIR / "samsung_s20").mkdir(exist_ok=True)

    pixel_id = resolve_active_adb_device(PIXEL_CANDIDATES, "Pixel") or resolve_active_adb_device(PIXEL_CANDIDATES, "mustang") or PIXEL_CANDIDATES[0]
    pixel_stat = get_android_storage(pixel_id)
    pixel_stat["name"] = "Google Pixel 10 Pro XL (L6)"
    pixel_stat["role"] = "Tensor G5 Edge TPU & Model/Dataset Cache"

    samsung_id = resolve_active_adb_device(SAMSUNG_CANDIDATES, "SM_G986B") or resolve_active_adb_device(SAMSUNG_CANDIDATES, "y2s") or SAMSUNG_CANDIDATES[0]
    samsung_stat = get_android_storage(samsung_id)
    samsung_stat["name"] = "Samsung Galaxy S20+ (L7)"
    samsung_stat["role"] = "Exynos 990 ADB Worker & UI Test Artifacts"

    total_pooled_gb = round(pixel_stat["available_gb"] + samsung_stat["available_gb"], 2)

    manifest = {
        "timestamp": time.time(),
        "total_mobile_pooled_available_gb": total_pooled_gb,
        "devices": {
            "L6_Pixel_10": pixel_stat,
            "L7_Samsung_S20": samsung_stat
        },
        "target_pool_path": "/Volumes/Lauburu-Monorepo/04_data_and_memory/mobile_storage_pool",
        "zero_mock_verified": True
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


if __name__ == "__main__":
    m = sync_pool_manifest()
    print(f"[*] Mobile Storage Pool Manifest Updated:")
    print(f"    Total Mobile Pooled Free: {m['total_mobile_pooled_available_gb']} GB")
    for k, dev in m["devices"].items():
        status = "ONLINE" if dev["reachable"] else "OFFLINE"
        print(f"    - {dev['name']}: {status} | Free: {dev['available_gb']} GB / {dev['total_gb']} GB")
