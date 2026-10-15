"""
00_core_infrastructure/lens_bootstrapper/orchestrator/prima_mesh_orchestrator.py
================================================================================
Milestone 3 (Features F11 & F12): Prima.cpp Mesh Sharding Allocator & PRP Parameter Generator.

Physics-aware dynamic layer calculation engine sharding LLM layers across 7 physical
mesh devices based on VRAM headroom, compute weight, link RTT/bandwidth, and thermal
derating factors.

Implements:
- F11: 7-Device Dynamic Layer Allocation & Strict Layer Conservation (\\sum l_i == L_total)
- F12: Upstream Prima.cpp ZeroMQ Piped-Ring Parallelism (PRP) CLI Parameter Generator
"""

from __future__ import annotations

import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("PrimaMeshOrchestrator")


@dataclass
class MeshNodeProfile:
    """Hardware and link profile for a physical mesh device participating in Prima.cpp."""
    name: str
    rank: int
    ip: str
    vram_mb: int
    link: str  # TB4, LAN, WIFI
    rtt_ms: float
    thermal: int = 0  # 0: NOMINAL, 1: FAIR/MODERATE, 2: SERIOUS, 3: CRITICAL
    compute_weight: float = 1.0


class PrimaMeshOrchestrator:
    """
    Authentic Prima.cpp PRP Sharding Engine & Parameter Generator.
    Shards frontier models across the 7-device physical mesh.
    """

    # Authoritative 7-device mesh hardware topology from 00_canonical_hardware_matrix.md
    NODE_PROFILES: Dict[str, Dict[str, Any]] = {
        "L1_mac_mini": {
            "rank": 0,
            "ip": "169.254.186.211",
            "vram_mb": 14000,
            "link": "TB4",
            "rtt_ms": 0.43,
            "thermal": 0,
            "compute_weight": 1.0,
        },
        "L1b_mac_mini_m2": {
            "rank": 1,
            "ip": "169.254.122.75",
            "vram_mb": 12000,
            "link": "TB4",
            "rtt_ms": 0.45,
            "thermal": 0,
            "compute_weight": 0.9,
        },
        "L5_mac_air_m4": {
            "rank": 2,
            "ip": "169.254.186.212",
            "vram_mb": 10000,
            "link": "TB4",
            "rtt_ms": 0.45,
            "thermal": 0,
            "compute_weight": 0.85,
        },
        "L2_macbook_intel": {
            "rank": 3,
            "ip": "100.103.212.21",
            "vram_mb": 4000,
            "link": "WIFI",
            "rtt_ms": 40.0,
            "thermal": 0,
            "compute_weight": 0.5,
        },
        "L3_linux_amd": {
            "rank": 4,
            "ip": "100.101.39.98",
            "vram_mb": 4000,
            "link": "LAN",
            "rtt_ms": 1.2,
            "thermal": 0,
            "compute_weight": 0.6,
        },
        "L6_pixel_10": {
            "rank": 5,
            "ip": "100.73.38.87",
            "vram_mb": 1500,
            "link": "WIFI",
            "rtt_ms": 15.0,
            "thermal": 0,
            "compute_weight": 0.3,
        },
        "L7_galaxy_s20": {
            "rank": 6,
            "ip": "100.78.206.96",
            "vram_mb": 1500,
            "link": "WIFI",
            "rtt_ms": 18.0,
            "thermal": 0,
            "compute_weight": 0.3,
        },
    }

    @classmethod
    def allocate_layers(
        cls,
        total_layers: int = 64,
        thermal_overrides: Optional[Dict[str, int]] = None,
        custom_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculates dynamic layer allocation across 7 physical mesh devices.
        
        Balances:
        - VRAM Headroom (vram_mb)
        - Compute silicon performance weight (compute_weight)
        - Link RTT and transport latency (lat_penalty: TB4 DMA = 1.0, LAN = 0.5, Wi-Fi = 0.2)
        - Thermal factor (theta_i: 0 -> 1.0, 1 -> 0.8, 2 -> 0.12/evacuate, 3 -> 0.0)
        
        Guarantees:
        - Strict layer conservation: sum(layers) == total_layers
        - Non-negative integer layer counts for all devices
        - If L1 is throttled (thermal_level >= 2), L1 layers <= 4 and excess is absorbed by TB4 peers (L1b & L5)
        """
        if total_layers <= 0:
            raise ValueError(f"total_layers must be positive, got {total_layers}")

        nodes = dict(custom_profiles or cls.NODE_PROFILES)
        thermals = thermal_overrides or {}

        # 1. Calculate effective weight w_i for each device
        effective_weights: Dict[str, float] = {}
        for name, profile in nodes.items():
            t_level = thermals.get(name, profile.get("thermal", 0))
            
            # Thermal factor theta_i
            if t_level == 0:
                t_factor = 1.0
            elif t_level == 1:
                t_factor = 0.8
            elif t_level == 2:
                # SERIOUS pressure: severely throttle node to enable evacuation
                t_factor = 0.12
            else:
                # CRITICAL pressure: isolate/quarantine
                t_factor = 0.0

            # Latency penalty based on probed RTT:
            # TB4 DMA (RTT < 1.0 ms) receives full 1.0 weight
            # High-speed LAN (RTT < 5.0 ms) receives 0.5 weight
            # Wi-Fi / Tailscale overlay receives 0.2 weight to prevent ring stall
            rtt = profile.get("rtt_ms", 10.0)
            if rtt < 1.0:
                lat_penalty = 1.0
            elif rtt < 5.0:
                lat_penalty = 0.5
            else:
                lat_penalty = 0.2

            compute_w = profile.get("compute_weight", 1.0)
            vram_gb = profile.get("vram_mb", 1000) / 1000.0

            w = vram_gb * lat_penalty * t_factor * compute_w
            effective_weights[name] = max(0.0, w)

        total_weight = sum(effective_weights.values())
        if total_weight <= 0.0:
            raise ValueError("All mesh nodes are throttled or unavailable; cannot shard model")

        # 2. Initial proportional allocation
        sorted_nodes = sorted(nodes.keys(), key=lambda n: nodes[n].get("rank", 0))
        allocations: Dict[str, int] = {}
        for name in sorted_nodes:
            w = effective_weights[name]
            raw_layers = int(round((w / total_weight) * total_layers))
            allocations[name] = max(0, raw_layers)

        # 3. L1 Host Sanctuary & Evacuation Invariant:
        # If L1 is experiencing a thermal spike (level >= 2), L1 MUST NOT exceed 4 layers.
        # Evacuated layers are shifted to healthy Thunderbolt 4 peers (L1b and L5).
        l1_thermal = thermals.get("L1_mac_mini", nodes.get("L1_mac_mini", {}).get("thermal", 0))
        if l1_thermal >= 2 and "L1_mac_mini" in allocations:
            max_l1 = 0 if l1_thermal >= 3 else min(4, allocations["L1_mac_mini"])
            if allocations["L1_mac_mini"] > max_l1:
                evacuate = allocations["L1_mac_mini"] - max_l1
                allocations["L1_mac_mini"] = max_l1
                
                # Split evacuated layers between L1b and L5 proportionally to VRAM
                l1b_vram = nodes.get("L1b_mac_mini_m2", {}).get("vram_mb", 12000)
                l5_vram = nodes.get("L5_mac_air_m4", {}).get("vram_mb", 10000)
                tb_vram_sum = l1b_vram + l5_vram
                if tb_vram_sum > 0:
                    l1b_gain = int(round(evacuate * (l1b_vram / tb_vram_sum)))
                    l5_gain = evacuate - l1b_gain
                    if "L1b_mac_mini_m2" in allocations:
                        allocations["L1b_mac_mini_m2"] += l1b_gain
                    if "L5_mac_air_m4" in allocations:
                        allocations["L5_mac_air_m4"] += l5_gain

        # 4. Strict Layer Conservation: sum(layers) == total_layers
        diff = total_layers - sum(allocations.values())
        if diff != 0:
            # Deterministically adjust the highest-capacity healthy Thunderbolt peer
            if l1_thermal < 2 and "L1_mac_mini" in allocations:
                target_peer = "L1_mac_mini"
            elif "L1b_mac_mini_m2" in allocations and thermals.get("L1b_mac_mini_m2", 0) < 2:
                target_peer = "L1b_mac_mini_m2"
            elif "L5_mac_air_m4" in allocations and thermals.get("L5_mac_air_m4", 0) < 2:
                target_peer = "L5_mac_air_m4"
            else:
                # Find any node with highest weight
                target_peer = max(sorted_nodes, key=lambda n: effective_weights[n])

            allocations[target_peer] = max(0, allocations[target_peer] + diff)

        # Final sanity check on layer conservation
        final_sum = sum(allocations.values())
        if final_sum != total_layers:
            # Secondary pass if rounding caused edge discrepancies
            discrepancy = total_layers - final_sum
            for peer in ["L1b_mac_mini_m2", "L5_mac_air_m4", "L1_mac_mini"]:
                if peer in allocations and (allocations[peer] + discrepancy) >= 0:
                    allocations[peer] += discrepancy
                    break

        # 5. Build standardized node metadata conforming to Interface Contract 3
        result: Dict[str, Dict[str, Any]] = {}
        for name in sorted_nodes:
            prof = nodes[name]
            t_val = thermals.get(name, prof.get("thermal", 0))
            if t_val == 0:
                t_state = "NOMINAL"
            elif t_val == 1:
                t_state = "MODERATE"
            elif t_val == 2:
                t_state = "SERIOUS"
            else:
                t_state = "CRITICAL"

            result[name] = {
                "rank": prof.get("rank", 0),
                "ip": prof.get("ip", "127.0.0.1"),
                "layers": int(allocations[name]),
                "vram_mb": int(prof.get("vram_mb", 1000)),
                "thermal_state": t_state,
            }

        return result

    @classmethod
    def generate_prp_cli_args(
        cls,
        node_name: str,
        allocations: Dict[str, Dict[str, Any]],
        data_port: int = 9000,
        signal_port: int = 10000,
        prefetch: bool = True,
    ) -> List[str]:
        """
        Formats ZeroMQ Piped-Ring Parallelism (PRP) CLI arguments for upstream prima.cpp.
        
        Matches contracts from /Users/aaron/prima.cpp:
        --world <size> --rank <rank> --master <master_ip> --next <next_ip>
        --data-port <data_port> --signal-port <signal_port>
        --gpu-mem <gpu_mem_gib> --gpu-layers <layers> [--prefetch]
        """
        if node_name not in allocations:
            raise KeyError(f"Node '{node_name}' not found in mesh allocations")

        node_info = allocations[node_name]
        world_size = len(allocations)
        rank = node_info["rank"]

        # Master is defined as rank 0
        master_candidates = [info["ip"] for info in allocations.values() if info.get("rank") == 0]
        if not master_candidates:
            raise ValueError("No Rank 0 node found in allocations to serve as ring master")
        master_ip = master_candidates[0]

        # Next node in ring is (rank + 1) mod world_size
        next_rank = (rank + 1) % world_size
        next_candidates = [info["ip"] for info in allocations.values() if info.get("rank") == next_rank]
        if not next_candidates:
            raise ValueError(f"Next node with rank {next_rank} not found in allocations")
        next_ip = next_candidates[0]

        gpu_mem_gib = max(1, int(node_info.get("vram_mb", 1024) / 1024))
        layers = int(node_info.get("layers", 0))

        args = [
            "--world", str(world_size),
            "--rank", str(rank),
            "--master", master_ip,
            "--next", next_ip,
            "--data-port", str(data_port),
            "--signal-port", str(signal_port),
            "--gpu-mem", str(gpu_mem_gib),
            "--gpu-layers", str(layers),
        ]
        if prefetch:
            args.append("--prefetch")

        return args

    @classmethod
    def generate_all_prp_cli_args(
        cls,
        allocations: Dict[str, Dict[str, Any]],
        data_port: int = 9000,
        signal_port: int = 10000,
        prefetch: bool = True,
    ) -> Dict[str, List[str]]:
        """Generates CLI arguments for all nodes participating in the PRP ring."""
        return {
            name: cls.generate_prp_cli_args(
                name, allocations, data_port=data_port, signal_port=signal_port, prefetch=prefetch
            )
            for name in allocations
        }

    @classmethod
    def generate_prp_command_line(
        cls,
        node_name: str,
        allocations: Dict[str, Dict[str, Any]],
        model_path: str = "download/qwen_38_max_27b_q4_k_m.gguf",
        binary_path: str = "/Users/aaron/prima.cpp/build/bin/llama-cli",
        data_port: int = 9000,
        signal_port: int = 10000,
        prefetch: bool = True,
        extra_flags: Optional[List[str]] = None,
    ) -> str:
        """Constructs the complete executable command-line string for a ring worker."""
        args = cls.generate_prp_cli_args(
            node_name, allocations, data_port=data_port, signal_port=signal_port, prefetch=prefetch
        )
        cmd = [binary_path, "-m", model_path] + args
        if extra_flags:
            cmd.extend(extra_flags)
        return " ".join(cmd)

    @classmethod
    def generate_mesh_config(
        cls,
        allocations: Dict[str, Dict[str, Any]],
        model: str = "qwen_38_max_27b",
        total_layers: int = 64,
        thermal_spike_active: bool = False,
        trigger: Optional[str] = None,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Creates a JSON-serializable dictionary matching Interface Contract 3.
        """
        config: Dict[str, Any] = {
            "model": model,
            "total_layers": total_layers,
            "world_size": len(allocations),
            "timestamp": timestamp or int(time.time()),
            "thermal_spike_active": thermal_spike_active,
            "nodes": allocations,
        }
        if trigger is not None:
            config["trigger"] = trigger
        return config


# Compatibility alias
PrimaMeshAllocator = PrimaMeshOrchestrator
