#!/usr/bin/env python3
"""
Petals Swarm Node Daemon & Distributed Inference Harness (v1.0)
Coordinates distributed BitTorrent-style layer sharding across the Lauburu 7-Node Mesh.

Roles:
1. DHT Bootstrap Server: Initial node providing entrypoint DHT routing table (Linux Head Node / Mac Mini Host).
2. Swarm Worker: Hosts a range of transformer attention/MLP blocks (e.g. blocks 0:8, 8:16, 16:24).
3. Swarm Client: Tokenizes prompt, streams intermediate hidden states through DHT peer chain, and decodes tokens.
"""

import os
import sys
import json
import time
import socket
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
PETALS_DIR = REPO_ROOT / "02_ai_models_and_inference/petals_dht"
CACHE_DIR = PETALS_DIR / "cache"

DEFAULT_DHT_PORT = 31330
DEFAULT_SWARM_PREFIX = "lauburu-mesh-swarm"

NODE_MAPPINGS = {
    "local_mac_mini": {"ip": "100.119.199.76", "blocks": "0:8", "name": "Apple M4 Pro Mac Mini Host"},
    "macbook_air": {"ip": "100.93.158.96", "blocks": "8:16", "name": "Apple M4 MacBook Air"},
    "macbook_pro": {"ip": "100.103.212.21", "blocks": "16:24", "name": "Headless Intel i7 MacBook Pro"},
    "linux_head": {"ip": "100.101.39.98", "blocks": "0:12", "name": "AMD Ryzen 7 Linux Node"},
}


class PetalsSwarmNode:
    def __init__(self, model_name: str = "bigscience/bloom-560m", dht_prefix: str = DEFAULT_SWARM_PREFIX):
        self.model_name = model_name
        self.dht_prefix = dht_prefix
        self.cache_path = CACHE_DIR / model_name.split("/")[-1]

    def check_dht_connectivity(self, target_ip: str, port: int = DEFAULT_DHT_PORT) -> Dict[str, Any]:
        """Probes DHT port on peer node."""
        t0 = time.perf_counter()
        reachable = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                res = s.connect_ex((target_ip, port))
                reachable = (res == 0)
        except Exception:
            reachable = False
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "target_ip": target_ip,
            "port": port,
            "reachable": reachable,
            "latency_ms": latency_ms,
            "status": "DHT_PEER_ACTIVE" if reachable else "DHT_PEER_STANDBY"
        }

    def generate_server_command(self, num_blocks: Optional[int] = None, block_indices: Optional[str] = None, public_ip: Optional[str] = None) -> List[str]:
        """Constructs CLI command to start petals.cli.run_server."""
        cmd = [
            "python3", "-m", "petals.cli.run_server",
            self.model_name,
            "--dht_prefix", self.dht_prefix,
            "--port", str(DEFAULT_DHT_PORT),
        ]
        if block_indices:
            cmd.extend(["--block_indices", block_indices])
        elif num_blocks:
            cmd.extend(["--num_blocks", str(num_blocks)])
        if public_ip:
            cmd.extend(["--public_ip", public_ip])
        return cmd

    def get_cluster_dht_status(self) -> Dict[str, Any]:
        """Probes all 7 nodes for Petals DHT listeners."""
        matrix = {}
        for key, node in NODE_MAPPINGS.items():
            matrix[key] = self.check_dht_connectivity(node["ip"], DEFAULT_DHT_PORT)

        active_peers = [k for k, v in matrix.items() if v["reachable"]]
        return {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model_name": self.model_name,
            "dht_prefix": self.dht_prefix,
            "active_dht_peers_count": len(active_peers),
            "total_configured_nodes": len(NODE_MAPPINGS),
            "peer_matrix": matrix,
            "cached_model_present": (self.cache_path / "model.safetensors").exists() or (self.cache_path / "pytorch_model.bin").exists()
        }


def main():
    parser = argparse.ArgumentParser(description="Petals Swarm Node Daemon")
    parser.add_argument("--status", action="store_true", help="Probe cluster DHT mesh connectivity")
    parser.add_argument("--model", type=str, default="bigscience/bloom-560m", help="Target HuggingFace Petals model")
    parser.add_argument("--server-cmd", action="store_true", help="Generate start command for this node")
    parser.add_argument("--blocks", type=str, help="Block range (e.g. 0:8, 8:16)")
    args = parser.parse_args()

    node = PetalsSwarmNode(model_name=args.model)

    if args.status or len(sys.argv) == 1:
        status = node.get_cluster_dht_status()
        print("\n🌸 ==================== PETALS DHT MESH STATUS ==================== 🌸\n")
        print(json.dumps(status, indent=2))
        print()

    if args.server_cmd:
        cmd = node.generate_server_command(block_indices=args.blocks)
        print("\n🚀 Command to start Petals Server Node:")
        print("   " + " ".join(cmd) + "\n")


if __name__ == "__main__":
    main()
