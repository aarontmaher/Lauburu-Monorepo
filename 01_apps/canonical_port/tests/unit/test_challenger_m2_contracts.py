"""
Adversarial & Empirical Challenger Verification Suite for Milestone 2 (M2)
Tests Ground-Up Stability Contracts, Data Integrity, Roundtrips, and Edge Cases
"""

import os
import sys
import json
import yaml
import time
import socket
import tempfile
import threading
import pytest
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))
from models.blackboard_models import (
    BlackboardTelemetryState,
    BlackboardProvenance,
    Layer0NetworkingState,
    Layer1HardwareState,
    Layer2BiometricsState,
    Layer3AiInferenceState,
    Layer4TrainingGamesState,
    Layer5GovernanceState,
    Layer6ToolingSkillsState,
    WolTarget,
    BluetoothPanLink,
    KdeConnectState,
    Tb4DmaInterconnect,
    WanRoute,
    TailscalePeer,
    HardwareNodeState,
    ObsidianVaultState,
    PySparkLakeState,
    GitHubTreeState,
    TriVaultStorageState,
    MovesenseStreamState,
    KamathFilterState,
    PttBloodPressure,
    ImuKinematicsState,
    GrapplingMapState,
    LlamaRpcNode,
    InferenceModelInfo,
    PetalsSwarmState,
    ExoP2PState,
    LoraDatasetInfo,
    LossDecayPoint,
    FfaArenaAgent,
    PySparkAstMetrics,
    TriOrchestratorDebateState,
    EloLeaderboardEntry,
    SwarmActionCommand,
    McpServerInfo,
    SdkInfo,
    CliToolInfo,
    AgentSkillInfo,
    ShopifyCommerceState
)
from services.blackboard_store import BlackboardStore


# ============================================================================
# CONTRACT 1: LAYER 0 NETWORKING CONTRACT VERIFICATION
# ============================================================================

def test_contract_layer_0_wol_mac_targets():
    """Verify Layer 0 WoL targets: exactly 5 targets with valid MACs and IPs."""
    state = BlackboardTelemetryState.create_canonical_default()
    l0 = state.layer_0_networking

    assert len(l0.wol_targets) == 5, f"Expected 5 WoL targets, got {len(l0.wol_targets)}"
    target_names = {t.name for t in l0.wol_targets}
    expected_names = {
        "L1_Mac_Mini_Host",
        "L2_MacBook_Pro_Vault",
        "L3_Linux_Head_Node",
        "L4_Linux_Tablet",
        "L5_MacBook_Air"
    }
    assert target_names == expected_names, f"WoL names mismatch: {target_names ^ expected_names}"

    for target in l0.wol_targets:
        assert target.port in (9, 7), f"Target {target.name} has invalid port: {target.port}"
        assert target.status in ("ONLINE", "STANDBY", "OFFLINE")
        # Validate MAC format (6 octets)
        octets = target.mac.split(":")
        assert len(octets) == 6, f"Invalid MAC format in {target.name}: {target.mac}"
        for octet in octets:
            assert len(octet) == 2 and all(c in "0123456789abcdefABCDEF" for c in octet)
        # Validate IPv4 format
        ip_parts = target.ip.split(".")
        assert len(ip_parts) == 4, f"Invalid IP format in {target.name}: {target.ip}"
        for part in ip_parts:
            assert 0 <= int(part) <= 255


def test_contract_layer_0_bluetooth_pan():
    """Verify Layer 0 Bluetooth PAN BNEP Proximity Link."""
    state = BlackboardTelemetryState.create_canonical_default()
    bt = state.layer_0_networking.bluetooth_pan

    assert bt.interface == "bnep0"
    assert bt.status in ("ONLINE", "DISCONNECTED", "OFFLINE")
    assert bt.rtt_ms == 0.03
    assert bt.bandwidth == "3.0 MB/s"
    assert bt.paired_devices == 7
    assert bt.profile == "BNEP/PANU"


def test_contract_layer_0_kde_connect():
    """Verify Layer 0 KDE Connect LAN routing."""
    state = BlackboardTelemetryState.create_canonical_default()
    kde = state.layer_0_networking.kde_connect

    assert kde.status == "ACTIVE"
    assert kde.port_udp == 1716
    assert kde.port_tcp_range == "1714-1764"
    assert kde.paired_nodes == 7
    assert kde.rtt_ms == 0.94
    assert kde.bandwidth_mb_s == 90.0
    assert kde.tls_encrypted is True


