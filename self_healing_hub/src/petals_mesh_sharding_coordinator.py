#!/usr/bin/env python3
"""
Petals & llama.cpp RPC Multi-Device Mesh Sharding Coordinator
=============================================================
Orchestrates decentralized layer-sharded model distribution across the
7-Device Unified Hardware Mesh (82.8 GB Total Pooled AI VRAM):

  - Layer 1: Mac Host Coordinator (M4 Mac Mini / Max - Ingestion & Memory Governor)
  - Layer 2: MacBook Pro Vault (Intel i7 / 285 GB SSD Model Vault / Metal GPU)
  - Layer 3: Linux Head Node (AMD Ryzen 7 5700U - DHT Swarm Bootstrap Hub)
  - Layer 4: Linux Tablet (Debian - Mobile Linux Compute & Secondary Sharding)
  - Layer 5: Mac Mini Metal Compute (Mac Mini M2/M4 - High-Speed Metal Shaders)
  - Layer 6: Pixel 10 Pro XL (Google Tensor G5 + TPU - Vision Stream & Edge Shard)
  - Layer 7: Samsung Galaxy S20+ (Snapdragon 865 - Dedicated UI Tester & Token Sampler)

Provides programmatic layer partitioning, Petals CLI startup command generation
for macOS MPS, Linux CPU, and Android Termux ARM64, llama-server RPC tensor splits,
and canonical storage compliance under /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/.
"""

import os
import sys
import json
import shlex
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [PETALS-COORDINATOR] %(levelname)s - %(message)s"
)
logger = logging.getLogger("PetalsMeshShardingCoordinator")

# Canonical Path Constants (Requirement R4)
CANONICAL_WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
CANONICAL_DATA_DIR = CANONICAL_WORKSPACE_ROOT / "data"

# Real Local Filesystem Resolution
_POSSIBLE_ROOTS = [
    Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"),
    Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"),
    Path(__file__).resolve().parents[2]
]
LOCAL_WORKSPACE_ROOT = next((p for p in _POSSIBLE_ROOTS if p.exists()), _POSSIBLE_ROOTS[0])
LOCAL_DATA_DIR = LOCAL_WORKSPACE_ROOT / "data"
LOCAL_SHARDING_DIR = LOCAL_DATA_DIR / "petals_sharding_plans"

# Network & DHT Defaults
DEFAULT_DHT_PREFIX = "lauburu-petals-mesh-v1"
DEFAULT_BOOTSTRAP_IP = "100.101.39.98"
DEFAULT_BOOTSTRAP_PORT = 31337
DEFAULT_BOOTSTRAP_PEER = f"/ip4/{DEFAULT_BOOTSTRAP_IP}/tcp/{DEFAULT_BOOTSTRAP_PORT}/p2p/QmLauburuLinuxHeadNodeDHTBootstrap"
DEFAULT_RPC_PORT = 50052

