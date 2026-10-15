#!/usr/bin/env python3
"""
================================================================================
Universal Mesh Workload Offload Router
================================================================================
Subsystem: 06_scripts_and_tooling / mesh
Enforces Canonical Rule #3: Dynamic RAM & Compute Governance.
Automatically offloads heavy compute, MLX LoRA training, AI testing, and
background subagents from the L1 Host Mac Mini to the L5 MacBook Air M4
or L3 Linux Head Node.
================================================================================
"""

import os
import sys
import time
import json
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

NODE_REGISTRY = {
    "air": {
        "name": "MacBook_Air_M4",
        "alias": "macbook-air",
        "ip": "100.93.158.96",
        "lan_ip": "192.168.8.222",
        "user": "aaronmaher",
        "ram_gb": 16.0,
        "ai_cap_gb": 14.0,
        "roles": ["MLX LoRA Distillation", "Metal GPU Worker", "Subagent Execution"],
        "default_env": "export PATH=\"/opt/homebrew/bin:$HOME/bin:$HOME/.local/bin:$PATH\";"
    },
    "mbp": {
        "name": "MacBook_Pro_TB4",
        "alias": "macbook-pro",
        "ip": "100.103.212.21",
        "tb4_ip": "169.254.187.138",
        "user": "aaronmaher",
        "ram_gb": 16.0,
        "ai_cap_gb": 14.0,
        "roles": ["Model Vault", "Metal RPC Sharding"],
        "default_env": "export PATH=\"/opt/homebrew/bin:$HOME/bin:$PATH\";"
    },
    "linux": {
        "name": "Linux_Head_Node",
        "alias": "linux",
        "ip": "100.101.39.98",
        "lan_ip": "192.168.8.224",
        "user": "linux",
        "ram_gb": 16.0,
        "ai_cap_gb": 12.8,
        "roles": ["Docker Hub", "Petals DHT", "Ray Compute"],
        "default_env": "export PATH=\"/usr/local/bin:$HOME/bin:$PATH\";"
    },
    "pixel": {
        "name": "Pixel_10_Pro_XL",
        "alias": "pixel",
        "ip": "100.73.38.87",
        "user": "u0_a363",
        "port": 8022,
        "ram_gb": 16.0,
        "ai_cap_gb": 13.6,
        "roles": ["Tensor G5 Edge TPU", "Vision OCR", "Speculative Drafting"],
        "default_env": "export PATH=\"$HOME/google-cloud-sdk/bin:$PREFIX/bin:$HOME/bin:$PATH\";"
    }
}


class WorkloadOffloadRouter:
    """Orchestrates transparent workload execution on peripheral mesh nodes."""

    def __init__(self, target_node: str = "air"):
        if target_node not in NODE_REGISTRY:
            raise ValueError(f"Unknown target node: {target_node}. Options: {list(NODE_REGISTRY.keys())}")
        self.node_id = target_node
        self.node_info = NODE_REGISTRY[target_node]

    def check_node_health(self) -> Dict[str, Any]:
        """Verify SSH reachability and check load."""
        alias = self.node_info["alias"]
        try:
            cmd = ["ssh", "-o", "ConnectTimeout=3", alias, "uptime"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return {
                    "status": "ONLINE",
                    "uptime": res.stdout.strip(),
                    "node": self.node_info["name"]
                }
        except Exception as e:
            return {"status": "UNREACHABLE", "error": str(e)}
        return {"status": "OFFLINE"}

    def run_remote(self, command: str, cwd: Optional[str] = None, sync_first: bool = False) -> int:
        """Executes a command on the remote target node with environment setup."""
        alias = self.node_info["alias"]
        env_prefix = self.node_info["default_env"]
        
        remote_cwd = cwd or "~/Lauburu-Monorepo"
        full_remote_cmd = f"{env_prefix} cd {remote_cwd} 2>/dev/null || true; {command}"

        print("=" * 80)
        print(f"🚀 [MESH OFFLOAD] Dispatching Workload to -> {self.node_info['name']} ({self.node_info['ip']})")
        print(f"📌 Roles   : {', '.join(self.node_info['roles'])}")
        print(f"⚙️ Command : {command}")
        print("=" * 80)

        ssh_cmd = ["ssh", "-o", "ConnectTimeout=4", alias, full_remote_cmd]
        
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(ssh_cmd, text=True)
            elapsed = time.perf_counter() - t0
            print("-" * 80)
            print(f"✅ Remote Execution Completed on {self.node_info['name']} in {elapsed:.2f}s (Exit Code: {proc.returncode})")
            print("=" * 80)
            return proc.returncode
        except KeyboardInterrupt:
            print("\nExecution canceled by user.")
            return 130
        except Exception as e:
            print(f"❌ Remote execution failed: {e}")
            return 1


def main():
    parser = argparse.ArgumentParser(description="Universal Mesh Workload Offload Router")
    parser.add_argument("--node", "-n", type=str, default="air", choices=["air", "mbp", "linux", "pixel"],
                        help="Target node for execution (default: air -> MacBook Air M4)")
    parser.add_argument("--check", action="store_true", help="Check target node health")
    parser.add_argument("command", nargs="*", help="Command to execute on remote node")
    
    args = parser.parse_args()
    
    router = WorkloadOffloadRouter(target_node=args.node)
    
    if args.check:
        health = router.check_node_health()
        print(json.dumps(health, indent=2))
        return 0 if health["status"] == "ONLINE" else 1

    if not args.command:
        # Default status sweep
        print("🌐 Active Mesh Offload Node Targets:")
        for nid, info in NODE_REGISTRY.items():
            r = WorkloadOffloadRouter(target_node=nid)
            h = r.check_node_health()
            status_sym = "🟢" if h["status"] == "ONLINE" else "🔴"
            print(f"  {status_sym} --node {nid:<6} -> {info['name']:<20} ({info['ip']}) | {info['ai_cap_gb']}GB AI Cap")
        print("\nUsage example:")
        print("  python3 06_scripts_and_tooling/mesh/workload_offload_router.py --node air 'python3 -c \"import mlx.core as mx; print(mx.array([1, 2, 3]))\"'")
        return 0

    cmd_str = " ".join(args.command)
    return router.run_remote(cmd_str)


if __name__ == "__main__":
    sys.exit(main())