def test_contract_layer_0_tb4_dma_interconnect():
    """Verify Layer 0 Thunderbolt 4 PCIe DMA Bridge (0.28ms RTT, 38.4 Gbps)."""
    state = BlackboardTelemetryState.create_canonical_default()
    tb4 = state.layer_0_networking.tb4_dma

    assert tb4.ip == "169.254.187.138"
    assert tb4.status in ("CONNECTED", "OFFLINE", "DEGRADED")
    assert round(tb4.rtt_ms, 2) == 0.28 or tb4.rtt_ms == 0.277
    assert tb4.throughput_gbps == 38.4
    assert tb4.interface == "bridge0 / tb0"
    assert tb4.zero_copy_active is True


def test_contract_layer_0_multi_wan_ewma_matrix():
    """Verify Layer 0 10-Route Multi-WAN matrix and EWMA parameters."""
    state = BlackboardTelemetryState.create_canonical_default()
    l0 = state.layer_0_networking

    assert len(l0.wan_routes) == 10, f"Expected 10 WAN routes, got {len(l0.wan_routes)}"
    assert l0.ewma_alpha == 0.35
    assert l0.circuit_breaker_trip_threshold == 0.284

    ifaces = [r.interface for r in l0.wan_routes]
    expected_ifaces = [
        "en0_wifi_wan",
        "utun1_tailscale",
        "en6_usb_tether",
        "cloudflare_quic",
        "p01_tb4_dma",
        "p02_10gbe",
        "p03_usb32_adb",
        "p05_wifi_direct",
        "p08_kde_localsend",
        "p15_ble_pan"
    ]
    assert ifaces == expected_ifaces, f"WAN routes mismatch:\nExpected: {expected_ifaces}\nGot: {ifaces}"

    for r in l0.wan_routes:
        assert r.status in ("ACTIVE", "STANDBY", "DEGRADED", "OFFLINE")
        assert r.circuit_state in ("CLOSED", "OPEN", "HALF_OPEN")
        assert r.priority in ("P0", "P1", "P2", "P3", "P4")
        assert r.category in ("WAN", "MESH", "LOCAL", "P2P")
        if r.rtt_ms is not None:
            assert r.rtt_ms >= 0.0


def test_contract_layer_0_tailscale_peers():
    """Verify Layer 0 Tailscale 7-node WireGuard overlay peers."""
    state = BlackboardTelemetryState.create_canonical_default()
    l0 = state.layer_0_networking

    assert len(l0.tailscale_peers) == 7, f"Expected 7 Tailscale peers, got {len(l0.tailscale_peers)}"
    peers_by_name = {p.node_name: p for p in l0.tailscale_peers}

    expected_peers = {
        "Mac_Node": ("100.119.199.76", "L1"),
        "MacBook_Pro": ("100.103.212.21", "L2"),
        "Linux_Head_Node": ("100.101.39.98", "L3"),
        "Linux_Tablet": ("100.81.92.125", "L4"),
        "MacBook_Air": ("100.93.158.96", "L5"),
        "Pixel_10_Pro_XL": ("100.73.38.87", "L6"),
        "Samsung_S20": ("100.84.40.95", "L7"),
    }

    for name, (expected_ip, expected_layer) in expected_peers.items():
        assert name in peers_by_name, f"Missing Tailscale peer: {name}"
        peer = peers_by_name[name]
        assert peer.ip == expected_ip, f"Peer {name} IP mismatch: expected {expected_ip}, got {peer.ip}"
        assert peer.layer == expected_layer, f"Peer {name} Layer mismatch: expected {expected_layer}, got {peer.layer}"
        assert peer.status in ("ONLINE", "IDLE", "OFFLINE")
        assert peer.relay in ("Direct WireGuard", "DERP Relay")


# ============================================================================
# CONTRACT 2: LAYER 1 HARDWARE & VRAM POOLING VERIFICATION
# ============================================================================

