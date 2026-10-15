import time
import json
import subprocess
import os
from datetime import datetime

LORA_DATASET_PATH = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl"
OS_POLL_INTERVAL = 300  # 5 minutes

def execute_remote(cmd):
    try:
        # We target the Pixel 10 natively via Termux
        full_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "-p", "8022", "u0_a245@100.73.38.87", cmd]
        result = subprocess.run(full_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

def harvest_shizuku_state():
    # Check if Shizuku UID 2000 is active via rish and Phantom Processes are disabled
    out = execute_remote("echo 'RISH_CHECK'; ~/bin/rish -c 'id' 2>&1 || echo 'RISH_DEAD'")
    phantom = execute_remote("settings get global settings_enable_monitor_phantom_procs 2>/dev/null || echo 'UNKNOWN'")
    return out, phantom

def append_to_lora(instruction, input_context, output_response):
    os.makedirs(os.path.dirname(LORA_DATASET_PATH), exist_ok=True)
    entry = {
        "text": f"<s>[INST] {instruction}\n\nContext:\n{input_context} [/INST] {output_response} </s>",
        "timestamp": datetime.now().isoformat()
    }
    with open(LORA_DATASET_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{datetime.now().isoformat()}] Appended LoRA trace: {instruction}")

def main_loop():
    print("🚀 Booting Lens Hardware LoRA Harvester (Rule 12 & Rule 9)")
    while True:
        shizuku_id, phantom_state = harvest_shizuku_state()
        
        if shizuku_id and phantom_state:
            instruction = "Analyze the Android Edge Node Shizuku Binder IPC state and Phantom Process Killer status to verify autonomous persistence."
            input_context = f"Telemetry Node: L6_Pixel_10\nNetwork Layer: Termux SSH / Wireless ADB\nShizuku Binder ID: {shizuku_id}\nPhantom Process Setting: {phantom_state}"
            
            if "uid=2000" in str(shizuku_id) and "false" in str(phantom_state):
                output = "The edge node is fully resilient. Shizuku is actively bridged into Termux (UID 2000 shell), and Android phantom process killers are strictly disabled. The node is ready for Screen Lens VLA 24/7 automation."
            else:
                output = "The edge node is severely degraded. Shizuku is either dead or Phantom Process Killers are enabled. Immediate self-healing required: Execute `~/bin/rish -c 'settings put global settings_enable_monitor_phantom_procs false'` and verify Wireless ADB pairing."
            
            append_to_lora(instruction, input_context, output)
            
        time.sleep(OS_POLL_INTERVAL)

if __name__ == "__main__":
    main_loop()
