import re
"""
Lauburu Mesh - On-Demand Ephemeral JIT Sharding Controller
Enforces Canonical Inference Engine Policy:
- prima.cpp is the permanent canonical baseline engine.
- Petals, Exo, and llama.cpp RPC are strictly EPHEMERAL: spun up on-demand for sharding, then immediately terminated.
"""

import os
import sys
import time
import json
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

MESH_NODES = {
    "L1_Mac_Node": {"ip": "100.119.199.76", "local_ip": "127.0.0.1", "type": "MACOS_HOST", "ssh_user": "aaron", "ssh_port": 22},
    "L2_MacBook_Pro": {"ip": "100.103.212.21", "local_ip": "192.168.8.127", "type": "MACOS_WORKER", "ssh_user": "aaron", "ssh_port": 22},
    "L3_Linux_Head_Node": {"ip": "100.101.39.98", "local_ip": "192.168.8.224", "type": "LINUX_HUB", "ssh_user": "aaron", "ssh_port": 22},
    "L5_MacBook_Air": {"ip": "100.121.202.34", "local_ip": "192.168.8.222", "type": "MACOS_WORKER", "ssh_user": "aaronmaher", "ssh_port": 22},
    "L6_Pixel_10_Pro_XL": {"ip": "100.73.38.87", "local_ip": "DHCP", "type": "ANDROID_TERMUX", "ssh_user": "u0_a363", "ssh_port": 8022},
    "L7_Samsung_S20": {"ip": "100.84.40.95", "local_ip": "DHCP", "type": "ANDROID_ADB", "adb_target": "100.84.40.95:5555"}
}

class EphemeralShardingController:
    @staticmethod
    def audit_all_nodes() -> Dict[str, Any]:
        """Audits all mesh nodes to verify prima.cpp status and ensure zero persistent zombie sharding daemons."""
        node_status = {}
        total_ram_reclaimed_mb = 0.0
        total_watts_saved = 0.0

        for name, meta in MESH_NODES.items():
            status = {
                "name": name,
                "type": meta["type"],
                "prima_cpp_running": False,
                "ephemeral_shards_active": [],
                "ram_freed_mb": 0.0
            }

            if meta["type"] == "ANDROID_TERMUX":
                try:
                    cmd = f"ssh -o ConnectTimeout=3 -p {meta['ssh_port']} {meta['ip']} \"ps aux | grep -E 'prima|petals|rpc|p2pd|exo' | grep -v grep\""
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                    out = res.stdout
                    if "prima-server" in out or "prima" in out:
                        status["prima_cpp_running"] = True
                    for z in ["petals", "p2pd", "ggml-rpc-server", "exo"]:
                        if re.search(rf'\b{z}\b', out, re.I):
                            status["ephemeral_shards_active"].append(z)
                except Exception as e:
                    status["error"] = str(e)

            elif meta["type"] == "ANDROID_ADB":
                try:
                    cmd = f"adb -s {meta['adb_target']} shell \"ps -ef | grep -E 'prima|rpc|petals|exo' | grep -v grep\""
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                    out = res.stdout
                    if "prima" in out:
                        status["prima_cpp_running"] = True
                    for z in ["rpc-server", "petals", "exo"]:
                        if re.search(rf'\b{z}\b', out, re.I):
                            status["ephemeral_shards_active"].append(z)
                except Exception as e:
                    status["error"] = str(e)

            elif meta["type"] == "MACOS_HOST":
                res = subprocess.run("ps aux | grep -E 'prima|llama-server' | grep -v grep", shell=True, capture_output=True, text=True)
                out = res.stdout
                status["prima_cpp_running"] = ("prima" in out or "llama-server" in out)

            # Rule 1 (Zero-Mock): Only report metrics measured from live syscalls/probes
            status["ram_freed_mb"] = 0.0
            status["watts_saved"] = 0.0
            node_status[name] = status

        return {
            "timestamp": time.time(),
            "policy": "ON_DEMAND_EPHEMERAL_SHARDING",
            "canonical_primary": "prima.cpp",
            "nodes": node_status,
            "total_ram_reclaimed_gb": round(total_ram_reclaimed_mb / 1024.0, 2),
            "total_mesh_power_reduction_watts": round(total_watts_saved, 1),
            "mobile_battery_extension_percent": "--",
            "ttft_latency_reduction_percent": "--"
        }

if __name__ == "__main__":
    audit = EphemeralShardingController.audit_all_nodes()
    print(json.dumps(audit, indent=2))
