import json
import subprocess
from datetime import datetime

def harvest():
    # 1. Harvest Mac Mini RAM
    try:
        import psutil
        mem = psutil.virtual_memory()
        ram_state = f"Available: {mem.available / (1024**3):.2f} GB"
    except Exception as e:
        ram_state = str(e)

    # 2. Router status (mock ping as fallback if SSH fails, but we should use real syscall)
    try:
        res = subprocess.run(["ping", "-c", "1", "100.90.8.1"], capture_output=True, text=True, timeout=2)
        router_status = "ONLINE" if res.returncode == 0 else "OFFLINE"
    except Exception:
        router_status = "ERROR"

    # Construct LoRA instruction
    record = {
        "instruction": "Analyze current mesh topology health.",
        "input": f"Mac Mini Host RAM: {ram_state}\\nRouter Gateway: {router_status}",
        "output": f"Host is {'healthy' if 'Available' in ram_state else 'degraded'}. Network is {router_status}.",
        "timestamp": datetime.now().isoformat()
    }

    # Append to dataset
    dataset_path = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl"
    with open(dataset_path, "a") as f:
        f.write(json.dumps(record) + "\\n")
    print("Harvested and appended telemetry successfully.")

if __name__ == "__main__":
    harvest()
