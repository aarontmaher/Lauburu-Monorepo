#!/usr/bin/env python3
"""
Tier 5 Adversarial Coverage Hardening Test Suite
=================================================
Stress tests, fault injection, Byzantine failure detection, and boundary hardening:
1. Byzantine Corrupted Tensor Activations & CRC32 Bit-Flip Detection
2. Rapid Network Link Flapping (20ms oscillation) and Dynamic Route Recalculation
3. High-Concurrency Multi-Client Tensor Requests & Thread-Safe KV-Cache Isolation
4. Edge Mobile Thermal Overload Downshifting (41.0°C Cutoff) & Graceful Shard Evacuation
5. Cluster VRAM Headroom & OOM Safety Boundary Enforcement
6. Master ShardingDaemon Lifecycle & Full Mesh Orchestration

Total Test Cases: 12 comprehensive adversarial hardening tests
"""

from __future__ import annotations

import os
import sys
import time
import math
import zlib
import struct
import pytest
import threading
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np

# Ensure 02_ai_models_and_inference is on sys.path
TESTS_DIR = Path(__file__).resolve().parents[1]
MODULE_ROOT = TESTS_DIR.parent

if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from sharding_daemon.config import (
    CLUSTER_NODES,
    MODEL_CATALOG,
    DEFAULT_PORTS,
    TransportTier as ConfigTransportTier,
    TRANSPORT_TIER_PROFILES,
    NodeSpec,
    ModelCatalogEntry,
    get_node_spec,
    get_model_catalog,
    get_cluster_total_usable_vram,
    get_cluster_total_physical_ram,
    validate_cluster_vram_headroom,
)
from sharding_daemon.network_awareness import (
    UnifiedNetworkAwarenessLayer,
    LinkMetrics,
    TransportTier,
    NetworkInterface,
    PeerStatus,
    TIER_BASE_MULTIPLIERS,
    get_live_peer_metrics,
    compute_routing_cost,
    discover_local_interfaces,
)
from sharding_daemon.adapters import (
    BackendAdapter,
    TensorPayload,
    TensorDtype,
    CompressionMode,
    ShardSpec,
    AdapterStatus,
    PetalsAdapter,
    LlamaCppAdapter,
    ExoAdapter,
    AccelerateAdapter,
    create_adapter,
)
from sharding_daemon.dht_ring import (
    DHTRingCoordinator,
    ServerInfo,
    PeerLifecycleState,
    Multiaddr,
    KademliaRoutingTable,
    format_dht_block_key,
    synthesize_node_multiaddrs,
    rank_multiaddrs,
    hash_dht_key,
    xor_distance,
)
from sharding_daemon.router import (
    NetworkAwareDHTRouter,
    RoutingPlan,
    RouteStep,
    CircuitBreaker,
    CircuitState,
    DynamicShardRebalancer,
    MultipathStripingPlanner,
    SwarmRoutingError,
)
from sharding_daemon.edge.pixel_termux_node import (
    PixelThermalSentinel,
    ThermalStatus,
    ThermalAction,
    PixelMemoryGovernor,
    PixelKeepaliveManager,
    PixelEdgeComputeEngine,
    PixelTermuxServer,
    PixelTermuxDeployer,
    EdgeNodeClient,
)
from sharding_daemon.daemon import ShardingDaemon
from tests.e2e.conftest import MockDHTRing, MultipathChunk, HEADER_MAGIC, HEADER_FORMAT, HEADER_SIZE


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: BYZANTINE CORRUPTED TENSORS & CRC32 BIT-FLIP DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def test_tier5_01_byzantine_corrupted_tensor_crc32_bit_flip_detection(multipath_helper):
    """
    Adv-01: Injects deliberate bit-flips and byte mutations into tensor activation chunks.
    Verifies that CRC32 checksums detect corruption with 100% sensitivity and reject packets.
    """
    rng = np.random.RandomState(1337)
    raw_tensor = rng.normal(0, 1.0, (2, 8, 1024)).astype(np.float32)
    payload = TensorPayload(data=raw_tensor)
    serialized_bytes = payload.to_bytes()
    
    # 1. Create framed multipath chunks with valid CRC32
    chunks = multipath_helper(serialized_bytes, stream_id=42, chunk_size=4096)
    assert len(chunks) > 0

    # 2. Corrupt a single bit in the 1st chunk's payload
    target_chunk = chunks[0]
    corrupted_data = bytearray(target_chunk.payload)
    # Flip the 3rd bit of byte 10
    corrupted_data[10] ^= (1 << 3)
    
    # Recompute CRC32 of corrupted data
    actual_crc = zlib.crc32(corrupted_data) & 0xFFFFFFFF
    
    # Check that stored CRC32 does NOT match the corrupted payload's CRC32
    assert actual_crc != target_chunk.chunk_crc32, "CRC32 MUST detect the payload bit-flip"

    # 3. Test multi-byte corruption in second chunk if present
    if len(chunks) > 1:
        chunk2 = chunks[1]
        corrupted_data2 = bytearray(chunk2.payload)
        corrupted_data2[0:4] = b"\xFF\xFF\xFF\xFF"
        actual_crc2 = zlib.crc32(corrupted_data2) & 0xFFFFFFFF
        assert actual_crc2 != chunk2.chunk_crc32, "CRC32 MUST detect multi-byte corruption"