def test_contract_layer_1_hardware_nodes_and_memory_pools():
    """Verify Layer 1: 7 physical nodes (L1-L7) + GW totalling 108.0 GB RAM and 82.8 GB VRAM."""
    state = BlackboardTelemetryState.create_canonical_default()
    l1 = state.layer_1_hardware

    assert len(l1.nodes) == 8, f"Expected 8 nodes (7 physical + 1 GW), got {len(l1.nodes)}"

    # Sum up 7 physical nodes L1 through L7
    physical_nodes = [n for n in l1.nodes if n.node_id != "GW"]
    assert len(physical_nodes) == 7, f"Expected 7 physical nodes, got {len(physical_nodes)}"

    sum_ram = sum(n.ram_total_gb for n in physical_nodes)
    assert round(sum_ram, 1) == 108.0, f"Sum of RAM for L1-L7: expected 108.0 GB, got {sum_ram}"

    # Verify canonical aggregate pool fields
    assert l1.total_ram_gb == 108.0
    assert l1.total_vram_gb == 82.8
    assert l1.pooled_ram_used_gb == 48.2
    assert l1.pooled_vram_used_gb == 39.0
    assert l1.memory_governor_active is True

    # Node-by-node verification against the canonical hardware matrix
    node_map = {n.node_id: n for n in l1.nodes}
    expected_hardware = {
        "L1": {"name": "Mac_Node", "ram": 24.0, "vram": 21.6, "cap": 90.0, "arch": "ARM64"},
        "L2": {"name": "MacBook_Pro", "ram": 16.0, "vram": 14.0, "cap": 90.0, "arch": "x86_64"},
        "L3": {"name": "Linux_Head_Node", "ram": 16.0, "vram": 13.8, "cap": 80.0, "arch": "x86_64"},
        "L4": {"name": "Linux_Tablet", "ram": 8.0, "vram": 6.5, "cap": 75.0, "arch": "ARM64"},
        "L5": {"name": "MacBook_Air", "ram": 16.0, "vram": 14.0, "cap": 90.0, "arch": "ARM64"},
        "L6": {"name": "Pixel_10_Pro_XL", "ram": 16.0, "vram": 12.5, "cap": 85.0, "arch": "ARM64"},
        "L7": {"name": "Samsung_S20", "ram": 12.0, "vram": 9.0, "cap": 75.0, "arch": "ARM64"},
        "GW": {"name": "GL.iNet Router", "ram": 0.5, "vram": 0.0, "cap": 100.0, "arch": "MIPS/ARM"}
    }

    for nid, exp in expected_hardware.items():
        assert nid in node_map, f"Missing node {nid}"
        node = node_map[nid]
        assert node.name == exp["name"]
        assert node.ram_total_gb == exp["ram"]
        assert node.vram_cap_gb == exp["vram"]
        assert node.dynamic_cap_pct == exp["cap"]
        assert node.arch == exp["arch"]


def test_contract_layer_1_trivault_storage_invariants():
    """Verify Layer 1 Tri-Vault storage health invariants."""
    state = BlackboardTelemetryState.create_canonical_default()
    storage = state.layer_1_hardware.storage_health

    assert storage.obsidian_vault.path == "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
    assert storage.obsidian_vault.healthy is True
    assert storage.obsidian_vault.permissions == "0755/0644"

    assert storage.pyspark_lake.path == "/Users/aaron/DFS_UNIFIED/lora_datasets"
    assert storage.pyspark_lake.healthy is True
    assert storage.pyspark_lake.headroom_threshold_gb == 10.0

    assert storage.github_tree.path == "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
    assert storage.github_tree.healthy is True
    assert storage.github_tree.index_locked is False

    assert storage.all_healthy is True


# ============================================================================
# CONTRACT 3: LAYER 2 BIOMETRICS & KINEMATICS VERIFICATION
# ============================================================================

def test_contract_layer_2_biometrics_and_kinematics():
    """Verify Layer 2: Movesense 512Hz ECG, Kamath filter, RMSSD, DFA-alpha1 0.75, 31 OPML Grappling nodes."""
    state = BlackboardTelemetryState.create_canonical_default()
    l2 = state.layer_2_biometrics

    # 1. Movesense 512Hz ECG
    assert l2.movesense_stream.connected is True
    assert l2.movesense_stream.sampling_rate_hz == 512, f"Expected 512Hz, got {l2.movesense_stream.sampling_rate_hz}"
    assert l2.movesense_stream.sensor_id == "Movesense-Medical-230950000"
    assert l2.movesense_stream.profile == "zone2"
    assert l2.movesense_stream.medical_class == "Class IIa"
    assert l2.movesense_stream.ecg_snr_db == 28.5

    # 2. Kamath 20% Filter
    assert l2.kamath_filter.filter_name == "Kamath 20% Clinical RR Filter"
    assert l2.kamath_filter.threshold_pct == 20.0
    assert l2.kamath_filter.is_active is True
    assert l2.kamath_filter.rejection_rate_pct == 1.42

    # 3. RMSSD and Heart Rate
    assert l2.heart_rate_bpm == 138.4
    assert len(l2.rr_intervals_ms) == 5
    assert l2.rmssd_ms == 42.8

    # 4. DFA-alpha1 0.75 Target
    assert l2.dfa_alpha1 == 0.75, f"Expected DFA-alpha1 == 0.75, got {l2.dfa_alpha1}"
    assert l2.zone2_status == "ZONE_2_OPTIMAL"
    assert l2.vo2_max_ml_kg_min == 52.4

    # 5. PTT Blood Pressure & IMU Kinematics
    assert l2.ptt_blood_pressure.systolic_mmhg == 118
    assert l2.ptt_blood_pressure.diastolic_mmhg == 76
    assert l2.ptt_blood_pressure.pulse_transit_time_ms == 212.4
    assert l2.imu_kinematics.cadence_spm == 164
    assert l2.imu_kinematics.mechanical_power_watts == 182.4

    # 6. 31 OPML Grappling Nodes
    assert l2.grappling_map.total_nodes == 31, f"Expected 31 OPML nodes, got {l2.grappling_map.total_nodes}"
    assert l2.grappling_map.total_transitions == 57
    assert l2.grappling_map.active_position == "Side Control"
    assert len(l2.grappling_map.tactical_categories) == 8
    assert len(l2.grappling_map.recent_submissions) == 5