# 7-Device Mesh Layer Specifications (82.8 GB Total Pooled AI VRAM)
MESH_7_DEVICE_LAYERS: Dict[str, Dict[str, Any]] = {
    "layer_1_mac_host": {
        "layer": 1,
        "node_id": "Mac_Node",
        "name": "Apple M4 Pro Mac Mini Host Coordinator",
        "platform": "macos",
        "os": "Darwin",
        "arch": "arm64",
        "device_type": "mps",
        "python_cmd": "python3",
        "ram_total_gb": 24.0,
        "usable_vram_gb": 13.5,
        "tailscale_ip": "100.119.199.76",
        "lan_ip": "127.0.0.1",
        "port": 31338,
        "rpc_port": DEFAULT_RPC_PORT,
        "role": "Host Coordinator / Ingestion & Memory Governor",
        "is_master": True,
        "is_bootstrap": False,
        "torch_dtype": "float16",
        "weight": 13.5 / 82.8
    },
    "layer_2_headless_mac": {
        "layer": 2,
        "node_id": "MacBook_Pro",
        "name": "Headless MacBook Pro Vault",
        "platform": "macos",
        "os": "Darwin",
        "arch": "x86_64",
        "device_type": "mps",
        "python_cmd": "python3",
        "ram_total_gb": 16.0,
        "usable_vram_gb": 14.0,
        "tailscale_ip": "100.103.212.21",
        "tb4_ip": "169.254.187.138",
        "port": 31338,
        "rpc_port": DEFAULT_RPC_PORT,
        "role": "Deep Transformer Layers & Model Vault (285 GB SSD)",
        "is_master": False,
        "is_bootstrap": False,
        "torch_dtype": "float16",
        "weight": 14.0 / 82.8
    },
    "layer_3_linux_node": {
        "layer": 3,
        "node_id": "Linux_Head_Node",
        "name": "Linux Head Node (AMD Ryzen 7 5700U)",
        "platform": "linux_x86_64",
        "os": "Linux",
        "arch": "x86_64",
        "device_type": "cpu",
        "python_cmd": "python3",
        "ram_total_gb": 16.0,
        "usable_vram_gb": 13.8,
        "tailscale_ip": "100.101.39.98",
        "lan_ip": "192.168.8.119",
        "port": 31337,
        "rpc_port": DEFAULT_RPC_PORT,
        "role": "Gateway Ingress & DHT Swarm Bootstrap Hub",
        "is_master": False,
        "is_bootstrap": True,
        "torch_dtype": "float16",
        "weight": 13.8 / 82.8
    },
    "layer_4_linux_tablet": {
        "layer": 4,
        "node_id": "Linux_Tablet",
        "name": "Debian Linux Tablet",
        "platform": "linux_x86_64",
        "os": "Linux",
        "arch": "x86_64",
        "device_type": "cpu",
        "python_cmd": "python3",
        "ram_total_gb": 8.0,
        "usable_vram_gb": 6.5,
        "tailscale_ip": "100.81.92.125",
        "lan_ip": "192.168.8.152",
        "port": 31337,
        "rpc_port": DEFAULT_RPC_PORT,
        "role": "Mobile Linux Compute & Secondary Sharding",
        "is_master": False,
        "is_bootstrap": False,
        "torch_dtype": "float32",
        "weight": 6.5 / 82.8
    },
    "layer_5_macbook_air": {
        "layer": 5,
        "node_id": "MacBook_Air",
        "name": "Headless Apple M4 MacBook Air Metal Node",
        "platform": "macos",
        "os": "Darwin",
        "arch": "arm64",
        "device_type": "mps",
        "python_cmd": "python3",
        "ram_total_gb": 16.0,
        "usable_vram_gb": 13.5,
        "tailscale_ip": "100.93.158.96",
        "lan_ip": "192.168.8.222",
        "port": 31338,
        "rpc_port": DEFAULT_RPC_PORT,
        "role": "High-Speed Metal Performance Shaders & Secondary Vault",
        "is_master": False,
        "is_bootstrap": False,
        "torch_dtype": "float16",
        "weight": 13.5 / 82.8
    },
    "layer_6_pixel_10_pro": {
        "layer": 6,
        "node_id": "Pixel_10_Pro_XL",
        "name": "Google Pixel 10 Pro XL",
        "platform": "android_termux",
        "os": "Android",
        "arch": "aarch64",
        "device_type": "cpu",
        "python_cmd": "python",
        "ram_total_gb": 16.0,
        "usable_vram_gb": 12.5,
        "tailscale_ip": "100.73.38.87",
        "lan_ip": "192.168.8.160",
        "ssh_port": 8022,
        "adb_target": "100.73.38.87:5555",
        "port": 31337,
        "rpc_port": DEFAULT_RPC_PORT,
        "forward_rpc_port": 50054,
        "role": "Edge TPU Vision Stream & Secondary RPC Shard",
        "is_master": False,
        "is_bootstrap": False,
        "torch_dtype": "float32",
        "weight": 12.5 / 82.8
    },
    "layer_7_samsung_s20": {
        "layer": 7,
        "node_id": "Samsung_S20",
        "name": "Samsung Galaxy S20+",
        "platform": "android_termux",
        "os": "Android",
        "arch": "aarch64",
        "device_type": "cpu",
        "python_cmd": "python",
        "ram_total_gb": 12.0,
        "usable_vram_gb": 9.0,
        "tailscale_ip": "100.84.40.95",
        "lan_ip": "192.168.8.158",
        "ssh_port": 8022,
        "adb_target": "100.84.40.95:5555",
        "port": 31337,
        "rpc_port": DEFAULT_RPC_PORT,
        "forward_rpc_port": 50055,
        "role": "Dedicated UI Tester & Edge Token Sampler",
        "is_master": False,
        "is_bootstrap": False,
        "torch_dtype": "float32",
        "weight": 9.0 / 82.8
    }
}


