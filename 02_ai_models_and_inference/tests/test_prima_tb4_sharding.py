#!/usr/bin/env python3
"""
02_ai_models_and_inference/tests/test_prima_tb4_sharding.py
============================================================
Comprehensive Unit & Integration Test Suite for Milestone M3 (R5):
TB4 DMA PRP Tensor Sharding & Network Awareness Layer.

Validates:
1. PrimaRingAdapter.route_tensor_shard contract & CRC32 chunk verification.
2. TB4 DMA latency SLA (<0.30ms RTT, nominal 0.204ms).
3. >45 tok/s tensor streaming throughput validation.
4. Zero dropped chunk guarantees across burst activations.
5. Dynamic layer migration (offload_layers, migrate_layers).
6. NetworkAwarenessLayer.probe_transports contract & TransportMatrix schema.
7. Multi-tier Dijkstra routing cost computation for tensor sharding.
"""

import os
import sys
import zlib
import time
import pytest
import numpy as np
from pathlib import Path

# Ensure paths on sys.path
TEST_DIR = Path(__file__).resolve().parent
MODULE_ROOT = TEST_DIR.parent
REPO_ROOT = MODULE_ROOT.parent
SHARDING_DIR = MODULE_ROOT / "sharding_daemon"

for p in [str(REPO_ROOT), str(MODULE_ROOT), str(SHARDING_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from prima_ring_adapter import (
    PrimaRingAdapter,
    PrimaTB4OffloadManager,
    ShardResponse,
    TB4DMAMetrics,
    get_tb4_status,
    offload_to_tb4,
    migrate_layers,
    TB4_BRIDGE_IP,
)
from network_awareness import (
    NetworkAwarenessLayer,
    UnifiedNetworkAwarenessLayer,
    TransportMatrix,
    TransportTier,
    LinkMetrics,
    compute_routing_cost,
    get_live_peer_metrics,
    discover_local_interfaces,
)


class TestPrimaTB4TensorSharding:
    """Verifies R5: prima.cpp PRP Tensor Sharding over 10Gbps TB4 DMA."""

    def test_prima_ring_adapter_initialization(self):
        adapter = PrimaRingAdapter()
        assert adapter.manager is not None
        status = adapter.manager.get_status()
        assert "tb4_bridge_ip" in status
        assert "bandwidth_gbps" in status
        assert status["bandwidth_gbps"] == 40.0

    def test_route_tensor_shard_success_and_crc32(self):
        adapter = PrimaRingAdapter()
        # Generate authentic tensor activation chunk
        data = np.random.randn(128, 4096).astype(np.float16)
        raw_bytes = data.tobytes()
        expected_crc = zlib.crc32(raw_bytes)

        resp = adapter.route_tensor_shard(layer_idx=14, activation_chunk=raw_bytes)

        assert isinstance(resp, ShardResponse)
        assert resp.success is True
        assert resp.layer_idx == 14
        assert resp.bytes_transferred == len(raw_bytes)
        assert resp.crc32 == expected_crc
        assert resp.zero_drop_verified is True
        assert resp.status == "TB4_DMA_STREAMING_OK"

    def test_tb4_dma_latency_sla_under_0_30ms(self):
        adapter = PrimaRingAdapter()
        raw_bytes = b"tensor_activation_test_payload_12345"
        resp = adapter.route_tensor_shard(layer_idx=15, activation_chunk=raw_bytes)

        assert resp.latency_ms < 0.30, f"Latency {resp.latency_ms}ms must be <0.30ms SLA"
        assert resp.latency_ms >= 0.10, "Latency must be physical non-negative value"

    def test_throughput_exceeds_45_tok_s(self):
        adapter = PrimaRingAdapter()
        # 128x2048 float16 activation tensor
        data = np.ones((128, 2048), dtype=np.float16).tobytes()
        resp = adapter.route_tensor_shard(layer_idx=16, activation_chunk=data)

        assert resp.throughput_tok_s >= 45.0, f"Throughput {resp.throughput_tok_s} tok/s must be >= 45 tok/s"

    def test_zero_dropped_chunks_guarantee_across_burst(self):
        adapter = PrimaRingAdapter()
        initial_dropped = adapter.manager.metrics.dropped_chunks

        # Burst 20 activation chunk transfers
        for i in range(20):
            chunk = f"chunk_data_{i}_{time.time()}".encode("utf-8")
            resp = adapter.route_tensor_shard(layer_idx=(i % 12) + 12, activation_chunk=chunk)
            assert resp.success is True
            assert resp.zero_drop_verified is True

        assert adapter.manager.metrics.dropped_chunks == initial_dropped

    def test_dynamic_layer_offload_and_migration(self):
        manager = PrimaTB4OffloadManager.get_instance()
        target_layers = [12, 13, 14, 15, 16, 17]
        ok = manager.offload_layers(target_layers, target_node_ip=TB4_BRIDGE_IP)
        assert ok is True

        status = manager.get_status()
        assert status["active_offloaded_layers"] == target_layers
        assert 0 not in status["active_offloaded_layers"]

        # Test helper functions
        assert offload_to_tb4([18, 19, 20]) is True
        assert migrate_layers("mac_host", "macbook_pro", 20, 24) is True


class TestUNALNetworkAwarenessAndRouting:
    """Verifies UNAL transport discovery, matrix probing, and routing cost computation."""

    def test_discover_local_interfaces_returns_loopback_and_primary(self):
        ifaces = discover_local_interfaces()
        assert len(ifaces) >= 1
        assert any(i.type == "loopback" or i.name in ("lo0", "lo") for i in ifaces)

    def test_probe_transports_matrix_contract(self):
        unal = UnifiedNetworkAwarenessLayer.get_instance()
        matrix = unal.probe_transports()

        assert isinstance(matrix, TransportMatrix)
        assert matrix.local_hostname != ""
        assert "tb4_dma" in matrix.__dict__
        assert "lan_1gbe" in matrix.__dict__
        assert "wifi7_mlo" in matrix.__dict__
        assert "tailscale_direct" in matrix.__dict__
        assert "derp_relay" in matrix.__dict__
        assert matrix.active_paths_count >= 0
        assert matrix.effective_throughput_mbps > 0.0
        assert matrix.min_latency_ms <= 3.50

    def test_get_live_peer_metrics_localhost(self):
        metrics = get_live_peer_metrics("127.0.0.1")
        assert isinstance(metrics, LinkMetrics)
        assert metrics.is_direct is True
        assert metrics.transport_tier == TransportTier.LOCAL_LOOPBACK.value
        assert metrics.rtt_ms < 1.0
        assert metrics.bandwidth_mbps >= 10000.0

    def test_compute_routing_cost_dijkstra_tiers(self):
        # Localhost transfer (zero cost)
        cost_local = compute_routing_cost("127.0.0.1", "127.0.0.1", 1024 * 1024)
        assert cost_local == 0.0

        # TB4 DMA link vs generic IP
        cost_tb4 = compute_routing_cost("127.0.0.1", "169.254.187.138", 10 * 1024 * 1024)
        assert cost_tb4 > 0.0
        assert cost_tb4 < 1.0, f"TB4 DMA cost should be minimal, got {cost_tb4}"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
