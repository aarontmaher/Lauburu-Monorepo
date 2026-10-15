#!/usr/bin/env python3
"""
Autonomous Lens Cross-Device Training Loop
Executes randomized cross-device round trips via SSH and KDE Connect.
Distills mesh telemetry into Instruction/Input/Output pairs for VLA training.
Appends directly to the PySpark LoRA Data Lake.
"""

import json
import os
import random
import subprocess
import time
from datetime import datetime

LORA_LAKE = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl"

# Hardware Matrix mapped from Rule 0
NODES = [
    {"name": "L2_MacBook_Pro", "ip": "100.103.212.21", "type": "ssh"},
    {"name": "L3_Linux_Head", "ip": "100.101.39.98", "type": "ssh"},
    {"name": "L4_Linux_Tablet", "ip": "192.168.8.176", "type": "ssh"},
    {"name": "L5_MacBook_Air", "ip": "169.254.59.109", "type": "ssh"},
    {"name": "L6_Pixel_10", "type": "kdeconnect"},
    {"name": "L7_Galaxy_S20", "type": "kdeconnect"}
]

def run_ssh_round_trip(ip):
    start = time.time()
    try:
        cmd = ["ssh", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", f"aaron@{ip}", "echo 'Lens Mesh Sync'"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        rtt = (time.time() - start) * 1000
        if res.returncode == 0:
            return {"status": "SUCCESS", "rtt_ms": round(rtt, 2), "output": res.stdout.strip()}
        else:
            return {"status": "FAIL", "rtt_ms": round(rtt, 2), "error": res.stderr.strip()[:100]}
    except Exception as e:
        return {"status": "TIMEOUT", "rtt_ms": None, "error": str(e)}

def run_kdeconnect_round_trip():
    start = time.time()
    try:
        # Ping all paired reachable devices via KDE Connect CLI
        cmd = ["kdeconnect-cli", "-a", "--ping-msg", "Lens Sovereign Training Round-Trip"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        rtt = (time.time() - start) * 1000
        if res.returncode == 0:
            return {"status": "SUCCESS", "rtt_ms": round(rtt, 2), "output": res.stdout.strip()[:100]}
        else:
            return {"status": "FAIL", "rtt_ms": round(rtt, 2), "error": res.stderr.strip()[:100]}
    except FileNotFoundError:
        return {"status": "SKIPPED", "rtt_ms": None, "error": "kdeconnect-cli not found on executing host"}
    except Exception as e:
        return {"status": "TIMEOUT", "rtt_ms": None, "error": str(e)}

def execute_randomized_trips(iterations=4):
    results = []
    # Force at least one KDE Connect and one SSH attempt to ensure diverse training data
    targets = [n for n in NODES if n["type"] == "kdeconnect"][:1] + [n for n in NODES if n["type"] == "ssh"][:1]
    targets += random.choices(NODES, k=iterations - 2)
    random.shuffle(targets)

    for target in targets:
        print(f"[{datetime.now().isoformat()}] Tripping {target['name']} via {target['type']}...")
        if target["type"] == "ssh":
            res = run_ssh_round_trip(target["ip"])
        else:
            res = run_kdeconnect_round_trip()
        
        trip = {"target": target["name"], "transport": target["type"], "result": res}
        results.append(trip)
        time.sleep(random.uniform(0.3, 0.8))
        
    return results

def append_to_lora_lake(trips):
    instruction = "Evaluate the randomized cross-device communication mesh utilizing SSH and KDE Connect protocols. Analyze transport latency, identify offline edges, and recommend topology routing optimizations or fallback layers."
    input_data = json.dumps({"timestamp": datetime.now().isoformat(), "round_trips": trips}, separators=(',', ':'))
    
    failed = [t["target"] for t in trips if t["result"]["status"] not in ["SUCCESS", "SKIPPED"]]
    
    if not failed:
        output = "Cross-device telemetry confirms nominal mesh connectivity. SSH and KDE Connect round trips executed successfully. Maintain current dynamic routing paths."
    else:
        output = f"MESH DEGRADATION DETECTED: Transports to {', '.join(set(failed))} failed or timed out. RECOMMENDATION: Execute exhaustive mesh IP matrix exhaustion protocol (TB4 -> Nebula -> Tailscale -> Wi-Fi -> BT PAN). If unresolved, pivot to Layer 0 Bluetooth PAN bridging."
        
    pair = {"instruction": instruction, "input": input_data, "output": output}
    
    os.makedirs(os.path.dirname(LORA_LAKE), exist_ok=True)
    with open(LORA_LAKE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(pair) + '\n')
    print(f"[{datetime.now().isoformat()}] Appended randomized cross-device training trips to LoRA Data Lake.")

if __name__ == "__main__":
    print(f"[{datetime.now().isoformat()}] Starting Lens Cross-Device Randomized Training Loop...")
    trips = execute_randomized_trips(iterations=5)
    append_to_lora_lake(trips)
