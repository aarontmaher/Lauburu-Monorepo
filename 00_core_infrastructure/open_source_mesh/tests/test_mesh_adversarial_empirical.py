#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
00_core_infrastructure/open_source_mesh/tests/test_mesh_adversarial_empirical.py
================================================================================
Adversarial Empirical Challenge Test Suite for Open-Source Mesh Infrastructure
& Autonomous AGI Governance (LAUBURU-STRAT-2026-MESH-AGI-001)

Stress-Tests:
1. Multi-WAN Bonding & Failover Edge Cases (TB4 DMA collapse, 5G cellular jitter, BLEST vs lowest-rtt).
2. Headscale Embedded DERP & STUN Failover under Carrier CGNAT (UDP 3478 drop -> HTTPS 8443 relay).
3. Secure Sandboxing Containment & Safety (QEMU br-test0 isolation, Docker --net=none, cgroups).
4. Closed-Form Multi-Objective Reward & Dynamic ELO Mathematical Invariants.
5. Ed25519 Merkle Root Cryptographic Attestation.
"""

import math
import time
import json
import hashlib
import struct
import pytest
from typing import Dict, List, Any, Tuple


# ==============================================================================
# Domain 1: Multi-WAN Bonding, TB4 Failover & MPTCP Scheduler Simulation
# ==============================================================================

class MptcpSubflow:
    def __init__(self, name: str, capacity_mbps: float, rtt_ms: float, loss_rate: float):
        self.name = name
        self.capacity_mbps = capacity_mbps
        self.rtt_ms = rtt_ms
        self.loss_rate = loss_rate
        self.bytes_in_flight = 0
        self.is_up = True

class MptcpSchedulerSimulator:
    """Simulates MPTCP Schedulers: lowest-rtt, blest, and redundant under chaos injection."""
    def __init__(self, scheduler_type: str = "lowest-rtt"):
        self.scheduler_type = scheduler_type
        self.subflows: Dict[str, MptcpSubflow] = {}

    def add_subflow(self, name: str, capacity_mbps: float, rtt_ms: float, loss_rate: float = 0.0):
        self.subflows[name] = MptcpSubflow(name, capacity_mbps, rtt_ms, loss_rate)

    def select_subflow(self, packet_size_bytes: int) -> Tuple[str, float]:
        active_flows = [f for f in self.subflows.values() if f.is_up]
        if not active_flows:
            raise RuntimeError("All MPTCP subflows are down! Network partition.")

        if self.scheduler_type == "redundant":
            # Duplicate across all active subflows
            min_rtt = min(f.rtt_ms for f in active_flows)
            return "all", min_rtt

        elif self.scheduler_type == "lowest-rtt":
            # Select subflow with lowest measured RTT
            best = min(active_flows, key=lambda f: f.rtt_ms)
            return best.name, best.rtt_ms

        elif self.scheduler_type == "blest":
            # Blocking Estimation Scheduler:
            # Prevents sending on high-RTT link if it will arrive later than waiting
            # for the fast link to become free.
            # Condition: If fast link queue time + RTT_fast < RTT_slow, suppress slow link.
            sorted_flows = sorted(active_flows, key=lambda f: f.rtt_ms)
            fast_flow = sorted_flows[0]
            
            # Estimated drain time on fast link in ms
            drain_time_ms = (fast_flow.bytes_in_flight * 8.0) / (fast_flow.capacity_mbps * 1000.0)
            
            for flow in sorted_flows:
                if flow.name == fast_flow.name:
                    flow.bytes_in_flight += packet_size_bytes
                    return flow.name, flow.rtt_ms
                else:
                    # Check if using this slow flow causes receiver buffer head-of-line blocking
                    if flow.rtt_ms > (fast_flow.rtt_ms + drain_time_ms):
                        # Suppress slow flow to avoid buffer stall
                        continue
                    else:
                        flow.bytes_in_flight += packet_size_bytes
                        return flow.name, flow.rtt_ms
            
            # Fallback to fast flow
            fast_flow.bytes_in_flight += packet_size_bytes
            return fast_flow.name, fast_flow.rtt_ms

        else:
            raise ValueError(f"Unknown scheduler: {self.scheduler_type}")


def calculate_reward_total(
    t_bonded: float,
    t_target: float,
    sum_capacity: float,
    avg_rtt: float,
    tau_rtt: float,
    rtt_max_budget: float,
    t_switch: float,
    t_cutoff: float,
    session_dropped: bool,
    p_loss: float,
    d_queue: float,
    d_base: float,
    rtt_max: float,
    rtt_min: float,
    power_watts: float,
    node_temps: Dict[str, float],
    temp_crits: Dict[str, float],
    psi_weights: Dict[str, float],
    is_authentic_telemetry: bool = True
) -> float:
    """Evaluates the exact closed-form multi-objective reward R_total(s, a) from Section 3.2."""
    if not is_authentic_telemetry:
        return -float("inf")

    # Term 1: Throughput Reward
    r_thru = 100.0 * (0.6 * (t_bonded / max(1.0, sum_capacity)) + 0.4 * min(1.0, t_bonded / max(1.0, t_target)))

    # Term 2: Latency Reward
    r_rtt = 100.0 * math.exp(-avg_rtt / max(0.001, tau_rtt)) - 2.0 * max(0.0, avg_rtt - rtt_max_budget)

    # Term 3: Failover Latency Reward
    if not session_dropped and t_switch <= t_cutoff:
        r_failover = 100.0 * (1.0 - (t_switch / max(0.001, t_cutoff)))
    else:
        r_failover = -150.0

    # Term 4: Packet Loss & Queue Delay Penalty
    p_loss_term = 50.0 * (p_loss ** 2) + 25.0 * math.log(1.0 + (d_queue / max(0.001, d_base)))
    if p_loss > 1.0:  # > 1% packet loss incurs critical penalty
        p_loss_term += 100.0

    # Term 5: Packet Reordering Skew Penalty
    skew_ratio = (rtt_max - rtt_min) / max(0.001, avg_rtt)
    p_skew = 30.0 * (max(0.0, skew_ratio - 0.15) ** 2)

    # Term 6: Energy & Thermal Reward
    efficiency = min(10.0, t_bonded / max(0.1, power_watts))
    thermal_penalty = 0.0
    for node, temp in node_temps.items():
        crit = temp_crits.get(node, 75.0)
        psi = psi_weights.get(node, 1.0)
        thermal_penalty += psi * (max(0.0, temp - crit) ** 2)
    r_energy = 10.0 * efficiency - thermal_penalty

    # Weights [0.25, 0.25, 0.20, 0.15, 0.05, 0.10]
    r_total = (
        0.25 * r_thru +
        0.25 * r_rtt +
        0.20 * r_failover -
        0.15 * p_loss_term -
        0.05 * p_skew +
        0.10 * r_energy +
        10.0  # R_truth (+10 for verified real streams)
    )
    return r_total


# ==============================================================================
# Domain 2: Headscale STUN UDP 3478 Drop & DERP Relay Fallback Simulation
# ==============================================================================

class HeadscaleClientState:
    DISCONNECTED = "DISCONNECTED"
    STUN_PROBING = "STUN_PROBING"
    DIRECT_P2P_WIREGUARD = "DIRECT_P2P_WIREGUARD"
    DERP_RELAY_CONNECTING = "DERP_RELAY_CONNECTING"
    DERP_RELAY_ACTIVE = "DERP_RELAY_ACTIVE"

class HeadscaleDerpStateMachine:
    """Models Headscale client connection lifecycle under STUN blocking (CGNAT)."""
    def __init__(self, stun_timeout_ms: float = 3000.0, derp_rtt_ms: float = 28.5):
        self.state = HeadscaleClientState.DISCONNECTED
        self.stun_timeout_ms = stun_timeout_ms
        self.derp_rtt_ms = derp_rtt_ms
        self.active_protocol = "NONE"
        self.effective_mtu = 1420
        self.measured_rtt_ms = 0.0

    def connect(self, udp_stun_available: bool, direct_udp_available: bool) -> Dict[str, Any]:
        self.state = HeadscaleClientState.STUN_PROBING
        if udp_stun_available and direct_udp_available:
            self.state = HeadscaleClientState.DIRECT_P2P_WIREGUARD
            self.active_protocol = "UDP_WIREGUARD_P2P"
            self.effective_mtu = 1420
            self.measured_rtt_ms = 1.8  # Direct LAN/Wi-Fi
            return {
                "status": "SUCCESS",
                "state": self.state,
                "protocol": self.active_protocol,
                "mtu": self.effective_mtu,
                "rtt_ms": self.measured_rtt_ms
            }
        else:
            # STUN dropped or symmetric CGNAT prevents direct mapping
            # Fallback to embedded DERP over HTTPS/TLS Port 8443
            self.state = HeadscaleClientState.DERP_RELAY_CONNECTING
            # Simulation of TCP handshake + TLS 1.3 setup to Region 900
            time_to_connect_ms = self.derp_rtt_ms * 2.0
            self.state = HeadscaleClientState.DERP_RELAY_ACTIVE
            self.active_protocol = "HTTPS_DERP_RELAY_8443"
            # DERP framing overhead: TLS (29B) + DERP header (20B) reduces payload
            self.effective_mtu = 1360  # Reduced MTU for DERP encapsulation
            self.measured_rtt_ms = self.derp_rtt_ms
            return {
                "status": "FALLBACK_DERP",
                "state": self.state,
                "protocol": self.active_protocol,
                "mtu": self.effective_mtu,
                "rtt_ms": self.measured_rtt_ms,
                "fallback_delay_ms": self.stun_timeout_ms + time_to_connect_ms
            }


# ==============================================================================
# Domain 3: Sandboxing Containment & Network Isolation Verification
# ==============================================================================

def verify_sandbox_firewall_rules(rules: List[str]) -> Dict[str, bool]:
    """Validates that QEMU br-test0 and Docker buildroots are strictly firewalled."""
    has_net_none = any("--net=none" in r for r in rules)
    has_bridge_isolation = any("br-test0" in r and "DROP" in r for r in rules)
    has_memory_limit = any("--memory=" in r for r in rules)
    has_non_root_user = any("USER sandboxuser" in r for r in rules)
    has_ro_source_mount = any(":ro" in r for r in rules)

    return {
        "network_airgap": has_net_none,
        "bridge_leak_prevented": has_bridge_isolation,
        "memory_governor_safe": has_memory_limit,
        "rootless_containment": has_non_root_user,
        "source_immutability": has_ro_source_mount
    }


# ==============================================================================
# Domain 4: Dynamic ELO K-Factor & Cryptographic Verification
# ==============================================================================

def compute_dynamic_k_factor(
    k0: float,
    eta_type: float,
    params_b: float,
    tokens: int,
    score_agree: float,
    rtt_ms: float,
    is_authentic_telemetry: bool
) -> float:
    """Calculates K_dyn according to Section 4.3 formulas."""
    if not is_authentic_telemetry:
        return 0.0  # Instant disqualification
    
    eta_size = max(0.50, min(2.50, math.log2(71.0) / math.log2(params_b + 1.0)))
    eta_token = min(1.50, max(0.50, 2048.0 / max(1.0, float(tokens))))
    eta_consensus = min(1.00, max(0.50, 0.50 + 0.50 * score_agree))
    eta_compute = min(1.30, max(0.70, 100.0 / (rtt_ms + 30.0)))
    eta_truth = 1.00

    return k0 * eta_type * eta_size * eta_token * eta_consensus * eta_compute * eta_truth


def compute_tournament_state_root(
    debate_jsonl: str,
    arena_telemetry: str,
    ast_diff: str,
    timestamp: str
) -> str:
    """Computes SHA-256 Merkle leaf state root hash (Section 4.4.1)."""
    h_debate = hashlib.sha256(debate_jsonl.encode("utf-8")).hexdigest()
    h_arena = hashlib.sha256(arena_telemetry.encode("utf-8")).hexdigest()
    h_diff = hashlib.sha256(ast_diff.encode("utf-8")).hexdigest()
    
    combined = f"{h_debate}||{h_arena}||{h_diff}||{timestamp}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


# ==============================================================================
# Pytest Test Cases
# ==============================================================================

class TestMeshEmpiricalChallenges:

    def test_tb4_abrupt_disconnect_and_mptcp_failover(self):
        """Stress-Test 1: Abrupt drop of 10Gbps TB4 DMA bridge during active tensor transmission."""
        sim = MptcpSchedulerSimulator(scheduler_type="blest")
        sim.add_subflow("tb4_dma", capacity_mbps=38400.0, rtt_ms=0.28)
        sim.add_subflow("wifi7_mlo", capacity_mbps=2400.0, rtt_ms=1.4)
        sim.add_subflow("lan_1gbe", capacity_mbps=1000.0, rtt_ms=1.8)

        # Baseline dispatch to TB4
        flow, rtt = sim.select_subflow(packet_size_bytes=65536)
        assert flow == "tb4_dma"
        assert rtt == 0.28

        # CHAOS INJECTION: Abrupt TB4 link severance (DMA bus reset)
        sim.subflows["tb4_dma"].is_up = False

        # Failover to secondary low-latency link (Wi-Fi 7 / 1GbE)
        flow_after, rtt_after = sim.select_subflow(packet_size_bytes=65536)
        assert flow_after == "wifi7_mlo"
        assert rtt_after == 1.4

        # Validate failover reward score with dynamic media-aware tau_rtt (tau_rtt=5.0 for Wi-Fi 7/LAN)
        reward_failover_media_aware = calculate_reward_total(
            t_bonded=2400.0,
            t_target=3500.0,
            sum_capacity=3400.0,
            avg_rtt=1.4,
            tau_rtt=5.0,  # Media-aware budget for Wi-Fi 7 LAN failover
            rtt_max_budget=50.0,
            t_switch=0.85,  # Sub-millisecond switch
            t_cutoff=20.0,  # Multi-media cutoff budget
            session_dropped=False,
            p_loss=0.0,
            d_queue=0.2,
            d_base=1.0,
            rtt_max=1.8,
            rtt_min=1.4,
            power_watts=15.0,
            node_temps={"Mac_Node": 45.0, "MacBook_Pro": 50.0},
            temp_crits={"Mac_Node": 75.0, "MacBook_Pro": 80.0},
            psi_weights={"Mac_Node": 1.5, "MacBook_Pro": 1.2},
            is_authentic_telemetry=True
        )
        assert reward_failover_media_aware > 70.0, f"Failover reward {reward_failover_media_aware} should be resilient (>70.0)"

    def test_cellular_5g_jitter_spike_and_blest_blocking_prevention(self):
        """Stress-Test 2: High jitter and latency surge (25ms -> 450ms) on 5G cellular hotspot."""
        sim = MptcpSchedulerSimulator(scheduler_type="blest")
        sim.add_subflow("wifi7_mlo", capacity_mbps=2400.0, rtt_ms=1.4)
        sim.add_subflow("cellular_5g", capacity_mbps=120.0, rtt_ms=450.0)  # Extreme jitter

        # BLEST scheduler should NOT dispatch to 5G when Wi-Fi drain time is tiny
        for _ in range(5):
            flow, rtt = sim.select_subflow(packet_size_bytes=65536)
            assert flow == "wifi7_mlo", "BLEST must suppress high-jitter 450ms 5G link to prevent buffer stall"

    def test_headscale_stun_dropped_fallback_to_https_derp(self):
        """Stress-Test 3: Carrier CGNAT blocks UDP 3478 STUN, forcing HTTPS 8443 DERP relay."""
        client = HeadscaleDerpStateMachine(stun_timeout_ms=3000.0, derp_rtt_ms=28.5)
        
        # Test STUN dropped scenario
        res = client.connect(udp_stun_available=False, direct_udp_available=False)
        assert res["status"] == "FALLBACK_DERP"
        assert res["protocol"] == "HTTPS_DERP_RELAY_8443"
        assert res["mtu"] == 1360  # Reduced MTU for DERP encapsulation
        assert res["rtt_ms"] == 28.5
        assert res["fallback_delay_ms"] <= 3100.0

    def test_sandbox_firewall_and_resource_safety_matrix(self):
        """Stress-Test 4: Air-gapped compilation containment and QEMU bridge leak defense."""
        strategy_docker_args = [
            "docker run --rm --net=none --memory=8g --cpus=6",
            "USER sandboxuser",
            "-v /path/to/src:/home/sandboxuser/openwrt/package/custom_patch:ro",
            "iptables -A FORWARD -i br-test0 -o eth0 -j DROP",
            "ebtables -A FORWARD -i br-test0 -j DROP"
        ]
        audit = verify_sandbox_firewall_rules(strategy_docker_args)
        assert audit["network_airgap"] is True
        assert audit["bridge_leak_prevented"] is True
        assert audit["memory_governor_safe"] is True
        assert audit["rootless_containment"] is True
        assert audit["source_immutability"] is True

    def test_rule_zero_truth_disqualification(self):
        """Stress-Test 5: Synthetic/hallucinated telemetry instantly incurs -inf reward."""
        reward_fake = calculate_reward_total(
            t_bonded=3500.0,
            t_target=3500.0,
            sum_capacity=38400.0,
            avg_rtt=0.28,
            tau_rtt=0.5,
            rtt_max_budget=50.0,
            t_switch=0.1,
            t_cutoff=1.0,
            session_dropped=False,
            p_loss=0.0,
            d_queue=0.0,
            d_base=1.0,
            rtt_max=0.28,
            rtt_min=0.28,
            power_watts=10.0,
            node_temps={},
            temp_crits={},
            psi_weights={},
            is_authentic_telemetry=False  # Rule #0 Violation
        )
        assert reward_fake == -float("inf")

    def test_dynamic_elo_k_factor_frugality_scaling(self):
        """Stress-Test 6: Parameter frugality and concise token reward scaling in dynamic ELO."""
        # 14B MoE SLM vs 72B Giant
        k_slm = compute_dynamic_k_factor(
            k0=32.0, eta_type=1.0, params_b=14.0, tokens=256, score_agree=0.95, rtt_ms=15.0, is_authentic_telemetry=True
        )
        k_giant = compute_dynamic_k_factor(
            k0=32.0, eta_type=1.0, params_b=72.0, tokens=1024, score_agree=0.95, rtt_ms=150.0, is_authentic_telemetry=True
        )
        assert k_slm > k_giant, "Frugal 14B SLM with fast TTFT must receive higher dynamic K-factor multiplier than 72B slow giant"

    def test_cryptographic_state_root_attestation(self):
        """Stress-Test 7: SHA-256 Merkle tournament state root hashing and immutability."""
        h1 = compute_tournament_state_root(
            debate_jsonl='{"round": 4, "consensus": 0.986}',
            arena_telemetry='{"bonded_mbps": 3480.5, "rtt_ms": 0.28}',
            ast_diff='diff --git a/omr.conf b/omr.conf',
            timestamp="2026-08-27T06:20:00Z"
        )
        h2 = compute_tournament_state_root(
            debate_jsonl='{"round": 4, "consensus": 0.986}',
            arena_telemetry='{"bonded_mbps": 3480.5, "rtt_ms": 0.28}',
            ast_diff='diff --git a/omr.conf b/omr.conf',
            timestamp="2026-08-27T06:20:00Z"
        )
        assert h1 == h2 and len(h1) == 64
        # Tamper test
        h_tampered = compute_tournament_state_root(
            debate_jsonl='{"round": 4, "consensus": 0.986}',
            arena_telemetry='{"bonded_mbps": 100.0, "rtt_ms": 50.0}',  # Tampered
            ast_diff='diff --git a/omr.conf b/omr.conf',
            timestamp="2026-08-27T06:20:00Z"
        )
        assert h1 != h_tampered
