#!/usr/bin/env python3
"""
Test Universal Pipeline Sharding (llama.cpp)
Ensures compliance with Rule 8 (Pre-Flight Network Telemetry & Gate).
Tests Pipeline Parallelism across all available nodes.
"""

import subprocess
import sys
import argparse

def check_rpc_endpoint(ip: str, port: int = 50052, timeout: int = 1) -> bool:
    """Mandatory Pre-Flight Gate check as per Rule 8."""
    try:
        result = subprocess.run(
            ["nc", "-zv", "-w", str(timeout), ip, str(port)],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def main():
    parser = argparse.ArgumentParser(description="Universal Pipeline Sharding Test (llama.cpp)")
    parser.add_argument("--model", type=str, default="Hermes-3-Llama-3.1-8B.Q4_K_M.gguf", help="Model to shard")
    args = parser.parse_args()

    # Hardware IP Matrix across L1 to L8 based on Rule 0
    node_ips = {
        "L1": "127.0.0.1",                  # Localhost
        "L1b": "169.254.122.75",            # TB4 IP
        "L2": "100.103.212.21",             # Tailscale / Mac Intel
        "L3": "100.101.39.98",              # Tailscale / Linux Head Node
        "L5": "100.93.158.96",              # Tailscale / Mac Air M4
        "L6": "100.73.38.87",               # Tailscale / Pixel 10 Pro XL
        "L7": "100.78.206.96",               # Tailscale / Galaxy S20
        "L8": "169.254.105.129",            # TB4 placeholder for L8 / lauburu
    }

    active_endpoints = []
    
    print("Executing Mandatory Pre-Flight Network Gate (Rule 8)...")
    for node, ip in node_ips.items():
        if check_rpc_endpoint(ip):
            print(f"[OK] Node {node} ({ip}:50052)")
            active_endpoints.append(f"{ip}:50052")
        else:
            print(f"[FAIL] Node {node} ({ip}:50052) - Unreachable")

    if not active_endpoints:
        print("No remote endpoints passed the pre-flight gate. Aborting sharding.")
        sys.exit(1)
        
    rpc_servers = ",".join(active_endpoints)
    print(f"\nTriggering llama-server Pipeline Parallelism (PP) with endpoints:\n{rpc_servers}")
    
    cmd = [
        "llama-server",
        "-m", args.model,
        "--rpc", rpc_servers,
        "-c", "4096",
        "--port", "8090"
    ]
    
    print(f"\nCommand:\n{' '.join(cmd)}")
    
    print("\n[Execution] Starting PP Sharding. Press Ctrl+C to stop.")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nllama-server stopped.")
    
if __name__ == "__main__":
    main()
