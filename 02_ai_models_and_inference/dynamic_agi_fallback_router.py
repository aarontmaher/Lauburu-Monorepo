#!/usr/bin/env python3
"""
Dynamic AGI Fallback Router & Autonomous Mesh Repair Engine
Executes Rule #0 and dynamic VRAM routing across the 7-layer Lauburu Mesh.
When nodes drop, it downshifts to device-specific survival models to repair the network,
then upshifts back to the Kimi 88B Tandem titan when full mesh is restored.
"""
import os
import json
import time
import subprocess
from pathlib import Path

# Global Mesh State
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
MESH_STATUS_FILE = MONOREPO_ROOT / "data/network/nomad_self_healer_status.json"
ROUTING_CONFIG_FILE = MONOREPO_ROOT / "02_ai_models_and_inference/active_model_routing.json"

# -----------------------------------------------------------------------------
# Survival Model Matrix (Device-Specific Maximal Capabilities)
# -----------------------------------------------------------------------------
FALLBACK_MATRIX = {
    "Mac_Node": {
        "max_repair_model": "Qwen-3.8-Max-27B-GGUF",
        "smallest_rag_model": "Phi-3-mini-4k-instruct-q4",
        "primary_role": "Master Orchestrator Recovery"
    },
    "MacBook_Pro": {
        "max_repair_model": "Llama-3-8B-Instruct-Q8",
        "smallest_rag_model": "Phi-3-mini-4k-instruct-q4",
        "primary_role": "TB4 DMA Bridge Repair"
    },
    "Linux_Head_Node": {
        "max_repair_model": "Mistral-7B-Instruct-v0.3-Q4_K_M",
        "smallest_rag_model": "TinyLlama-1.1B-Chat-v1.0",
        "primary_role": "Docker/Gateway Ingress Repair"
    },
    "Pixel_10_Pro_XL": {
        "max_repair_model": "Gemma-2-9B-It-Q4_K_M (Edge TPU)",
        "smallest_rag_model": "Gemma-2-2B-It",
        "primary_role": "Cellular UWB Routing Repair"
    }
}

# -----------------------------------------------------------------------------
# Global Titan Model (Requires Full Mesh)
# -----------------------------------------------------------------------------
TITAN_MODEL = "Kimi-88B-Tandem-IQ3_S"

def check_mesh_health() -> float:
    """
    Returns a health percentage (0.0 to 1.0) of the full 7-layer mesh.
    """
    try:
        if not MESH_STATUS_FILE.exists():
            return 0.0
            
        with open(MESH_STATUS_FILE, "r") as f:
            status = json.load(f)
            
        # Simplified evaluation of active nodes from Tailscale ping/RPC checks
        active_nodes = 0
        total_nodes = 4 # Counting primary compute nodes for this check
        
        rpc_matrix = status.get("llama_rpc_port_50052", {}).get("endpoint_matrix", {})
        for node, data in rpc_matrix.items():
            if data.get("status") == "ACTIVE":
                active_nodes += 1
                
        return min(active_nodes / total_nodes, 1.0)
    except Exception as e:
        print(f"Error reading mesh health: {e}")
        return 0.0

def trigger_mesh_repair(local_node: str):
    """
    Invokes the Nomad Courier to attempt a physical/logical connection rebuild.
    """
    print(f"[{local_node}] ⚠️ Mesh degraded. Triggering Nomad Courier repair protocols...")
    repair_script = MONOREPO_ROOT / "06_scripts_and_tooling/network/nomad_courier_self_healer.py"
    if repair_script.exists():
        subprocess.Popen(["python3", str(repair_script), "--once"])

def evaluate_and_route():
    """
    Evaluates mesh health and shifts the active inference routing config.
    """
    health = check_mesh_health()
    local_node = os.environ.get("LAUBURU_NODE_ID", "Mac_Node")
    
    current_routing = {
        "timestamp": time.time(),
        "mesh_health": health,
        "active_model": "",
        "fallback_engaged": False,
        "repair_target": "None"
    }
    
    if health >= 0.99:
        print("🟢 Full Mesh Confirmed. Upshifting to Titan AGI.")
        current_routing["active_model"] = TITAN_MODEL
        current_routing["fallback_engaged"] = False
    else:
        print(f"🔴 Mesh Degraded (Health: {health*100}%). Downshifting to Survival Mode.")
        node_capabilities = FALLBACK_MATRIX.get(local_node, FALLBACK_MATRIX["Mac_Node"])
        
        # Deploy the maximum capable device-specific model to lead the repair
        current_routing["active_model"] = node_capabilities["max_repair_model"]
        current_routing["smallest_rag_fallback"] = node_capabilities["smallest_rag_model"]
        current_routing["fallback_engaged"] = True
        current_routing["repair_target"] = node_capabilities["primary_role"]
        
        # Automatically fire the repair daemon
        trigger_mesh_repair(local_node)
        
    print(f"Active Model Configured: {current_routing['active_model']}")
    
    ROUTING_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ROUTING_CONFIG_FILE, "w") as f:
        json.dump(current_routing, f, indent=2)

if __name__ == "__main__":
    evaluate_and_route()