class PetalsMeshShardingCoordinator:
    """
    Coordinates Petals decentralized swarm sharding and llama.cpp RPC instance distribution
    across the 7-device hardware mesh.
    """

    def __init__(
        self,
        dht_prefix: str = DEFAULT_DHT_PREFIX,
        bootstrap_peer: Optional[str] = None,
        data_dir: Optional[Union[str, Path]] = None
    ):
        self.dht_prefix = dht_prefix
        self.bootstrap_peer = bootstrap_peer or DEFAULT_BOOTSTRAP_PEER
        self.mesh_layers = MESH_7_DEVICE_LAYERS
        
        # Resolve data directory
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = LOCAL_DATA_DIR
            
        self.sharding_plans_dir = self.data_dir / "petals_sharding_plans"
        try:
            self.sharding_plans_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create sharding plans directory {self.sharding_plans_dir}: {e}")

    def get_mesh_topology(self) -> Dict[str, Any]:
        """Returns the full 7-Device Hardware Mesh topology and pooled AI VRAM capacity."""
        total_pooled_vram = round(sum(n["usable_vram_gb"] for n in self.mesh_layers.values()), 2)
        total_ram = round(sum(n["ram_total_gb"] for n in self.mesh_layers.values()), 2)
        return {
            "mesh_name": "Lauburu 7-Device Unified Hardware Mesh",
            "total_nodes": len(self.mesh_layers),
            "total_pooled_vram_gb": total_pooled_vram,
            "total_ram_gb": total_ram,
            "dht_prefix": self.dht_prefix,
            "bootstrap_node": self.mesh_layers["layer_3_linux_node"]["name"],
            "bootstrap_peer": self.bootstrap_peer,
            "layers": self.mesh_layers
        }

    def shard_model_across_mesh(
        self,
        model_name: str,
        total_layers: int = 28,
        model_path: Optional[str] = None,
        active_nodes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Partitions model transformer layers across the mesh nodes and calculates layer blocks.
        
        Args:
            model_name: Identifier of the model (e.g. 'Lauburu-AGI-Offspring-v1')
            total_layers: Total number of transformer layers in the model (e.g. 24, 28, 32, 64, 80)
            model_path: Optional filesystem path or HuggingFace repo
            active_nodes: Optional list of specific layer keys/node IDs to shard across (defaults to all 7)
            
        Returns:
            Structured sharding plan dictionary.
        """
        if total_layers <= 0:
            raise ValueError(f"total_layers must be a positive integer, got {total_layers}")

        # Resolve active nodes
        selected_nodes: Dict[str, Dict[str, Any]] = {}
        if active_nodes:
            for k, v in self.mesh_layers.items():
                if k in active_nodes or v["node_id"] in active_nodes:
                    selected_nodes[k] = v
        if not selected_nodes:
            selected_nodes = self.mesh_layers.copy()

        # Calculate proportional layer allocation using Hare-Niemeyer largest-remainder method
        total_vram = sum(n["usable_vram_gb"] for n in selected_nodes.values())
        raw_allocations = {}
        floor_allocations = {}
        remainders = {}

        num_nodes = len(selected_nodes)
        if total_layers < num_nodes:
            # When total layers is smaller than node count, allocate 1 layer to top-capacity nodes
            sorted_nodes = sorted(selected_nodes.items(), key=lambda x: x[1]["usable_vram_gb"], reverse=True)
            allocated_counts = {}
            for i, (k, _) in enumerate(sorted_nodes):
                allocated_counts[k] = 1 if i < total_layers else 0
        else:
            for k, n in selected_nodes.items():
                share = (n["usable_vram_gb"] / total_vram) * total_layers
                raw_allocations[k] = share
                floor_allocations[k] = int(share)
                remainders[k] = share - floor_allocations[k]

            unallocated = total_layers - sum(floor_allocations.values())
            sorted_remainders = sorted(remainders.items(), key=lambda x: x[1], reverse=True)
            
            allocated_counts = floor_allocations.copy()
            for i in range(unallocated):
                k = sorted_remainders[i % len(sorted_remainders)][0]
                allocated_counts[k] += 1

        # Calculate contiguous non-overlapping [start_block, end_block) indices
        current_layer = 0
        shards: List[Dict[str, Any]] = []
        node_allocations: Dict[str, Tuple[int, int]] = {}

        for k, node_info in selected_nodes.items():
            count = allocated_counts.get(k, 0)
            start_block = current_layer
            end_block = current_layer + count
            current_layer = end_block

            node_allocations[k] = (start_block, end_block)
            node_allocations[node_info["node_id"]] = (start_block, end_block)

            # Generate individual startup command for this specific shard
            petals_cmd = self._build_single_petals_command(
                model_name=model_name,
                node_info=node_info,
                start_block=start_block,
                end_block=end_block,
                count=count
            )

            # RPC server command
            rpc_cmd = "ggml-rpc-server -H 0.0.0.0 -p 50052" if node_info["platform"] == "android_termux" else "llama-rpc-server -H 0.0.0.0 -p 50052"

            shards.append({
                "layer_key": k,
                "layer_number": node_info["layer"],
                "node_id": node_info["node_id"],
                "node_name": node_info["name"],
                "platform": node_info["platform"],
                "device_type": node_info["device_type"],
                "ip": node_info.get("tailscale_ip") or node_info.get("lan_ip"),
                "rpc_port": node_info["rpc_port"],
                "start_block": start_block,
                "end_block": end_block,
                "layer_count": count,
                "block_indices": f"{start_block}:{end_block}",
                "torch_dtype": node_info["torch_dtype"],
                "usable_vram_gb": node_info["usable_vram_gb"],
                "compute_share_pct": round((count / total_layers) * 100, 2) if total_layers > 0 else 0.0,
                "petals_startup_command": petals_cmd,
                "rpc_server_command": rpc_cmd
            })

        # Resolved canonical model path
        resolved_model_path = model_path or str(CANONICAL_DATA_DIR / "models" / model_name)

        # Generate Petals startup commands dict
        petals_commands = self.generate_petals_startup_commands(
            model_name=model_name,
            total_layers=total_layers,
            bootstrap_peer=self.bootstrap_peer,
            active_nodes=list(selected_nodes.keys())
        )

        # Generate llama.cpp RPC config
        llama_rpc_config = self.generate_llama_rpc_commands(
            model_path=resolved_model_path,
            active_nodes=list(selected_nodes.keys())
        )

        plan = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "model_path": resolved_model_path,
            "total_layers": total_layers,
            "total_allocated_layers": sum(allocated_counts.values()),
            "total_pooled_vram_gb": round(total_vram, 2),
            "active_nodes_count": len(selected_nodes),
            "dht_prefix": self.dht_prefix,
            "bootstrap_peer": self.bootstrap_peer,
            "shards": shards,
            "node_allocations": node_allocations,
            "petals_startup_commands": petals_commands,
            "llama_rpc_config": llama_rpc_config,
            "canonical_storage_path": str(CANONICAL_DATA_DIR / "petals_sharding_plans" / f"{model_name}_sharding_plan.json")
        }

        return plan

    def _build_single_petals_command(
        self,
        model_name: str,
        node_info: Dict[str, Any],
        start_block: int,
        end_block: int,
        count: int,
        bootstrap_peer: Optional[str] = None
    ) -> str:
        """Helper to build a precise Petals CLI command for a node given its slice."""
        python_cmd = node_info["python_cmd"]
        device = node_info["device_type"]
        dtype = node_info["torch_dtype"]
        port = node_info["port"]
        peer = bootstrap_peer or self.bootstrap_peer
        quoted_model_name = shlex.quote(model_name)
        quoted_peer = shlex.quote(peer)

        if node_info.get("is_bootstrap"):
            # Linux Head Node / DHT Bootstrap node
            return (
                f"{python_cmd} -m petals.cli.run_server "
                f"--model {quoted_model_name} "
                f"--dht_prefix {self.dht_prefix} "
                f"--port {port} "
                f"--num_blocks {count} "
                f"--block_indices {start_block}:{end_block} "
                f"--torch_dtype {dtype} "
                f"--device {device}"
            )
        elif node_info["platform"] == "android_termux":
            # Android Termux ARM64 Edge node
            return (
                f"{python_cmd} -m petals.cli.run_server "
                f"--model {quoted_model_name} "
                f"--initial_peers {quoted_peer} "
                f"--num_blocks {count} "
                f"--port {port} "
                f"--torch_dtype {dtype} "
                f"--device {device}"
            )
        else:
            # macOS / Metal MPS or Linux Worker nodes
            return (
                f"{python_cmd} -m petals.cli.run_server "
                f"--model {quoted_model_name} "
                f"--initial_peers {quoted_peer} "
                f"--block_indices {start_block}:{end_block} "
                f"--port {port} "
                f"--torch_dtype {dtype} "
                f"--device {device}"
            )

    def generate_petals_startup_commands(
        self,
        model_name: str,
        total_layers: int = 28,
        bootstrap_peer: Optional[str] = None,
        active_nodes: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Programmatically generates valid CLI startup commands for at least 3 distinct layers:
          - Mac Node (macOS / Metal / MPS)
          - Linux Head Node (x86_64 CPU DHT Bootstrap)
          - Android Termux (ARM64 CPU Edge)
        as well as all active mesh layers.
        
        Returns a dictionary mapping both layer keys and platform aliases to startup commands.
        """
        if total_layers <= 0:
            raise ValueError(f"total_layers must be a positive integer, got {total_layers}")

        peer = bootstrap_peer or self.bootstrap_peer

        # Partition layers
        selected_nodes = {}
        if active_nodes:
            for k, v in self.mesh_layers.items():
                if k in active_nodes or v["node_id"] in active_nodes:
                    selected_nodes[k] = v
        if not selected_nodes:
            selected_nodes = self.mesh_layers.copy()

        # Compute block counts for active nodes
        total_vram = sum(n["usable_vram_gb"] for n in selected_nodes.values())
        floor_allocations = {}
        remainders = {}
        for k, n in selected_nodes.items():
            share = (n["usable_vram_gb"] / total_vram) * total_layers
            floor_allocations[k] = int(share)
            remainders[k] = share - floor_allocations[k]

        unallocated = total_layers - sum(floor_allocations.values())
        sorted_remainders = sorted(remainders.items(), key=lambda x: x[1], reverse=True)
        allocated_counts = floor_allocations.copy()
        for i in range(unallocated):
            k = sorted_remainders[i % len(sorted_remainders)][0]
            allocated_counts[k] += 1

        # Build commands
        commands: Dict[str, str] = {}
        current_layer = 0
        for k, node_info in selected_nodes.items():
            count = allocated_counts.get(k, 0)
            start_block = current_layer
            end_block = current_layer + count
            current_layer = end_block

            cmd = self._build_single_petals_command(
                model_name=model_name,
                node_info=node_info,
                start_block=start_block,
                end_block=end_block,
                count=count,
                bootstrap_peer=peer
            )

            # Store by multiple identifier formats for convenient lookup
            commands[k] = cmd
            commands[node_info["node_id"]] = cmd

        # Explicitly guarantee canonical aliases for the 3 core required platforms:
        # 1. Mac Node (macOS / Metal / MPS)
        if "layer_1_mac_host" in commands:
            commands["mac_node"] = commands["layer_1_mac_host"]
            commands["macos_mps"] = commands["layer_1_mac_host"]
            commands["Mac_Node"] = commands["layer_1_mac_host"]

        # 2. Linux Head Node (x86_64 CPU DHT Bootstrap)
        if "layer_3_linux_node" in commands:
            commands["linux_head_node"] = commands["layer_3_linux_node"]
            commands["linux_cpu_bootstrap"] = commands["layer_3_linux_node"]
            commands["Linux_Head_Node"] = commands["layer_3_linux_node"]

        # 3. Android Termux (ARM64 CPU Edge)
        if "layer_6_pixel_10_pro" in commands:
            commands["android_termux"] = commands["layer_6_pixel_10_pro"]
            commands["android_edge"] = commands["layer_6_pixel_10_pro"]
            commands["Pixel_10_Pro_XL"] = commands["layer_6_pixel_10_pro"]

        return commands

    def generate_llama_rpc_commands(
        self,
        model_path: str,
        active_nodes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generates llama-rpc-server worker daemon commands and llama-server master
        tensor split launch configurations.
        
        Args:
            model_path: Canonical path to GGUF model
            active_nodes: Optional subset of nodes
            
        Returns:
            Dict containing worker commands, RPC flags, tensor splits, and full launch arguments.
        """
        selected_nodes = {}
        if active_nodes:
            for k, v in self.mesh_layers.items():
                if k in active_nodes or v["node_id"] in active_nodes:
                    selected_nodes[k] = v
        if not selected_nodes:
            selected_nodes = self.mesh_layers.copy()

        # Identify master and worker nodes
        master_key = "layer_1_mac_host"
        master_node = selected_nodes.get(master_key, list(selected_nodes.values())[0])

        worker_nodes = {k: v for k, v in selected_nodes.items() if k != master_key}

        # Build worker daemon commands
        worker_daemon_commands: Dict[str, str] = {}
        rpc_worker_endpoints: List[str] = []
        tensor_split_ratios: List[int] = []

        # Include master node in tensor split calculation
        master_vram = int(round(master_node["usable_vram_gb"]))
        tensor_split_ratios.append(master_vram)

        for k, v in worker_nodes.items():
            ip = v.get("tailscale_ip") or v.get("lan_ip") or "127.0.0.1"
            port = v["rpc_port"]
            rpc_worker_endpoints.append(f"{ip}:{port}")
            tensor_split_ratios.append(int(round(v["usable_vram_gb"])))

            if v["platform"] == "android_termux":
                cmd = f"ggml-rpc-server -H 0.0.0.0 -p {port} -t 8"
            else:
                cmd = f"llama-rpc-server -H 0.0.0.0 -p {port}"
            worker_daemon_commands[k] = cmd
            worker_daemon_commands[v["node_id"]] = cmd

        rpc_hosts_str = ",".join(rpc_worker_endpoints)
        tensor_splits_str = ",".join(str(s) for s in tensor_split_ratios)

        rpc_flag = f"--rpc {rpc_hosts_str}" if rpc_hosts_str else ""
        tensor_split_flag = f"-ts {tensor_splits_str}"

        full_launch_args = f"{rpc_flag} {tensor_split_flag}".strip()
        master_server_command = (
            f"llama-server -m {model_path} --host 0.0.0.0 --port 9005 -c 4096 -ngl 99 {full_launch_args}"
        )

        return {
            "master_server_command": master_server_command,
            "worker_daemon_commands": worker_daemon_commands,
            "rpc_hosts_str": rpc_hosts_str,
            "tensor_split_str": tensor_splits_str,
            "rpc_flag": rpc_flag,
            "tensor_split_flag": tensor_split_flag,
            "full_launch_args": full_launch_args,
            "tensor_splits": tensor_split_ratios,
            "active_workers": [
                {"node_id": v["node_id"], "name": v["name"], "ip": v.get("tailscale_ip"), "port": v["rpc_port"]}
                for v in worker_nodes.values()
            ],
            "model_path": model_path
        }

    def save_sharding_plan(
        self,
        plan: Dict[str, Any],
        filename: Optional[str] = None
    ) -> str:
        """
        Saves a sharding plan JSON to canonical workspace data storage (/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/).
        Requirement R4 strictly enforces all outputs under data directory.
        """
        model_name = plan.get("model_name", "unnamed_model")
        fname = Path(filename).name if filename else f"{model_name}_sharding_plan.json"
        
        target_file = self.sharding_plans_dir / fname
        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
            logger.info(f"✅ Saved sharding plan to {target_file}")
        except Exception as e:
            logger.error(f"Failed to write sharding plan to {target_file}: {e}")
            raise

        # Return the canonical path representation
        canonical_target = CANONICAL_DATA_DIR / "petals_sharding_plans" / fname
        return str(canonical_target)

    def load_sharding_plan(self, filename: str) -> Optional[Dict[str, Any]]:
        """Loads an existing sharding plan from data storage."""
        target_file = self.sharding_plans_dir / filename
        if not target_file.exists():
            # Try direct path
            target_file = Path(filename)
        if target_file.exists():
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read sharding plan from {target_file}: {e}")
        return None

    def validate_sharding_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Validates that a sharding plan has continuous, non-overlapping layer ranges
        that cover exactly 0 to total_layers - 1.
        """
        total_layers = plan.get("total_layers", 0)
        shards = plan.get("shards", [])
        if total_layers <= 0 or not shards:
            return False

        covered_layers = set()
        expected_layer = 0

        for shard in shards:
            start = shard["start_block"]
            end = shard["end_block"]
            if start != expected_layer:
                logger.warning(f"Validation failure: gap or overlap at block {start} (expected {expected_layer})")
                return False
            for layer_idx in range(start, end):
                if layer_idx in covered_layers:
                    logger.warning(f"Validation failure: duplicate layer {layer_idx}")
                    return False
                covered_layers.add(layer_idx)
            expected_layer = end

        if expected_layer != total_layers or len(covered_layers) != total_layers:
            logger.warning(f"Validation failure: covered {len(covered_layers)} layers, expected {total_layers}")
            return False

        return True

    def broadcast_merged_offspring(
        self,
        model_name: str,
        model_path: Optional[str] = None,
        total_layers: int = 28
    ) -> Dict[str, Any]:
        """
        Broadcasts a newly merged AGI offspring across the 7-device network (Requirement R3):
          1. Shards the model across the 7-device mesh nodes.
          2. Programmatically generates Petals startup commands for macOS, Linux, and Android.
          3. Configures llama.cpp RPC master and worker tensor splits.
          4. Persists the distribution plan to canonical storage (Requirement R4).
        """
        logger.info(f"🌐 Broadcasting merged AGI offspring '{model_name}' across 7-device mesh...")
        
        plan = self.shard_model_across_mesh(
            model_name=model_name,
            total_layers=total_layers,
            model_path=model_path
        )
        
        # Validate plan integrity
        if not self.validate_sharding_plan(plan):
            raise RuntimeError(f"Generated sharding plan for {model_name} failed validation.")

        # Save to canonical data storage
        canonical_path = self.save_sharding_plan(plan)
        plan["saved_canonical_path"] = canonical_path
        
        logger.info(f"✨ Successfully sharded and broadcasted '{model_name}' across {len(plan['shards'])} mesh layers.")
        return plan


if __name__ == "__main__":
    coordinator = PetalsMeshShardingCoordinator()
    print("=== Lauburu 7-Device Hardware Mesh Topology ===")
    print(json.dumps(coordinator.get_mesh_topology(), indent=2))

    print("\n=== Sharding Plan for Lauburu-AGI-Offspring-v1 (28 Layers) ===")
    test_plan = coordinator.shard_model_across_mesh(
        model_name="Lauburu-AGI-Offspring-v1",
        total_layers=28
    )
    print(json.dumps(test_plan, indent=2))