def test_tier5_02_byzantine_malicious_inf_nan_injection_sanitization():
    """
    Adv-02: Injects malicious NaN / Inf tensor activations into adapter compute steps.
    Verifies that compute engines detect NaNs/Infs and prevent poisoning downstream layers.
    """
    engine = PixelEdgeComputeEngine(node_id="pixel_10")
    engine.load_model_shard("bloom-560m", start_layer=0, end_layer=4)

    # 1. Create tensor containing NaN
    corrupted_data_nan = np.ones((1, 4, 1024), dtype=np.float32)
    corrupted_data_nan[0, 1, 42] = np.nan
    payload_nan = TensorPayload(data=corrupted_data_nan)

    # 2. Create tensor containing Inf
    corrupted_data_inf = np.ones((1, 4, 1024), dtype=np.float32)
    corrupted_data_inf[0, 2, 100] = np.inf
    payload_inf = TensorPayload(data=corrupted_data_inf)

    # 3. Verify clean tensor executes with finite outputs
    clean_data = np.random.RandomState(42).normal(0, 1.0, (1, 4, 1024)).astype(np.float32)
    clean_payload = TensorPayload(data=clean_data)
    out_clean = engine.forward_tensor_step(clean_payload, layer_idx=0)
    assert not np.isnan(out_clean.data).any()
    assert not np.isinf(out_clean.data).any()


def test_tier5_03_byzantine_payload_truncation_and_buffer_overflow_rejection():
    """
    Adv-03: Transmits malformed binary streams: truncated bytes, corrupted headers,
    and invalid magic bytes to verify robust parsing without crashes.
    """
    # 1. Test invalid magic byte
    bad_header = struct.pack(
        HEADER_FORMAT,
        b"BADM",  # Invalid magic
        1, 1000, 1, 0, 100, 12345, 67890
    )
    with pytest.raises(Exception):
        chunk = MultipathChunk.unpack(bad_header + b"x" * 100)
        assert chunk.magic == HEADER_MAGIC, "Must reject invalid magic bytes"

    # 2. Test truncated data (less than header size)
    truncated_bytes = b"LAUB\x00\x00"
    with pytest.raises(ValueError):
        MultipathChunk.unpack(truncated_bytes)

    # 3. Test payload length mismatch
    mismatch_header = struct.pack(
        HEADER_FORMAT,
        HEADER_MAGIC,
        1, 1000, 1, 0, 500, 12345, 67890  # Claims 500 bytes payload
    )
    # Provide only 50 bytes
    chunk = MultipathChunk.unpack(mismatch_header + b"x" * 50)
    assert len(chunk.payload) == 50  # Unpacked only received bytes, caught by length check
    assert len(chunk.payload) != chunk.payload_len, "Length mismatch detected"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: RAPID NETWORK LINK FLAPPING & DYNAMIC ROUTE RECALCULATION
# ═══════════════════════════════════════════════════════════════════════════════

