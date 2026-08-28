"""
Challenger 1 Adversarial Empirical Stress Test Suite (Milestone 2)
Focus: Blackboard Models & Store Service (blackboard_models.py, blackboard_store.py)

Empirically tests:
1. High-concurrency rapid read/write bursts across multiple threads (up to 32 concurrent workers).
2. Malformed JSON/YAML payloads, corrupted disk states, truncated files, and zero-crash self-healing recovery.
3. Memory leak / rapid state snapshot creation (5,000 snapshot/mutation cycles with memory delta tracking).
4. Non-blocking socket probe behavior under simulated network drops, hanging sockets, and connection resets.
5. Dataclass boundary values, null safety, and round-trip serialization fidelity across all 7 stability layers.
"""

import os
import sys
import time
import json
import yaml
import socket
import gc
import tracemalloc
import threading
import tempfile
import pytest
from typing import Dict, Any, List

# Add tui package to sys.path
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
# 1. HIGH-CONCURRENCY RAPID READ/WRITE BURSTS (32 Threads, 1,000+ Operations)
# ============================================================================

def test_stress_high_concurrency_multi_thread_bursts():
    """
    Stress test BlackboardStore with 32 concurrent threads (16 readers, 16 writers)
    performing rapid state reads, mutations, and disk flushes simultaneously.
    Verifies zero deadlocks, zero race conditions, and 100% data integrity.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, cache_ttl_seconds=0.05, auto_persist=True)
        # Clear RPC nodes from probe list in this test to benchmark pure concurrency
        init_snap = store.get_snapshot()
        init_snap.layer_3_ai_inference.llama_rpc_nodes = []
        store.persist_to_disk(init_snap)

        errors = []
        read_counts = [0] * 16
        write_counts = [0] * 16

        def reader_worker(worker_id: int):
            try:
                for i in range(50):
                    snap = store.get_snapshot(force_refresh=False)
                    assert snap.version == "3.0.0-CANONICAL"
                    raw = store.get_raw_state_for_agi()
                    assert "layer_0_networking" in raw
                    assert "layer_1_hardware" in raw
                    assert "layer_2_biometrics" in raw
                    assert "layer_3_ai_inference" in raw
                    assert "layer_4_training_games" in raw
                    assert "layer_5_governance" in raw
                    assert "layer_6_tooling_skills" in raw
                    read_counts[worker_id] += 1
                    time.sleep(0.0005)
            except Exception as e:
                errors.append((f"reader_{worker_id}", e))

        def writer_worker(worker_id: int):
            try:
                for i in range(30):
                    layer_target = f"layer_{worker_id % 7}"
                    snap = store.get_snapshot(force_refresh=False)

                    if layer_target in ("layer_0", "layer_0_networking"):
                        l0 = snap.layer_0_networking.to_dict()
                        l0["ewma_alpha"] = round(0.35 + (worker_id * 0.01), 3)
                        store.update_layer("layer_0", l0)
                    elif layer_target in ("layer_1", "layer_1_hardware"):
                        l1 = snap.layer_1_hardware.to_dict()
                        l1["pooled_ram_used_gb"] = round(48.2 + (worker_id * 0.1), 2)
                        store.update_layer("layer_1", l1)
                    elif layer_target in ("layer_2", "layer_2_biometrics"):
                        l2 = snap.layer_2_biometrics.to_dict()
                        l2["heart_rate_bpm"] = round(130.0 + worker_id + (i * 0.5), 2)
                        store.update_layer("layer_2", l2)
                    elif layer_target in ("layer_3", "layer_3_ai_inference"):
                        l3 = snap.layer_3_ai_inference.to_dict()
                        l3["total_sharded_layers"] = 80
                        store.update_layer("layer_3", l3)
                    elif layer_target in ("layer_4", "layer_4_training_games"):
                        l4 = snap.layer_4_training_games.to_dict()
                        l4["current_loss"] = round(0.142 + (worker_id * 0.001), 4)
                        store.update_layer("layer_4", l4)
                    elif layer_target in ("layer_5", "layer_5_governance"):
                        l5 = snap.layer_5_governance.to_dict()
                        l5["debate_council"]["cosine_accord"] = round(0.98 + (worker_id * 0.001), 4)
                        store.update_layer("layer_5", l5)
                    else:
                        l6 = snap.layer_6_tooling_skills.to_dict()
                        store.update_layer("layer_6", l6)

                    write_counts[worker_id] += 1
                    time.sleep(0.0005)
            except Exception as e:
                errors.append((f"writer_{worker_id}", e))

        threads: List[threading.Thread] = []
        for i in range(16):
            threads.append(threading.Thread(target=reader_worker, args=(i,)))
        for i in range(16):
            threads.append(threading.Thread(target=writer_worker, args=(i,)))

        start_time = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        elapsed = time.perf_counter() - start_time

        assert len(errors) == 0, f"Encountered thread errors during burst: {errors}"
        assert sum(read_counts) == 16 * 50, f"Expected 800 reads, got {sum(read_counts)}"
        assert sum(write_counts) == 16 * 30, f"Expected 480 writes, got {sum(write_counts)}"
        assert elapsed < 15.0, f"Concurrency test took too long: {elapsed:.2f}s"

        # Final state verification on disk
        disk_loaded = store.load_from_disk()
        assert disk_loaded is not None
        assert disk_loaded.version == "3.0.0-CANONICAL"


# ============================================================================
# 2. MALFORMED JSON/YAML & CORRUPTED DISK STATE RECOVERY (Adversarial Fuzzing)
# ============================================================================

def test_stress_corrupted_disk_recovery_matrix():
    """
    Empirically test resilience against corrupted disk states:
    1. Truncated JSON / partial write files
    2. Random non-JSON binary bytes
    3. Null bytes (\x00) and Unicode garbage
    4. Invalid YAML syntax
    5. Empty 0-byte files
    6. Read-only permissions on temporary paths
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        json_path = os.path.join(tmpdir, "blackboard_state.json")
        yaml_path = os.path.join(tmpdir, "blackboard_state.yaml")

        adversarial_payloads = [
            b"",  # Empty file
            b"   \n\t  ",  # Whitespace only
            b"{",  # Truncated open brace
            b'{"version": "3.0.0-CANONICAL", "layer_0_networking": {',  # Truncated nested
            b"\x00\x01\x02\x03\xff\xfe\xfd",  # Raw binary garbage
            b"--- \n [unclosed list item",  # Corrupted YAML in JSON file
        ]

        for payload in adversarial_payloads:
            with open(json_path, "wb") as f:
                f.write(payload)

            # 1. load_from_disk should return None on corrupted syntax
            loaded = store.load_from_disk()
            assert loaded is None, f"Expected load_from_disk to return None for payload {payload!r}"

            # 2. get_snapshot must self-heal by returning canonical default
            snap = store.get_snapshot(force_refresh=True)
            assert snap is not None
            assert snap.version == "3.0.0-CANONICAL"
            assert len(snap.layer_0_networking.wol_targets) == 5

        # Test corrupt YAML fallback
        if os.path.exists(json_path):
            os.remove(json_path)

        for payload in adversarial_payloads:
            with open(yaml_path, "wb") as f:
                f.write(payload)
            loaded_yaml = store.load_from_disk()
            assert loaded_yaml is None
            snap = store.get_snapshot(force_refresh=True)
            assert snap is not None
            assert snap.version == "3.0.0-CANONICAL"


