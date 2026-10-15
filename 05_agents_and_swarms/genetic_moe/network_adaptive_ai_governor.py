#!/usr/bin/env python3
"""
Autonomous Network-Adaptive AI Governor & Tool Self-Optimizer
============================================================
Subsystem: 05_agents_and_swarms/genetic_moe/network_adaptive_ai_governor.py
Lauburu 7-Layer Mesh — Dynamic Model Allocation, Tool Optimization & 24/7 Engine

Adapts the local AI strategy across 6 network connectivity states:
  - AIR_GAPPED_SERIAL      -> Standalone SLM (SmolLM2 360M), zero egress, pure POSIX/sysfs
  - AD_HOC_PEER_MESH       -> Speculative Proposer (k=1, Qwen 3B), BNEP PAN /dev/rfcomm0
  - LOCAL_HIGH_BANDWIDTH_LAN -> Pipelined-Ring (prima.cpp, k=3, Qwen 32B), Local LAN RPC
  - NOMAD_MOBILE_HOTSPOT   -> Adaptive Edge + Metered Cloud Teacher (Gemini Flash)
  - GLOBAL_ZERO_TRUST_OVERLAY -> Tailscale Peripheral Offloading onto Linux Ryzen Node
  - ULTRA_CLUSTER_TB4_DMA  -> 70B-80B MoE Tensor Sharded across 56GB Metal cluster (k=4)

Continuously self-optimizes tool selection via genetic evolutionary fitness and logs to Tri-Vault.
"""

from __future__ import annotations

import os
import sys
import time
import json
import fcntl
import random
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional, Tuple

from network_state_sensor import NetworkStateSensor, NetworkTopologyState, NetworkStateSnapshot

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
STATUS_FILE = WORKSPACE_ROOT / "data/network/network_adaptive_ai_status.json"
WEIGHTS_FILE = WORKSPACE_ROOT / "05_agents_and_swarms/genetic_moe/genetic_tool_weights.json"
LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")

STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
LORA_DATASET.parent.mkdir(parents=True, exist_ok=True)


class ToolDomain(str, Enum):
    SWE_BENCH = "swe_bench"
    HARDWARE_ADB = "hardware_adb"
    KERNEL_SYSFS = "kernel_sysfs"
    DOCKER_CONTAINER = "docker_container"
    LOCAL_AI_TRAINING = "local_ai_training"
    CLOUD_AI_OPTIMIZER = "cloud_ai_optimizer"
    SCREEN_LENS_OCR = "screen_lens_ocr"
    POSIX_SHELL = "posix_shell"


@dataclass
class ToolBindingSpec:
    domain: ToolDomain
    primary_exec: str
    fallback_strategy: str
    requires_network: bool
    requires_cloud: bool
    max_timeout_s: float
    weight: float = 0.125
    success_count: int = 0
    failure_count: int = 0


DEFAULT_TOOL_SPECS: Dict[ToolDomain, ToolBindingSpec] = {
    ToolDomain.SWE_BENCH: ToolBindingSpec(
        domain=ToolDomain.SWE_BENCH,
        primary_exec="/Users/aaron/.local/bin/sb-cli",
        fallback_strategy="posix_pytest_git_diff",
        requires_network=False,
        requires_cloud=False,
        max_timeout_s=180.0,
    ),
    ToolDomain.HARDWARE_ADB: ToolBindingSpec(
        domain=ToolDomain.HARDWARE_ADB,
        primary_exec="/Users/aaron/.local/bin/adb",
        fallback_strategy="posix_ssh_termux",
        requires_network=False,
        requires_cloud=False,
        max_timeout_s=30.0,
    ),
    ToolDomain.KERNEL_SYSFS: ToolBindingSpec(
        domain=ToolDomain.KERNEL_SYSFS,
        primary_exec="/usr/local/bin/dell-unthrottle.sh",
        fallback_strategy="posix_sysctl_procfs",
        requires_network=False,
        requires_cloud=False,
        max_timeout_s=15.0,
    ),
    ToolDomain.DOCKER_CONTAINER: ToolBindingSpec(
        domain=ToolDomain.DOCKER_CONTAINER,
        primary_exec="docker",
        fallback_strategy="posix_process_daemon",
        requires_network=False,
        requires_cloud=False,
        max_timeout_s=60.0,
    ),
    ToolDomain.LOCAL_AI_TRAINING: ToolBindingSpec(
        domain=ToolDomain.LOCAL_AI_TRAINING,
        primary_exec="python3",
        fallback_strategy="posix_python_trainer",
        requires_network=False,
        requires_cloud=False,
        max_timeout_s=300.0,
    ),
    ToolDomain.CLOUD_AI_OPTIMIZER: ToolBindingSpec(
        domain=ToolDomain.CLOUD_AI_OPTIMIZER,
        primary_exec="python3",
        fallback_strategy="local_mesh_fallback",
        requires_network=True,
        requires_cloud=True,
        max_timeout_s=45.0,
    ),
    ToolDomain.SCREEN_LENS_OCR: ToolBindingSpec(
        domain=ToolDomain.SCREEN_LENS_OCR,
        primary_exec="http://127.0.0.1:4003/stream.mjpg",
        fallback_strategy="posix_screencapture",
        requires_network=False,
        requires_cloud=False,
        max_timeout_s=20.0,
    ),
    ToolDomain.POSIX_SHELL: ToolBindingSpec(
        domain=ToolDomain.POSIX_SHELL,
        primary_exec="/bin/sh",
        fallback_strategy="native_posix_shell",
        requires_network=False,
        requires_cloud=False,
        max_timeout_s=60.0,
    ),
}


