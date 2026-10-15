#!/usr/bin/env python3
"""
================================================================================
🛡️ Lauburu Mesh: Gateway Storage Sentinel (Zero-Mock Rule #5 Compliance)
================================================================================
Monitors total network storage health across the 7-Layer Mesh.
Automatically executes disk triage operations (cleaning __pycache__, HF cache)
if available space on any layer drops below the 5.0 GB sanctuary limit.
"""

import os
import shutil
import time
import subprocess
import json
from pathlib import Path

# Mesh Tailscale IP Matrix
NODES = {
    "L1_MacHost": "localhost",
    "L2_MacBookPro": "10.1.0.11",
    "L3_LinuxMini": "10.1.0.12",
    "L4_LinuxTablet": "100.81.92.125",
    "L5_MacBookAir": "100.93.158.96"
}

MINIMUM_FREE_GB = 5.0

def check_local_storage():
    """Checks L1 Host storage."""
    free_b = shutil.disk_usage("/Users/aaron").free
    return free_b / (1024**3)

def check_remote_storage(ip):
    """Probes remote node storage health via batch SSH."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2", ip, "df -k / | tail -1 | awk '{print $4}'"]
    try:
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
        if res:
            return int(res) / (1024**2) # Convert KB to GB
    except Exception:
        pass
    return None

def trigger_healing(node_name, ip):
    """Executes Rule #5 self-healing (pycache & temp deletion)."""
    print(f"⚠️ {node_name} storage critical. Triggering self-healing protocol.")
    heal_cmd = "find /Volumes/Lauburu-Monorepo /Users/aaron/teamwork_projects -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true; rm -rf ~/.cache/huggingface/hub || true"
    
    if ip == "localhost":
        subprocess.run(heal_cmd, shell=True, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(["ssh", "-o", "BatchMode=yes", ip, heal_cmd], stderr=subprocess.DEVNULL)

def run_sentinel_loop():
    print("🛡️ Gateway Storage Sentinel Online.")
    while True:
        status_report = {}
        for name, ip in NODES.items():
            gb_free = check_local_storage() if ip == "localhost" else check_remote_storage(ip)
            if gb_free is None:
                status_report[name] = "OFFLINE"
            else:
                status_report[name] = f"{gb_free:.2f} GB"
                if gb_free < MINIMUM_FREE_GB:
                    trigger_healing(name, ip)
        
        # Log telemetry for Screen Lens / Genetic Engine
        with open("/Volumes/Lauburu-Monorepo/04_data_and_memory/storage_sentinel_telemetry.json", "w") as f:
            json.dump({"timestamp": time.time(), "nodes": status_report}, f)
            
        time.sleep(300) # Probe every 5 minutes

if __name__ == "__main__":
    run_sentinel_loop()
