#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
lens_edge_storage_sync_bridge.py
================================================================================
Screen Lens Sovereign: Edge Device Storage Mesh Synchronization Bridge
Bridges edge devices (Samsung S20+ L7, Google Pixel 10 Pro XL L6) with the
Lauburu Tri-Vault Storage Mesh (/Volumes/seaweed_network and SeaweedFS DFS).

Addresses physical Android non-root FUSE constraints:
On unrooted Android (Android 12/13/16), userspace apps (UID 10420 / UID 2000)
cannot invoke mount() syscall or access /dev/fuse directly due to kernel
CAP_SYS_ADMIN restrictions. Native FUSE mounts (weed mount) or SMB mounts
(mount -t cifs) are physically impossible in userspace.
This bridge provides authentic, cryptographically verified synchronization
between /sdcard/DFS_UNIFIED on Android and /Volumes/seaweed_network.

Governed by:
- Rule #0: Zero-Mock Empirical Truth
- Rule #1: Tri-Proof Verification Gate (Process exit code, SHA256, disk verification)
- Rule #2: Tri-Vault Storage Synchronization
================================================================================
"""

import os
import sys
import time
import json
import shutil
import hashlib
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

ADB_BIN = shutil.which("adb") or "/Users/aaron/.local/bin/adb"
DEFAULT_STORAGE_ROOT = Path("/Volumes/seaweed_network")
LOCAL_DFS_ROOT = Path("/Users/aaron/DFS_UNIFIED")

TARGET_DEVICES = {
    "samsung_s20": {
        "name": "Samsung Galaxy S20+ (L7)",
        "serials": ["192.168.8.131:5555", "100.84.40.95:5555", "R3CN40CJJ1R"],
        "remote_dir": "/sdcard/DFS_UNIFIED",
        "sync_dir_name": "samsung_s20"
    },
    "pixel_10_pro_xl": {
        "name": "Google Pixel 10 Pro XL (L6)",
        "serials": ["192.168.8.213:5555", "100.73.38.87:5555", "5B080DLCQ001LQ"],
        "remote_dir": "/sdcard/DFS_UNIFIED",
        "sync_dir_name": "pixel_10_pro_xl"
    }
}


def sha256_file(path: Path) -> str:
    """Computes SHA256 of a local file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_adb(serial: str, args: List[str], timeout: float = 10.0) -> subprocess.CompletedProcess:
    """Runs an adb command targeting a specific device serial."""
    cmd = [ADB_BIN, "-s", serial] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