# ============================================================================
# CONTRACT 4: LAYER 4 TRAINING & PYSPARK AST VERIFICATION
# ============================================================================

def test_contract_layer_4_lora_datasets_and_pyspark_ast():
    """Verify Layer 4: 23 LoRA datasets, PySpark AST stats (32 projects, 3104 files, 434965 LOC)."""
    state = BlackboardTelemetryState.create_canonical_default()
    l4 = state.layer_4_training_games

    # 1. 23 LoRA Datasets
    assert l4.total_datasets_count == 23, f"Expected 23 datasets count, got {l4.total_datasets_count}"
    assert len(l4.lora_datasets) == 23, f"Expected 23 dataset items, got {len(l4.lora_datasets)}"

    expected_datasets = [
        "all_local_ais_lora_burst_dataset.jsonl",
        "architectural_decisions.jsonl",
        "autonomous_consensus_iterations.jsonl",
        "biometrics_sleep_lora_dataset.jsonl",
        "continuous_lora_dataset.jsonl",
        "cot_distillation_generation_1786654798.jsonl",
        "device_doctor_telemetry.jsonl",
        "gemma_nano_training_dataset.jsonl",
        "genetic_ml_dataset_latest.jsonl",
        "genetic_smol_lora_training.jsonl",
        "healing_incidents.jsonl",
        "lauburu_chat_conversations.jsonl",
        "mesh_battle_game_training.jsonl",
        "model_merge_benchmarks.jsonl",
        "movesense_biometrics_coaching.jsonl",
        "on_device_nano_smol_training.jsonl",
        "quarantined_hallucinations.jsonl",
        "self_evolving_analysis_chains.jsonl",
        "shadow_coding_distillation.jsonl",
        "swarm_codebase_refactors.jsonl",
        "truth_audit_debate.jsonl",
        "truthfulness_retraining_dataset.jsonl",
        "ui_ux_improvements.jsonl"
    ]
    dataset_names = [d.name for d in l4.lora_datasets]
    assert dataset_names == expected_datasets, f"LoRA dataset names mismatch"

    for d in l4.lora_datasets:
        assert d.pairs_count > 0
        assert d.category in ("SFT", "DPO")
        assert d.path.startswith("12_continuous_lora_evolution/lora_datasets/")

    # 2. PySpark AST Stats
    ast = l4.pyspark_ast_metrics
    assert ast.total_projects == 32, f"Expected 32 projects, got {ast.total_projects}"
    assert ast.total_code_files == 3104, f"Expected 3104 code files, got {ast.total_code_files}"
    assert ast.total_loc == 434965, f"Expected 434965 LOC, got {ast.total_loc}"
    assert ast.total_test_suites == 325, f"Expected 325 test suites, got {ast.total_test_suites}"
    assert ast.total_ast_nodes == 124491, f"Expected 124491 AST nodes, got {ast.total_ast_nodes}"

    # 3. Training & FFA Arena
    assert l4.initial_loss == 2.18
    assert l4.current_loss == 0.142
    assert l4.training_step == 4800
    assert len(l4.loss_history) == 7
    assert len(l4.ffa_arena_agents) == 13


# ============================================================================
# STRESS, ROUNDTRIP, NULL GUARD, AND CORRUPTION TESTS
# ============================================================================