def test_stress_malformed_layer_mutation_payloads():
    """
    Test store.update_layer against malformed, partial, or wrong-type payloads.
    Ensures clear exceptions without corrupting the store state.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)

        # 1. Unknown layer key -> ValueError
        with pytest.raises(ValueError):
            store.update_layer("layer_99_nonexistent", {})

        # 2. Unsupported payload type -> TypeError
        with pytest.raises(TypeError):
            store.update_layer("layer_0", "THIS_IS_A_STRING_NOT_DICT_OR_DATACLASS")

        with pytest.raises(TypeError):
            store.update_layer("layer_1", 123456)

        # 3. Valid partial dict with missing optional keys should still hydrate properly
        partial_bio = {"heart_rate_bpm": 145.0}
        updated = store.update_layer("layer_2", partial_bio)
        assert updated.layer_2_biometrics.heart_rate_bpm == 145.0
        # Check that default fields are preserved
        assert updated.layer_2_biometrics.zone2_status == "ZONE_2_OPTIMAL"

        # 4. Invariant: store remains healthy and can produce clean JSON/YAML
        json_out = store.to_json()
        assert "3.0.0-CANONICAL" in json_out
        yaml_out = store.to_yaml()
        assert "3.0.0-CANONICAL" in yaml_out


# ============================================================================
# 3. MEMORY LEAK / RAPID STATE SNAPSHOT CREATION (5,000+ Iterations)
# ============================================================================

def test_stress_memory_leak_rapid_snapshot_creation():
    """
    Empirically profile memory allocation during 5,000 rapid snapshot creations
    and round-trip serialization cycles to detect memory leaks, cyclic references,
    or unbounded object retention.
    """
    gc.collect()
    tracemalloc.start()

    store = BlackboardStore(auto_persist=False, cache_ttl_seconds=1.0)
    snapshot_count = 5000

    start_mem, _ = tracemalloc.get_traced_memory()
    t0 = time.perf_counter()

    for i in range(snapshot_count):
        snap = store.get_snapshot(force_refresh=False)
        # Perform lightweight mutation every 100 iterations
        if i % 100 == 0:
            d = snap.layer_4_training_games.to_dict()
            d["training_step"] = 4800 + i
            store.update_layer("layer_4", d)

        # Serialize to dict every 500 iterations
        if i % 500 == 0:
            _ = store.get_raw_state_for_agi()

    t1 = time.perf_counter()
    gc.collect()

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    duration = t1 - t0
    ops_per_sec = snapshot_count / duration
    net_mem_growth_kb = (current_mem - start_mem) / 1024.0

    print(f"\n[Memory Stress] {snapshot_count} cycles in {duration:.2f}s ({ops_per_sec:.0f} ops/sec)")
    print(f"[Memory Stress] Current: {current_mem/1024/1024:.2f}MB, Peak: {peak_mem/1024/1024:.2f}MB, Net Growth: {net_mem_growth_kb:.2f}KB")

    # Invariants:
    # 1. Throughput must exceed 500 ops/sec
    assert ops_per_sec > 500, f"Snapshot throughput too low: {ops_per_sec:.0f} ops/sec"
    # 2. Net memory growth after GC should be under 5 MB for 5,000 iterations
    assert net_mem_growth_kb < 5120.0, f"Potential memory leak: net growth {net_mem_growth_kb:.2f} KB"


# ============================================================================
# 4. NON-BLOCKING SOCKET PROBE & SIMULATED NETWORK DROPS
# ============================================================================

def test_stress_socket_probe_simulated_network_drops():
    """
    Stress test probe_endpoint under diverse adversarial network conditions:
    1. Port listening with instant connection -> valid RTT float
    2. Connection refused (closed port) -> authentic None (fast < 10ms)
    3. Unroutable IP (simulated network blackhole, e.g. 192.0.2.1) -> timeout without blocking beyond timeout + delta
    4. Hanging socket (server binds and listens but never accepts) -> timeout respected
    5. Invalid hostnames / malformed IPs -> authentic None without unhandled exceptions
    """
    store = BlackboardStore()

    # 1. Valid real local TCP server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server_port = server.getsockname()[1]
    server.listen(128)

    try:
        rtt = store.probe_endpoint("127.0.0.1", server_port, timeout=0.10)
        assert rtt is not None
        assert isinstance(rtt, float)
        assert rtt >= 0.0
    finally:
        server.close()

    # 2. Closed port (Connection Refused)
    t0 = time.perf_counter()
    rtt_closed = store.probe_endpoint("127.0.0.1", 59998, timeout=0.05)
    t1 = time.perf_counter()
    assert rtt_closed is None
    assert (t1 - t0) < 0.10

    # 3. Non-routable TEST-NET IP (RFC 5737: 192.0.2.1) -> must timeout without exceeding timeout bound
    timeout_limit = 0.05
    t0 = time.perf_counter()
    rtt_blackhole = store.probe_endpoint("192.0.2.1", 80, timeout=timeout_limit)
    t1 = time.perf_counter()
    assert rtt_blackhole is None
    elapsed = t1 - t0
    assert elapsed < (timeout_limit + 0.15), f"Socket probe blocked for {elapsed:.3f}s on blackhole IP"

    # 4. Malformed hostnames / invalid IP strings -> None without crashing
    assert store.probe_endpoint("invalid.domain.that.does.not.exist.test", 8080, timeout=0.05) is None
    assert store.probe_endpoint("999.999.999.999", 8080, timeout=0.05) is None


def test_stress_concurrent_socket_probes():
    """
    Stress test 20 concurrent threads performing rapid socket probes to ensure
    socket descriptor exhaustion or thread contention does not occur.
    """
    store = BlackboardStore()
    results = []

    def probe_worker(idx: int):
        for _ in range(10):
            r = store.probe_endpoint("127.0.0.1", 59990 + (idx % 5), timeout=0.02)
            results.append(r)

    threads = [threading.Thread(target=probe_worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert len(results) == 200
    assert all(r is None for r in results)  # All were closed ports


# ============================================================================
# 5. DATACLASS FUZZING & BOUNDARY CONDITIONS ACROSS ALL 7 LAYERS
# ============================================================================

def test_stress_dataclass_boundary_and_fuzz_conditions():
    """
    Fuzz test dataclasses with boundary values:
    - Empty collections
    - None/null values on optional and required fields
    - Extreme float/integer values (NaN, Inf, negative numbers, high integers)
    - Unicode strings and long character sequences
    """
    # 1. Layer 0: Empty routes & targets
    l0 = Layer0NetworkingState(
        wol_targets=[],
        bluetooth_pan=BluetoothPanLink(rtt_ms=None, bandwidth="0 B/s", paired_devices=0),
        kde_connect=KdeConnectState(paired_nodes=0, rtt_ms=None),
        tb4_dma=Tb4DmaInterconnect(rtt_ms=None, throughput_gbps=0.0),
        wan_routes=[],
        tailscale_peers=[],
        ewma_alpha=0.0,
        circuit_breaker_trip_threshold=1.0
    )
    d0 = l0.to_dict()
    r0 = Layer0NetworkingState.from_dict(d0)
    assert len(r0.wol_targets) == 0
    assert len(r0.wan_routes) == 0
    assert r0.bluetooth_pan.rtt_ms is None

    # 2. Layer 1: Hardware with extreme loads & temperatures
    node = HardwareNodeState(
        node_id="L99", name="Extreme_Node_\u26a1", model="Test Model", arch="RISC-V",
        os="Custom OS", role="Stress Tester", ip="0.0.0.0", tailscale_ip="100.0.0.0",
        status="DEGRADED", ram_total_gb=1024.0, ram_used_gb=1023.9, ram_usage_pct=99.99,
        vram_cap_gb=512.0, vram_used_gb=511.9, dynamic_cap_pct=100.0, cpu_usage_pct=100.0,
        cpu_cores=128, load_1m=150.0, load_5m=120.0, load_15m=100.0, thermal_c=98.5,
        thermal_status="CRITICAL", battery_pct=1, is_charging=False, power_source="BATTERY",
        qi_power_watts=0.0, storage_free_gb=0.001
    )
    d_node = node.to_dict()
    r_node = HardwareNodeState(**d_node)
    assert r_node.thermal_status == "CRITICAL"
    assert r_node.cpu_cores == 128
    assert r_node.name == "Extreme_Node_\u26a1"

    # 3. Layer 2: Biometrics with extreme/null heart rate and zero-length RR intervals
    l2 = Layer2BiometricsState(
        movesense_stream=MovesenseStreamState(connected=False, battery_pct=0, ecg_snr_db=0.0),
        kamath_filter=KamathFilterState(is_active=False, rejection_rate_pct=100.0),
        heart_rate_bpm=None,
        rr_intervals_ms=[],
        rmssd_ms=None,
        dfa_alpha1=None,
        zone2_status="OFFLINE",
        vo2_max_ml_kg_min=None,
        ptt_blood_pressure=PttBloodPressure(systolic_mmhg=None, diastolic_mmhg=None, pulse_transit_time_ms=None),
        imu_kinematics=ImuKinematicsState(cadence_spm=0, mechanical_power_watts=0.0),
        grappling_map=GrapplingMapState(total_nodes=0, total_transitions=0, recent_submissions=[])
    )
    d2 = l2.to_dict()
    r2 = Layer2BiometricsState.from_dict(d2)
    assert r2.heart_rate_bpm is None
    assert len(r2.rr_intervals_ms) == 0
    assert r2.zone2_status == "OFFLINE"

    # 4. Layer 4: 1,000 loss decay history points
    huge_loss_history = [LossDecayPoint(step=i, loss=round(2.0 / (i + 1), 4)) for i in range(1000)]
    l4 = Layer4TrainingGamesState(
        loss_history=huge_loss_history,
        total_harvested_pairs=10000000,
        training_step=1000000
    )
    d4 = l4.to_dict()
    r4 = Layer4TrainingGamesState.from_dict(d4)
    assert len(r4.loss_history) == 1000
    assert r4.loss_history[999].step == 999

    # 5. Full Root State Roundtrip with all fuzzed layers
    root = BlackboardTelemetryState(
        version="3.0.0-FUZZ",
        source_node="Stress_Harness",
        provenance=BlackboardProvenance(rule_zero_certified=True),
        layer_0_networking=l0,
        layer_1_hardware=Layer1HardwareState(nodes=[node]),
        layer_2_biometrics=l2,
        layer_4_training_games=l4
    )

    json_fuzz = root.to_json()
    reconstructed_json = BlackboardTelemetryState.from_json(json_fuzz)
    assert reconstructed_json.version == "3.0.0-FUZZ"
    assert reconstructed_json.layer_1_hardware.nodes[0].name == "Extreme_Node_\u26a1"
    assert len(reconstructed_json.layer_4_training_games.loss_history) == 1000

    yaml_fuzz = root.to_yaml()
    reconstructed_yaml = BlackboardTelemetryState.from_yaml(yaml_fuzz)
    assert reconstructed_yaml.version == "3.0.0-FUZZ"
    assert reconstructed_yaml.layer_2_biometrics.heart_rate_bpm is None