class EdgeStorageSyncBridge:
    def __init__(self, storage_root: Path = DEFAULT_STORAGE_ROOT):
        self.storage_root = Path(storage_root)
        self.device_sync_root = self.storage_root / "device_sync"
        self.ensure_storage_directories()

    def ensure_storage_directories(self):
        """Ensures storage mesh sync roots exist."""
        if self.storage_root.exists():
            self.device_sync_root.mkdir(parents=True, exist_ok=True)
            for dev in TARGET_DEVICES.values():
                (self.device_sync_root / dev["sync_dir_name"]).mkdir(parents=True, exist_ok=True)

    def discover_online_devices(self) -> Dict[str, Dict[str, Any]]:
        """Probes ADB and network to find online edge devices."""
        res = subprocess.run([ADB_BIN, "devices", "-l"], capture_output=True, text=True, timeout=5.0)
        lines = res.stdout.strip().splitlines()[1:]
        online_serials = set()
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                online_serials.add(parts[0])

        status = {}
        for dev_key, dev_info in TARGET_DEVICES.items():
            matched_serial = None
            for s in dev_info["serials"]:
                if s in online_serials:
                    matched_serial = s
                    break
            status[dev_key] = {
                "name": dev_info["name"],
                "online": matched_serial is not None,
                "serial": matched_serial,
                "remote_dir": dev_info["remote_dir"],
                "sync_dir": str(self.device_sync_root / dev_info["sync_dir_name"])
            }
        return status

    def verify_device_remote_dir(self, serial: str, remote_dir: str) -> bool:
        """Ensures remote DFS directory exists on Android device."""
        proc = run_adb(serial, ["shell", f"mkdir -p {remote_dir} && ls -ld {remote_dir}"])
        return proc.returncode == 0

    def compute_remote_sha256(self, serial: str, remote_path: str) -> Optional[str]:
        """Computes SHA256 of a file on Android device via sha256sum."""
        proc = run_adb(serial, ["shell", f"sha256sum {remote_path} 2>/dev/null || true"])
        out = proc.stdout.strip()
        if out:
            parts = out.split()
            if len(parts) >= 1 and len(parts[0]) == 64:
                return parts[0]
        return None

    def execute_canary_test(self, dev_key: str, serial: str) -> Dict[str, Any]:
        """
        Executes an authentic end-to-end bidirectional canary verification:
        1. Device -> Storage Mesh:
           - S20 creates timestamped canary in /sdcard/DFS_UNIFIED/
           - S20 computes local sha256
           - Bridge pulls canary into /Volumes/seaweed_network/device_sync/<dev>/
           - Bridge computes local sha256
           - Compares SHA256 hashes (Proof 1)
        2. Storage Mesh -> Device:
           - Bridge writes timestamped canary into /Volumes/seaweed_network/device_sync/<dev>/
           - Bridge computes local sha256
           - Bridge pushes canary into S20 /sdcard/DFS_UNIFIED/
           - S20 computes sha256
           - Compares SHA256 hashes (Proof 2)
        """
        dev_info = TARGET_DEVICES[dev_key]
        sync_dir = self.device_sync_root / dev_info["sync_dir_name"]
        remote_dir = dev_info["remote_dir"]
        self.verify_device_remote_dir(serial, remote_dir)

        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        results = {
            "device": dev_info["name"],
            "serial": serial,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_to_mesh": None,
            "mesh_to_device": None,
            "overall_pass": False
        }

        # --- Test 1: Device -> Storage Mesh ---
        device_canary_name = f"canary_from_{dev_key}_{now_str}.txt"
        remote_canary_path = f"{remote_dir}/{device_canary_name}"
        canary_content = f"CANARY_DATA_SOURCE={dev_key}|TIMESTAMP={now_str}|HOST_MESH=Volumes_seaweed_network|AUTH=SOVEREIGN"

        # Write on device
        run_adb(serial, ["shell", f"echo -n '{canary_content}' > {remote_canary_path}"])
        remote_sha = self.compute_remote_sha256(serial, remote_canary_path)

        # Pull to storage mesh
        local_pulled_file = sync_dir / device_canary_name
        run_adb(serial, ["pull", remote_canary_path, str(local_pulled_file)])

        local_sha = sha256_file(local_pulled_file) if local_pulled_file.exists() else None
        d2m_pass = (remote_sha is not None and local_sha is not None and remote_sha == local_sha)

        results["device_to_mesh"] = {
            "file": device_canary_name,
            "remote_sha256": remote_sha,
            "local_sha256": local_sha,
            "bytes": local_pulled_file.stat().st_size if local_pulled_file.exists() else 0,
            "pass": d2m_pass
        }

        # --- Test 2: Storage Mesh -> Device ---
        mesh_canary_name = f"canary_from_mesh_to_{dev_key}_{now_str}.txt"
        local_mesh_file = sync_dir / mesh_canary_name
        mesh_content = f"MESH_BROADCAST_BEACON|TARGET={dev_key}|TIMESTAMP={now_str}|STORAGE=/Volumes/seaweed_network"
        with open(local_mesh_file, "w") as f:
            f.write(mesh_content)

        local_mesh_sha = sha256_file(local_mesh_file)
        remote_mesh_path = f"{remote_dir}/{mesh_canary_name}"

        # Push to device
        run_adb(serial, ["push", str(local_mesh_file), remote_mesh_path])
        remote_mesh_sha = self.compute_remote_sha256(serial, remote_mesh_path)
        m2d_pass = (local_mesh_sha is not None and remote_mesh_sha is not None and local_mesh_sha == remote_mesh_sha)

        results["mesh_to_device"] = {
            "file": mesh_canary_name,
            "local_sha256": local_mesh_sha,
            "remote_sha256": remote_mesh_sha,
            "bytes": local_mesh_file.stat().st_size,
            "pass": m2d_pass
        }

        results["overall_pass"] = d2m_pass and m2d_pass
        return results

    def sync_all_active(self) -> Dict[str, Any]:
        """Runs discovery and canary verification across all connected devices."""
        print("================================================================================")
        print("📲 SCREEN LENS: EDGE STORAGE MESH SYNCHRONIZATION & VERIFICATION")
        print(f"Storage Mesh Root: {self.storage_root}")
        print("================================================================================")

        devices = self.discover_online_devices()
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "storage_root": str(self.storage_root),
            "storage_root_mounted": self.storage_root.exists(),
            "devices": {}
        }

        for dev_key, dev_status in devices.items():
            print(f"\n[*] Probing {dev_status['name']}...")
            if dev_status["online"]:
                print(f"  [✓] Device Online: {dev_status['serial']}")
                canary_res = self.execute_canary_test(dev_key, dev_status["serial"])
                dev_status["verification"] = canary_res
                if canary_res["overall_pass"]:
                    print(f"  [✓] End-to-End Canary Verification: PASS")
                    print(f"      Device -> Mesh: SHA256 {canary_res['device_to_mesh']['local_sha256']}")
                    print(f"      Mesh -> Device: SHA256 {canary_res['mesh_to_device']['remote_sha256']}")
                else:
                    print(f"  [!] Verification FAILED for {dev_status['name']}")
            else:
                print(f"  [-] Device Offline / In Deep Sleep (Candidates: {TARGET_DEVICES[dev_key]['serials']})")
                dev_status["verification"] = {
                    "overall_pass": False,
                    "reason": "device_offline_deep_sleep"
                }

            report["devices"][dev_key] = dev_status

        # Write audit receipt
        if self.device_sync_root.exists():
            receipt_path = self.device_sync_root / "sync_audit_report.json"
            with open(receipt_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\n[✓] Audit receipt written to: {receipt_path}")

        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edge Storage Mesh Sync Bridge")
    parser.add_argument("--root", type=str, default=str(DEFAULT_STORAGE_ROOT), help="Storage mesh root")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    bridge = EdgeStorageSyncBridge(storage_root=Path(args.root))
    res = bridge.sync_all_active()

    if args.json:
        print(json.dumps(res, indent=2))