class NetworkAdaptiveAIGovernor:
    """
    Evaluates real-time network topology, selects model strategy, 
    and self-optimizes tool usage using genetic evolutionary fitness.
    """

    def __init__(self):
        self.sensor = NetworkStateSensor()
        self.generation = 1
        self.tools = self._load_or_init_tool_weights()

    def _load_or_init_tool_weights(self) -> Dict[ToolDomain, ToolBindingSpec]:
        specs = dict(DEFAULT_TOOL_SPECS)
        if WEIGHTS_FILE.exists():
            try:
                with open(WEIGHTS_FILE, "r") as f:
                    data = json.load(f)
                    self.generation = data.get("generation", 1)
                    weights = data.get("weights", {})
                    for d_str, w in weights.items():
                        try:
                            dom = ToolDomain(d_str)
                            if dom in specs:
                                specs[dom].weight = float(w)
                        except ValueError:
                            pass
            except Exception:
                pass
        return specs

    def save_weights(self):
        payload = {
            "generation": self.generation,
            "timestamp": int(time.time()),
            "weights": {dom.value: round(spec.weight, 4) for dom, spec in self.tools.items()},
        }
        with open(WEIGHTS_FILE, "w") as f:
            json.dump(payload, f, indent=2)

    def evaluate_strategy(self) -> Dict[str, Any]:
        """Runs the sensor and outputs full adaptive strategy for current network state."""
        snap = self.sensor.evaluate_state()

        # Tool filtering based on network availability:
        # In airgapped state, disable cloud tools
        is_airgapped = snap.active_topology == NetworkTopologyState.AIR_GAPPED_SERIAL or not snap.cloud_offload_allowed
        available_tools = []
        for dom, spec in self.tools.items():
            if is_airgapped and spec.requires_network:
                continue
            available_tools.append(dom.value)

        strategy = {
            "timestamp": snap.timestamp,
            "active_topology": snap.active_topology.value,
            "effective_bandwidth_mbps": snap.effective_bandwidth_mbps,
            "overall_link_score": snap.overall_link_score,
            "recommended_model_tier": snap.recommended_model_tier,
            "active_moe_top_k": snap.active_moe_top_k,
            "sharding_protocol": snap.sharding_protocol,
            "cloud_offload_allowed": snap.cloud_offload_allowed,
            "generation": self.generation,
            "available_tools": available_tools,
            "transports": {k: asdict(v) for k, v in snap.transports.items()},
        }

        # Write status atomically
        tmp_status = STATUS_FILE.with_suffix(".tmp")
        with open(tmp_status, "w") as f:
            json.dump(strategy, f, indent=2)
        tmp_status.replace(STATUS_FILE)

        return strategy

    def evolve_weights(self, reward_domain: ToolDomain, latency_ms: float, success: bool):
        """Applies genetic evolutionary reinforcement to tool routing weights."""
        spec = self.tools.get(reward_domain)
        if not spec:
            return

        if success:
            spec.success_count += 1
            # Fitness reward
            latency_factor = min(1.0, 1000.0 / max(10.0, latency_ms))
            delta = 0.05 * latency_factor
            spec.weight = min(1.0, spec.weight + delta)
        else:
            spec.failure_count += 1
            spec.weight = max(0.01, spec.weight - 0.05)

        # Normalize weights
        total = sum(s.weight for s in self.tools.values())
        if total > 0:
            for s in self.tools.values():
                s.weight = round(s.weight / total, 4)

        self.generation += 1
        self.save_weights()
        self._append_lora_pair(reward_domain, latency_ms, success)

    def _append_lora_pair(self, domain: ToolDomain, latency_ms: float, success: bool):
        """Appends training tuple under flock to continuous LoRA dataset."""
        pair = {
            "timestamp": int(time.time()),
            "source": "network_adaptive_ai_governor",
            "generation": self.generation,
            "domain": domain.value,
            "latency_ms": latency_ms,
            "success": success,
            "instruction": f"Select optimal tool for domain {domain.value} under current network topology.",
            "response": f"Bound to {self.tools[domain].primary_exec} with fallback {self.tools[domain].fallback_strategy}. Status: {'SUCCESS' if success else 'RETRY'}.",
        }
        try:
            with open(LORA_DATASET, "a") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(json.dumps(pair) + "\n")
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass


if __name__ == "__main__":
    gov = NetworkAdaptiveAIGovernor()
    strat = gov.evaluate_strategy()
    print(json.dumps(strat, indent=2))
