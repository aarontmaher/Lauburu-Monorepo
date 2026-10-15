import json
import hashlib
import time

def hash_entry(entry):
    s = json.dumps(entry, sort_keys=True).encode('utf-8')
    return hashlib.sha256(s).hexdigest()

def append_to_dataset():
    instruction = "Synthesize distributed sharding and load balancing architecture across 7 mesh layers, factoring in hardware constraints, containerization overhead (Docker/Podman/K8s), and IDE/Web terminal deployments."
    input_data = "[System Probe]: Hardware totals: 147 GB RAM, 100 GB VRAM. TB4 provides <0.5ms latency. Tailscale: 3-90ms. Docker overhead: 0.5ms."
    output_data = "For optimal AI sharding: 1. Deploy real-time pipeline models over TB4 (L1, L1b, L2, L8) avoiding Wi-Fi due to socket buffer deadlock. 2. Use Tailscale/Wireguard strictly for asynchronous batch processing (Petals) to edge Android nodes (L4, L6, L7). 3. Host centralized IntelliJ IDE/MCP on L8 Linux Hub to preserve L1 memory (Sanctuary Rule). 4. Use Docker on L8, and Podman rootless on edges."
    
    entry = {
        "instruction": instruction,
        "input": input_data,
        "output": output_data,
        "timestamp": int(time.time())
    }
    
    entry["sha256"] = hash_entry(entry)
    
    dataset_path = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl"
    with open(dataset_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
        
    print(f"Appended to {dataset_path}")
    print(f"SHA256: {entry['sha256']}")

if __name__ == "__main__":
    append_to_dataset()
