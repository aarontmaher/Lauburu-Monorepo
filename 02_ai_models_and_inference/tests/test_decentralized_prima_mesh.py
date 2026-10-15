# -*- coding: utf-8 -*-
"""
Master Test Suite for Decentralized prima.cpp Multi-Device Mesh Self-Healing
============================================================================
Subsystem: 02_ai_models_and_inference/tests/test_decentralized_prima_mesh.py
Lauburu Mesh Ecosystem — 2026
"""

import os
import sys
import time
import pytest
from pathlib import Path

# Add subsystem root to sys.path
_curr_dir = Path(__file__).resolve().parent
_subsystem_root = _curr_dir.parent
if str(_subsystem_root) not in sys.path:
    sys.path.insert(0, str(_subsystem_root))

from decentralized_prima_mesh_coordinator import DecentralizedPrimaMeshCoordinator
from distributed_mesh_consensus import DistributedMeshConsensus
from decentralized_mesh_healer import DecentralizedMeshHealer


def test_7_device_topology_and_pooled_vram():
    """Verifies that all 7 devices pool >= 80 GB AI VRAM and have designated roles."""
    coord = DecentralizedPrimaMeshCoordinator()
    assert len(coord.MESH_TOPOLOGY) == 7
    assert coord.pooled_vram_gb >= 80.0
    assert coord.total_ram_gb >= 100.0

    l1 = coord.get_node_by_id("L1")
    assert l1 is not None
    assert l1.priority == 100
    assert l1.tb4_ip is not None

    gw = coord.get_node_by_id("GW")
    assert gw is not None
    assert gw.standalone_model_capable is True
    assert gw.usable_ai_vram_gb >= 0.120


def test_self_healing_model_distribution():
    """Verifies that 100% of mesh devices hold the self-healing model (7x redundancy)."""
    coord = DecentralizedPrimaMeshCoordinator()
    dist = coord.compute_self_healing_model_distribution("SmolLM2-135M-Instruct.Q4_K_M", 84.0)

    assert dist["total_nodes_holding_model"] == 7
    assert "7x" in dist["decentralized_redundancy_factor"]
    for n in dist["nodes"]:
        assert n["can_heal_autonomously"] is True


def test_prp_pipelined_ring_topology():
    """Verifies that PRP ring links are computed with sub-millisecond Thunderbolt DMA."""
    coord = DecentralizedPrimaMeshCoordinator()
    links = coord.compute_ring_topology()

    assert len(links) >= 7
    tb4_link = next(l for l in links if l.from_node == "L1" and l.to_node == "L2")
    assert tb4_link.transport == "TB4_DMA"
    assert tb4_link.rtt_ms <= 0.25
    assert tb4_link.bandwidth_gbps >= 10.0


def test_distributed_consensus_leader_election():
    """Verifies priority leader election, lease expiration, and dynamic failover."""
    consensus = DistributedMeshConsensus(current_node_id="L1")
    now = time.time()

    # Initial state: L1 is leader
    consensus.record_heartbeat("L1", is_online=True, timestamp=now)
    consensus.record_heartbeat("L2", is_online=True, timestamp=now)
    consensus.record_heartbeat("GW", is_online=True, timestamp=now)

    leader = consensus.elect_leader(current_time=now)
    assert leader == "L1"
    assert consensus.can_execute_healing_action("L1", current_time=now) is True

    # Scenario: L1 misses heartbeats (dies), L2 takes over
    t_after_fail = now + 4.0
    consensus.record_heartbeat("L2", is_online=True, timestamp=t_after_fail)
    consensus.record_heartbeat("GW", is_online=True, timestamp=t_after_fail)

    new_leader = consensus.elect_leader(current_time=t_after_fail)
    assert new_leader == "L2"


def test_decentralized_healing_scenarios():
    """Verifies autonomous healing across router death, Tailscale drop, and hardware USB."""
    healer = DecentralizedMeshHealer(current_node_id="L1")

    # 1. Router unreachable -> Out-of-band resurrection
    ev1 = healer.evaluate_and_heal_anomaly(
        target_node_id="GW",
        anomaly_type="ROUTER_GATEWAY_UNREACHABLE",
        metrics={"rtt_ms": 9999.0, "loss_pct": 100.0},
    )
    assert "Path 0" in ev1.chosen_pathway
    assert ev1.execution_success is True
    assert ev1.inference_latency_ms < 50.0

    # 2. Tailscale wireguard stale -> Systemd reload
    ev2 = healer.evaluate_and_heal_anomaly(
        target_node_id="L3",
        anomaly_type="TAILSCALE_HANDSHAKE_STALE",
        metrics={"handshake_age_s": 240.0},
    )
    assert "Path 1" in ev2.chosen_pathway
    assert ev2.execution_success is True

    # 3. L7 frozen wireless -> Hardware USB ADB override
    ev3 = healer.evaluate_and_heal_anomaly(
        target_node_id="L7",
        anomaly_type="WIRELESS_STACK_FROZEN_L7",
        metrics={"wifi_rssi_dbm": -99, "adb_tcp_responsive": False},
    )
    assert "Path 4.5" in ev3.chosen_pathway
    assert ev3.execution_success is True