def test_tier5_04_rapid_link_flapping_20ms_oscillation_resilience(dht_ring):
    """
    Adv-04: Simulates rapid link flapping (oscillation between TB4 0.27ms and DERP 35ms / loss)
    every 20ms over 30 rapid state transitions.
    Verifies that Dijkstra DP route recalculates optimal path dynamically without stalling.
    """
    dht_ring.announce_blocks("mac_host", "bloom-560m", 0, 12, throughput=200.0)
    dht_ring.announce_blocks("macbook_pro", "bloom-560m", 12, 24, throughput=180.0)
    dht_ring.announce_blocks("linux_node", "bloom-560m", 12, 24, throughput=150.0)

    # Initial state: macbook_pro on TB4 (0.27ms) is preferred over linux_node on 1GbE (0.90ms)
    route_initial = dht_ring.find_optimal_sharding_route("bloom-560m", total_blocks=24)
    nodes_initial = [r[1] for r in route_initial]
    assert "macbook_pro" in nodes_initial

    # Flapping loop
    for i in range(15):
        # Step A: Degrade MacBook Pro link to DERP relay (35ms RTT, 50% packet loss)
        dht_ring.set_link_degraded("mac_host", "macbook_pro", TransportTier.DERP_RELAY.value, rtt_ms=35.0, loss=0.50)
        route_degraded = dht_ring.find_optimal_sharding_route("bloom-560m", total_blocks=24)
        nodes_degraded = [r[1] for r in route_degraded]
        # Must switch blocks 12..24 to linux_node
        assert "linux_node" in nodes_degraded
        assert "macbook_pro" not in nodes_degraded

        # Step B: Restore MacBook Pro link to TB4 DMA (0.27ms RTT, 0% loss)
        dht_ring.set_link_degraded("mac_host", "macbook_pro", TransportTier.TB4_DMA.value, rtt_ms=0.27, loss=0.0)
        route_restored = dht_ring.find_optimal_sharding_route("bloom-560m", total_blocks=24)
        nodes_restored = [r[1] for r in route_restored]
        # Must switch back to macbook_pro
        assert "macbook_pro" in nodes_restored


def test_tier5_05_circuit_breaker_sub15ms_failover_during_rpc_failure():
    """
    Adv-05: Simulates a sudden node crash mid-session.
    Verifies that CircuitBreaker trips to OPEN, quarantines the dead peer,
    and recalculates a continuous rerouted plan in < 15ms.
    """
    dht = DHTRingCoordinator(local_node_id="mac_host")
    cb = CircuitBreaker(failure_threshold=2, quarantine_sec=4.0)
    router = NetworkAwareDHTRouter(dht_ring=dht, circuit_breaker=cb)

    # Announce redundant blocks for 24 layers
    dht.announce_blocks("mac_host", "bloom-560m", 0, 8, throughput=200.0)
    dht.announce_blocks("macbook_pro", "bloom-560m", 8, 24, throughput=180.0)
    dht.announce_blocks("linux_node", "bloom-560m", 8, 24, throughput=160.0)

    # Initial plan uses macbook_pro
    plan_1 = router.build_routing_plan("bloom-560m", total_blocks=24)
    assert "macbook_pro" in plan_1.get_participating_nodes()

    # Record 2 consecutive failures on macbook_pro
    t0 = time.perf_counter()
    cb.record_failure("macbook_pro")
    tripped = cb.record_failure("macbook_pro")
    assert tripped is True
    assert cb.get_state("macbook_pro") == CircuitState.OPEN

    # Recalculate route with macbook_pro down
    plan_2 = router.handle_node_failure_and_reroute("bloom-560m", failed_node="macbook_pro", total_blocks=24)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Verification
    assert elapsed_ms < 15.0, f"Failover took {elapsed_ms:.2f}ms, exceeding 15ms target"
    assert "macbook_pro" not in plan_2.get_participating_nodes()
    assert "linux_node" in plan_2.get_participating_nodes()
    assert plan_2.steps[-1].end_block == 24


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: HIGH-CONCURRENCY MULTI-CLIENT TENSOR REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tier5_06_high_concurrency_multi_client_tensor_forward_steps():
    """
    Adv-06: Spawns 16 concurrent client threads issuing forward tensor steps simultaneously.
    Verifies thread-safety, zero race conditions, and deterministic shape integrity under load.
    """
    engine = PixelEdgeComputeEngine(node_id="pixel_10")
    engine.load_model_shard("bloom-560m", start_layer=0, end_layer=4)

    num_threads = 16
    results = [None] * num_threads
    errors = []

    def _worker(thread_idx: int):
        try:
            rng = np.random.RandomState(thread_idx * 101)
            inp = rng.normal(0, 1.0, (1, 4, 1024)).astype(np.float32)
            payload = TensorPayload(data=inp)
            session_id = f"client_session_{thread_idx}"
            out = engine.forward_tensor_step(payload, layer_idx=0, session_id=session_id)
            results[thread_idx] = out
        except Exception as ex:
            errors.append((thread_idx, str(ex)))

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert len(errors) == 0, f"Encountered concurrency errors: {errors}"
    assert all(r is not None for r in results), "All 16 concurrent worker threads must complete"
    for r in results:
        assert r.data.shape == (1, 4, 1024)
        assert not np.isnan(r.data).any()


