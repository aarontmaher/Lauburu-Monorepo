import psutil
import time
import requests
import sys

# 06_scripts_and_tooling/ai/kv_cache_pager.py
# Implements Transparent Memory Paging over Thunderbolt 4.

L1_SANCTUARY_LIMIT_GB = 4.8
TOTAL_UNIFIED_RAM_GB = 24.0
TB4_PEER_IP = "169.254.122.75" # MacBook Pro L2
RPC_PORT = 50052

def get_free_memory_gb():
    mem = psutil.virtual_memory()
    return mem.available / (1024 ** 3)

def trigger_kv_page_out():
    print(f"Sanctuary limit breached! Paging KV-cache over TB4 to {TB4_PEER_IP}...")
    try:
        # Instruct prima.cpp or llama-server to offload KV to the remote RPC worker
        res = requests.post(f"http://127.0.0.1:8082/api/v1/page_out", json={
            "target_rpc": f"{TB4_PEER_IP}:{RPC_PORT}",
            "bytes": 2 * 1024 * 1024 * 1024 # Evict 2GB of context
        }, timeout=2.0)
        print("Paging successful:", res.status_code)
    except Exception as e:
        print("Paging failed:", e)

def monitor_loop():
    print("Starting Transparent KV-Cache Paging Monitor...")
    while True:
        free_gb = get_free_memory_gb()
        if free_gb < L1_SANCTUARY_LIMIT_GB:
            trigger_kv_page_out()
            time.sleep(30) # Cool-down
        time.sleep(2)

if __name__ == "__main__":
    monitor_loop()
