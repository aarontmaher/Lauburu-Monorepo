import subprocess
import json
import os
from pathlib import Path

LORA_FILE = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl")

def fetch_and_drain_kv():
    try:
        # List all keys
        res = subprocess.run(["npx", "wrangler", "kv", "key", "list", "--binding", "LORA_SYNTHESIS_QUEUE"],
                            capture_output=True, text=True, cwd="/Volumes/Lauburu-Monorepo/01_apps/lora_synthesizer_worker")
        if res.returncode != 0:
            print("Failed to list KV:", res.stderr)
            return

        keys = json.loads(res.stdout)
        if not keys:
            print("No new LoRA pairs found.")
            return

        print(f"Found {len(keys)} new LoRA pairs. Downloading...")
        
        with open(LORA_FILE, "a") as f:
            for item in keys:
                key_name = item["name"]
                val_res = subprocess.run(["npx", "wrangler", "kv", "key", "get", key_name, "--binding", "LORA_SYNTHESIS_QUEUE"],
                                      capture_output=True, text=True, cwd="/Volumes/Lauburu-Monorepo/01_apps/lora_synthesizer_worker")
                if val_res.returncode == 0:
                    val = val_res.stdout.strip()
                    if val:
                        f.write(val + "\n")
                    
                    # Delete after reading
                    subprocess.run(["npx", "wrangler", "kv", "key", "delete", key_name, "--binding", "LORA_SYNTHESIS_QUEUE"],
                                cwd="/Volumes/Lauburu-Monorepo/01_apps/lora_synthesizer_worker")
        
        print(f"Successfully drained {len(keys)} pairs to {LORA_FILE}")

    except Exception as e:
        print("Error pulling KV:", e)

if __name__ == "__main__":
    fetch_and_drain_kv()