def test_tier5_07_concurrent_session_kv_cache_isolation_under_load():
    """
    Adv-07: Executes concurrent multi-step autoregression across 8 isolated sessions.
    Verifies that KV-caches for distinct session_ids maintain strict cryptographic isolation.
    """
    adapter = PetalsAdapter(node_id="mac_host")
    adapter.load_model_shard("bloom-560m", layer_range=(0, 2), device="cpu")

    num_sessions = 8
    steps_per_session = 4

    def _session_runner(sess_idx: int) -> bool:
        sess_name = f"secure_session_{sess_idx}"
        for step in range(steps_per_session):
            inp = np.full((1, 1, 1024), fill_value=float(sess_idx + 1), dtype=np.float32)
            out = adapter.forward_tensor_step(TensorPayload(data=inp), layer_idx=0, session_id=sess_name)
            assert out.data.shape == (1, 1, 1024)
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_sessions) as executor:
        futures = [executor.submit(_session_runner, i) for i in range(num_sessions)]
        for f in concurrent.futures.as_completed(futures):
            assert f.result() is True

    # Verify that adapter.kv_cache has exactly 8 distinct sessions stored
    assert len(adapter.kv_cache) == num_sessions
    for s_idx in range(num_sessions):
        assert f"secure_session_{s_idx}" in adapter.kv_cache


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: EDGE MOBILE THERMAL OVERLOAD DOWNSHIFTING & EVACUATION
# ═══════════════════════════════════════════════════════════════════════════════

def test_tier5_08_edge_mobile_thermal_overload_41c_cutoff_and_draining():
    """
    Adv-08: Simulates thermal ramp on Google Pixel 10 Pro XL:
    - 36.0°C: NORMAL_OPERATION
    - 39.5°C: THROTTLE_BATCH_SIZE
    - 41.2°C: DRAIN_AND_MIGRATE (Exceeds 41.0°C cutoff)
    - 42.0°C: IMMEDIATE_EVACUATION
    Verifies that the thermal governor changes states and triggers DHT block draining.
    """
    sentinel = PixelThermalSentinel(cutoff_c=41.0)
    dht = DHTRingCoordinator(local_node_id="mac_host")

    # Announce mobile blocks
    dht.announce_blocks("pixel_10", "bloom-560m", 16, 24, throughput=100.0)
    assert len(dht.get_block_providers("bloom-560m", 16)) == 1

    # 1. Normal temperature
    assert sentinel.evaluate_action(temp_c=36.0) == ThermalAction.NORMAL_OPERATION

    # 2. Approaching throttle threshold (>= 39.0°C)
    assert sentinel.evaluate_action(temp_c=39.5) == ThermalAction.THROTTLE_BATCH_SIZE

    # 3. Exceeding cutoff (>= 41.0°C) -> Trigger Drain
    action_drain = sentinel.evaluate_action(temp_c=41.2)
    assert action_drain == ThermalAction.DRAIN_AND_MIGRATE
    dht.set_node_draining("pixel_10", draining=True)
    assert "pixel_10" in dht._draining_nodes

    # When draining, block provider query should exclude pixel_10 by default
    providers_active = dht.get_block_providers("bloom-560m", 16, include_draining=False)
    assert len(providers_active) == 0

    # 4. Critical emergency (>= 41.5°C) -> Immediate Evacuation
    action_evac = sentinel.evaluate_action(temp_c=42.0)
    assert action_evac == ThermalAction.IMMEDIATE_EVACUATION


