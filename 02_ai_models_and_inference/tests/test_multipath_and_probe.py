#!/usr/bin/env python3
"""
Unit and Integration Tests for Mesh Network Probe & Multipath Tensor Router
Milestone M1 — Lauburu AI Mesh Network Foundation
"""

import os
import sys
import zlib
import json
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NETWORK_DIR = REPO_ROOT / "06_scripts_and_tooling" / "network"
SHARDING_DIR = REPO_ROOT / "02_ai_models_and_inference"

for p in (str(NETWORK_DIR), str(SHARDING_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from mesh_network_probe import MeshNetworkProbe
from tensor_multipath_router import (
    MultipathTensorEngine,
    HEADER_FORMAT,
    HEADER_MAGIC,
    HEADER_SIZE,
    DEFAULT_CHUNK_SIZE,
)


class TestMeshNetworkProbe:
    """Test MeshNetworkProbe continuous probing and output serialization."""

    def test_probe_cycle_execution(self, tmp_path):
        probe = MeshNetworkProbe(interval_sec=2.0)
        data = probe.probe_cycle(verbose=False)

        assert isinstance(data, dict)
        assert "timestamp_utc" in data
        assert "local_node" in data
        assert "peers" in data
        assert "bonding_state" in data

        # Check bonding state fields
        bonding = data["bonding_state"]
        assert "mode" in bonding
        assert "effective_throughput_mbps" in bonding
        assert bonding["effective_throughput_mbps"] > 0
        assert "active_paths_count" in bonding
        assert bonding["active_paths_count"] >= 1

    def test_probe_single_peer(self):
        probe = MeshNetworkProbe()
        res = probe.probe_single_peer("127.0.0.1")
        assert res["target"] == "127.0.0.1"
        assert "metrics" in res
        assert res["metrics"]["tailscale_ip"] == "127.0.0.1"
        assert res["routing_cost"] == 0.0


class TestMultipathTensorEngine:
    """Test MultipathTensorEngine dynamic binding, 36-byte framing, and failover."""

    def test_dynamic_interface_binding(self):
        engine = MultipathTensorEngine()
        assert len(engine.active_paths) >= 1
        for path in engine.active_paths:
            assert "name" in path
            assert "src_ip" in path
            assert "device" in path
            assert "bandwidth_mbps" in path
            assert "weight" in path
            assert path["weight"] > 0.0

        total_weight = sum(p["weight"] for p in engine.active_paths)
        assert abs(total_weight - 1.0) < 0.05

    def test_36_byte_binary_framing_integrity(self):
        engine = MultipathTensorEngine()
        payload = b"TEST_AI_TENSOR_WEIGHT_MATRIX_RAW_BYTES_CHUNK_12345"
        total_size = len(payload)
        stream_id = 998877
        total_chunks = 1
        chunk_idx = 0
        total_crc = zlib.crc32(payload)

        # Pack
        packet = engine.pack_chunk(stream_id, total_size, total_chunks, chunk_idx, payload, total_crc)
        assert len(packet) == HEADER_SIZE + len(payload)
        assert packet[:4] == HEADER_MAGIC

        # Unpack
        meta, unpacked_payload = engine.unpack_chunk(packet)
        assert unpacked_payload == payload
        assert meta["stream_id"] == stream_id
        assert meta["total_size"] == total_size
        assert meta["total_chunks"] == total_chunks
        assert meta["chunk_index"] == chunk_idx
        assert meta["chunk_crc32"] == zlib.crc32(payload)
        assert meta["total_crc32"] == total_crc

    def test_chunk_partitioning(self):
        engine = MultipathTensorEngine()
        chunks = [f"chunk_{i}".encode("utf-8") for i in range(20)]
        allocations = engine.partition_chunks(chunks)

        assert isinstance(allocations, dict)
        all_allocated = []
        for path_name, path_chunks in allocations.items():
            all_allocated.extend(path_chunks)

        # Ensure all 20 chunks were allocated
        assert len(all_allocated) == 20
        indices = {idx for idx, _ in all_allocated}
        assert indices == set(range(20))

    def test_bonded_benchmark_throughput(self):
        engine = MultipathTensorEngine()
        res = engine.benchmark_bonded_throughput(tensor_size_mb=5)

        assert res["status"] == "OPTIMAL_BONDED"
        assert res["total_chunks"] > 0
        assert res["bonded_multipath_mbps"] > 0
        assert "VERIFIED_MATCH" in res["integrity_crc32"]

    def test_failover_resilience_sla(self):
        engine = MultipathTensorEngine()
        res = engine.test_failover_resilience(tensor_size_mb=2)

        assert res["status"] == "FAILOVER_SUCCESSFUL"
        assert res["failover_sla_met"] is True
        assert res["failover_duration_ms"] < 100.0
        assert res["crc32_verified"] is True