def test_stress_full_roundtrip_fidelity():
    """Verify full round-trip Dict -> JSON -> Dataclass -> YAML -> Dataclass preserves 100% precision."""
    orig = BlackboardTelemetryState.create_canonical_default()

    # Step 1: Dataclass -> Dict
    d = orig.to_dict()
    # Step 2: Dict -> JSON
    j = json.dumps(d)
    # Step 3: JSON -> Dataclass
    r1 = BlackboardTelemetryState.from_json(j)
    # Step 4: Dataclass -> YAML
    y = r1.to_yaml()
    # Step 5: YAML -> Dataclass
    r2 = BlackboardTelemetryState.from_yaml(y)

    assert r2.version == orig.version
    assert len(r2.layer_0_networking.wol_targets) == 5
    assert len(r2.layer_0_networking.wan_routes) == 10
    assert len(r2.layer_0_networking.tailscale_peers) == 7
    assert r2.layer_1_hardware.total_ram_gb == 108.0
    assert r2.layer_1_hardware.total_vram_gb == 82.8
    assert r2.layer_2_biometrics.movesense_stream.sampling_rate_hz == 512
    assert r2.layer_2_biometrics.dfa_alpha1 == 0.75
    assert r2.layer_2_biometrics.grappling_map.total_nodes == 31
    assert r2.layer_4_training_games.total_datasets_count == 23
    assert r2.layer_4_training_games.pyspark_ast_metrics.total_projects == 32
    assert r2.layer_4_training_games.pyspark_ast_metrics.total_code_files == 3104
    assert r2.layer_4_training_games.pyspark_ast_metrics.total_loc == 434965


def test_stress_null_guard_and_offline_states():
    """Verify dataclasses gracefully handle None / null values in all optional fields (Rule #0 zero-mock)."""
    node = HardwareNodeState(
        node_id="L1", name="Test_Node", model="Test", arch="ARM64", os="macOS",
        role="Test", ip="127.0.0.1", tailscale_ip="100.0.0.1", status="OFFLINE",
        ram_total_gb=16.0, ram_used_gb=0.0, ram_usage_pct=0.0, vram_cap_gb=14.0,
        vram_used_gb=0.0, dynamic_cap_pct=90.0, cpu_usage_pct=0.0, cpu_cores=8,
        load_1m=0.0, load_5m=0.0, load_15m=0.0, thermal_c=0.0, thermal_status="NOMINAL",
        battery_pct=None, is_charging=False, power_source="AC", qi_power_watts=0.0, storage_free_gb=0.0
    )
    assert node.battery_pct is None

    bio = Layer2BiometricsState(
        heart_rate_bpm=None,
        rmssd_ms=None,
        dfa_alpha1=None,
        vo2_max_ml_kg_min=None,
        ptt_blood_pressure=PttBloodPressure(systolic_mmhg=None, diastolic_mmhg=None, pulse_transit_time_ms=None)
    )
    assert bio.heart_rate_bpm is None
    assert bio.rmssd_ms is None
    assert bio.dfa_alpha1 is None
    assert bio.ptt_blood_pressure.systolic_mmhg is None

    # Serialization test with None fields
    d = bio.to_dict()
    assert d["heart_rate_bpm"] is None
    restored = Layer2BiometricsState.from_dict(d)
    assert restored.heart_rate_bpm is None


def test_stress_malformed_json_fallback_and_recovery():
    """Verify BlackboardStore gracefully recovers from corrupted disk files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)

        # Write invalid/corrupt JSON to disk
        json_path = os.path.join(tmpdir, "blackboard_state.json")
        with open(json_path, "w") as f:
            f.write("{ INVALID JSON CORRUPT CONTENT [[")

        # load_from_disk should return None and not crash
        loaded = store.load_from_disk()
        assert loaded is None

        # get_snapshot should fall back to canonical default
        snap = store.get_snapshot()
        assert snap is not None
        assert snap.version == "3.0.0-CANONICAL"
        assert len(snap.layer_0_networking.wol_targets) == 5


def test_stress_concurrent_read_write_heavy():
    """Fast concurrent stress test without socket probing latency: worker threads hammering BlackboardStore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, cache_ttl_seconds=10.0, auto_persist=True)
        errors = []

        def reader():
            try:
                for _ in range(50):
                    snap = store.get_snapshot(force_refresh=False)
                    assert snap.version == "3.0.0-CANONICAL"
                    raw = store.get_raw_state_for_agi()
                    assert "layer_0_networking" in raw
                    assert "layer_4_training_games" in raw
            except Exception as e:
                errors.append(e)

        def writer(idx):
            try:
                for i in range(25):
                    data = store.get_snapshot(force_refresh=False).layer_4_training_games.to_dict()
                    data["current_loss"] = round(0.142 + (idx * 0.001) + (i * 0.0001), 4)
                    store.update_layer("layer_4", data)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(8)] + \
                  [threading.Thread(target=writer, args=(i,)) for i in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered errors during concurrent stress: {errors}"
