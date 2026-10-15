#!/usr/bin/env python3
"""
Autonomous Netmon LoRA Distillation Loop
Executes ~/.local/bin/netmon --once --json and formats the mesh telemetry
into an Instruction/Input/Output pair for continuous QLoRA training.
Appends directly to the PySpark LoRA Data Lake.
"""

import json
import os
import subprocess
import time
from datetime import datetime

NETMON_PATH = os.path.expanduser("~/.local/bin/netmon")
LORA_DATASET_PATH = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl"

def harvest_telemetry():
    print(f"[{datetime.now().isoformat()}] Executing Netmon...")
    try:
        result = subprocess.run([NETMON_PATH, "--once", "--json"], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error executing netmon: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print("Error: Could not parse netmon JSON output.")
        return None

def format_lora_pair(telemetry_data):
    # Construct an instruction tailored to mesh health
    instruction = "Analyze the following sovereign mesh network telemetry. Identify offline nodes, degraded connections, and low storage headroom. Recommend self-healing actions if necessary."
    
    # Input is the raw telemetry JSON
    input_text = json.dumps(telemetry_data, separators=(',', ':'))
    
    # Generate a simple synthetic output based on the telemetry (in reality, a teacher model would evaluate this)
    # For distillation, we record the baseline healthy/unhealthy states.
    offline_nodes = [n["name"] for n in telemetry_data.get("nodes", []) if not n.get("online", False)]
    offline_daemons = [p["name"] for p in telemetry_data.get("services", []) if p.get("status") != "UP"]
    low_storage = [s["label"] for s in telemetry_data.get("storage", []) if not s.get("healthy", True)]

    output_parts = []
    if not offline_nodes and not offline_daemons and not low_storage:
        output_parts.append("All mesh nodes and daemons are fully operational and healthy. Storage headroom is nominal.")
    else:
        if offline_nodes:
            output_parts.append(f"CRITICAL: The following nodes are offline: {', '.join(offline_nodes)}.")
            output_parts.append("SELF-HEALING RECOMMENDATION: Evaluate offline detection against live recovery triggers. Execute multi-transport Ping Matrix exhaustion (TB4 -> Nebula -> Tailscale -> Wi-Fi -> BT PAN -> GoodCloud OOB). If unresolved, dispatch WoL magic packets or `rfcomm` restart via fallback layer.")
        if offline_daemons:
            output_parts.append(f"WARNING: The following services/daemons are down: {', '.join(offline_daemons)}.")
            output_parts.append("SELF-HEALING RECOMMENDATION: Trigger `systemctl restart` for failed services on the host machine and verify port bindings.")
        if low_storage:
            output_parts.append(f"STORAGE ALERT: Low headroom on: {', '.join(low_storage)}.")
            output_parts.append("SELF-HEALING RECOMMENDATION: Trigger automated log rotation, clear `~/.cache/huggingface/hub`, and offload Parquet partitions to SeaweedFS.")
    
    output_text = " ".join(output_parts)
    
    return {
        "instruction": instruction,
        "input": input_text,
        "output": output_text
    }

def append_to_lake(lora_pair):
    os.makedirs(os.path.dirname(LORA_DATASET_PATH), exist_ok=True)
    with open(LORA_DATASET_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(lora_pair) + '\n')
    print(f"[{datetime.now().isoformat()}] Successfully appended telemetry LoRA pair to Data Lake.")

def main():
    print(f"[{datetime.now().isoformat()}] Starting Netmon LoRA Distillation (One-Shot)...")
    data = harvest_telemetry()
    if data:
        pair = format_lora_pair(data)
        append_to_lake(pair)

if __name__ == "__main__":
    main()