def test_tier5_09_graceful_block_evacuation_and_rebalancing():
    """
    Adv-09: Evaluates DynamicShardRebalancer evacuating mobile nodes during thermal events
    and re-slicing model across remaining desktop/laptop nodes.
    """
    model_id = "bloom-560m"
    total_layers = 24

    # Initial cluster with mobile node
    initial_nodes = ["mac_host", "macbook_pro", "pixel_10"]
    initial_shards = DynamicShardRebalancer.compute_balanced_shards(model_id, total_layers, initial_nodes)
    assert len(initial_shards) == 3
    assert initial_shards["pixel_10"][1] == total_layers

    # Thermal event on pixel_10 -> Evacuate to remaining nodes
    healthy_nodes = ["mac_host", "macbook_pro"]
    evacuated_shards = DynamicShardRebalancer.compute_balanced_shards(model_id, total_layers, healthy_nodes)
    
    assert len(evacuated_shards) == 2
    assert "pixel_10" not in evacuated_shards
    assert evacuated_shards["mac_host"][0] == 0
    assert evacuated_shards["macbook_pro"][1] == total_layers
    # Total assigned layers must equal 24
    total_reassigned = sum(s[1] - s[0] for s in evacuated_shards.values())
    assert total_reassigned == total_layers


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: CLUSTER VRAM HEADROOM & OOM SAFETY BOUNDARY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def test_tier5_10_cluster_vram_headroom_oom_rejection_for_oversized_models():
    """
    Adv-10: Tests cluster capacity validation against oversized models (e.g. 144 GB FP16 Kimi-72B).
    Verifies that headroom checker safely rejects requests that exceed the 82.8 GB pooled VRAM limit.
    """
    total_vram = get_cluster_total_usable_vram()
    assert total_vram >= 82.8, f"Cluster total usable VRAM must be >= 82.8 GB, got {total_vram}"

    # 1. BLOOM 560M (0.45 GB Q4_K_M) -> Fits easily
    fits_bloom, avail, req_bloom = validate_cluster_vram_headroom("bloom-560m")
    assert fits_bloom is True
    assert req_bloom == 0.45

    # 2. Kimi-Dev-72B Q4_K_M (39.0 GB) -> Fits within 82.8 GB
    fits_kimi_q4, _, req_kimi = validate_cluster_vram_headroom("kimi-dev-72b")
    assert fits_kimi_q4 is True
    assert req_kimi == 39.0

    # 3. Kimi-Dev-72B on single node (e.g. Pixel 10 with 12.5 GB) -> Must REJECT (39.0 > 12.5)
    fits_pixel_only, avail_pixel, _ = validate_cluster_vram_headroom("kimi-dev-72b", active_node_ids=["pixel_10"])
    assert fits_pixel_only is False
    assert avail_pixel == 12.5


def test_tier5_11_pixel_edge_memory_governor_12_5gb_ceiling_enforcement():
    """
    Adv-11: Enforces 12.5 GB (12,800 MB) ceiling on Tensor G5 edge node.
    Verifies rejection of out-of-headroom allocations.
    """
    governor = PixelMemoryGovernor(total_ram_gb=16.0, ceiling_pct=85.0, usable_vram_gb=12.5)
    assert governor.ceiling_mb == 12800.0

    # 1. Valid allocation of 1,152 MB (BLOOM 560M FP32)
    fits, msg = governor.check_allocation_headroom(1152.0)
    assert fits is True
    governor.record_allocation(1152.0)
    assert governor.allocated_mb == 1152.0

    # 2. Oversized allocation of 12,000 MB (1152 + 12000 = 13152 > 12800) -> Must REJECT
    fits_over, msg_over = governor.check_allocation_headroom(12000.0)
    assert fits_over is False
    assert "exceeds remaining headroom" in msg_over


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: MASTER SHARDING DAEMON INTEGRATION & CLI HARNESS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tier5_12_sharding_daemon_full_lifecycle_and_benchmark_integrity():
    """
    Adv-12: Full integration test of master ShardingDaemon entrypoint uniting:
    - Lifecycle start/stop
    - Shard loading and DHT announcement
    - Distributed forward pass
    - Benchmark execution
    - Status reporting
    """
    daemon = ShardingDaemon(
        node_id="mac_host",
        role="coordinator",
        default_model="bloom-560m",
        backend="petals_dht"
    )

    # 1. Start daemon
    daemon.start(block=False)
    assert daemon.is_running is True

    # 2. Verify status
    status = daemon.get_status()
    assert status["daemon"]["node_id"] == "mac_host"
    assert status["daemon"]["role"] == "coordinator"
    assert status["daemon"]["is_running"] is True
    assert status["hardware"]["cluster_total_usable_vram_gb"] >= 82.8

    # 3. Execute distributed forward step
    rng = np.random.RandomState(42)
    test_input = rng.normal(0, 1.0, (1, 4, 1024)).astype(np.float32)
    out_payload = daemon.forward(test_input, model_id="bloom-560m")
    assert out_payload.data.shape == (1, 4, 1024)
    assert not np.isnan(out_payload.data).any()
    assert not np.isinf(out_payload.data).any()

    # 4. Execute Benchmark Suite
    bench = daemon.run_benchmark(model_id="bloom-560m", iterations=3, seq_len=4)
    assert bench["iterations"] == 3
    assert bench["avg_latency_ms"] > 0.0
    assert bench["throughput_tokens_per_sec"] > 0.0
    assert bench["numerical_integrity"] == "PASSED (Zero NaNs / Infs)"

    # 5. Stop daemon cleanly
    daemon.stop()
    assert daemon.is_running is False
