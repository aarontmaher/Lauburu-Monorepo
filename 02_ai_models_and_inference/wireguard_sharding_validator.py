import subprocess
import json
from datetime import datetime, timezone

TARGET_IP = "10.1.0.12" # L3 Linux Hub WireGuard IP
NODE_NAME = "L3 Linux Hub"

def get_ping_rtt(ip):
    try:
        output = subprocess.check_output(f"ping -c 3 -W 1000 {ip}", shell=True).decode()
        for line in output.split('\n'):
            if "min/avg/max/stddev" in line or "min/avg/max/mdev" in line:
                avg = float(line.split('=')[1].split('/')[1])
                return avg
    except:
        pass
    return None

def main():
    rtt = get_ping_rtt(TARGET_IP)
    if rtt is None:
        print(f"FAILED to ping {TARGET_IP}")
        return
        
    print(f"WireGuard Ping to {TARGET_IP} ({NODE_NAME}) RTT: {rtt} ms")
    
    if rtt > 1.0:
        decision = "FALLBACK_TO_LLAMACPP_PP"
        reason = f"RTT {rtt}ms exceeds 1.0ms Hard Gate (Rule 8). Tensor Parallelism (prima.cpp) PROHIBITED."
    else:
        decision = "ENABLE_PRIMACPP_TP"
        reason = f"RTT {rtt}ms is within 1.0ms Hard Gate (Rule 8)."

    print(f"Orchestrator Decision: {decision}")
    print(f"Reasoning: {reason}")
    
    # Save to continuous_lora_dataset
    lora_pair = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "instruction": f"Evaluate tensor sharding protocol over WireGuard to {NODE_NAME} (IP: {TARGET_IP}).",
        "input": f"Empirical Ping RTT: {rtt} ms",
        "output": f"Validation complete. {reason} Fallback protocol engaged: {decision} over WireGuard overlay."
    }
    
    with open("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl", "a") as f:
        f.write(json.dumps(lora_pair) + "\n")
        
    print("Recorded to continuous_lora_dataset.jsonl")

if __name__ == "__main__":
    main()
