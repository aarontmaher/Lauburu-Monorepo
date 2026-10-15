#!/usr/bin/env python3
"""
02_ai_models_and_inference/tests/test_prima_ring_tb4_offload.py
==============================================================
Unit & Integration Test Suite for:
1. Dynamic Runtime Layer Migration over 10Gbps TB4 DMA Bridge (169.254.187.138 / bridge0).
2. Strict <0.30ms latency SLA verification and zero dropped activation chunks.
3. PrimaRingAdapter REST/RPC endpoints (/prima/offload, /prima/migrate, /prima/tb4/metrics).
4. Transparent OpenAI-compatible Proxy (/v1/chat/completions, /v1/models).
"""

import sys
import time
import zlib
import pytest
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repo root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SHARDING_DIR = PROJECT_ROOT / "02_ai_models_and_inference" / "sharding_daemon"
if str(SHARDING_DIR) not in sys.path:
    sys.path.insert(0, str(SHARDING_DIR))

from prima_ring_adapter import (
    app,
    PrimaTB4OffloadManager,
    TB4DMAMetrics,
    TB4_BRIDGE_IP,
    TB4_INTERFACE,
    get_tb4_status,
    offload_to_tb4,
    migrate_layers,
    _state,
)


class TestPrimaTB4OffloadManagerUnit:
    """Unit tests for PrimaTB4OffloadManager core logic and DMA transfers."""

    @pytest.fixture(autouse=True)
    def setup_manager(self):
        self.manager = PrimaTB4OffloadManager.get_instance()
        # Reset state
        _state.total_layers = 24
        _state.host_layers = list(range(0, 12))
        _state.offloaded_layers = list(range(12, 24))
        self.manager.metrics.dropped_chunks = 0
        self.manager.metrics.total_chunks_transferred = 0
        self.manager.metrics.bytes_transferred = 0

    def test_manager_singleton_and_defaults(self):
        assert self.manager is not None
        assert self.manager.target_ip == TB4_BRIDGE_IP
        assert self.manager.metrics.interface == TB4_INTERFACE
        assert self.manager.metrics.nominal_latency_ms == 0.27
        assert self.manager.metrics.bandwidth_gbps == 40.0

    def test_tb4_latency_probe_sub_300us_sla(self):
        lat_ms = self.manager.probe_tb4_latency()
        assert lat_ms < 0.30, f"TB4 DMA latency {lat_ms:.3f}ms exceeded <0.30ms SLA"
        assert lat_ms > 0.05
        assert self.manager.metrics.last_rtt_latency_ms < 0.30

    def test_offload_layers_state_mutation(self):
        target_layers = [16, 17, 18, 19, 20, 21, 22, 23]
        success = self.manager.offload_layers(target_layers, target_node_ip=TB4_BRIDGE_IP, model_id="bloom-560m")
        assert success is True
        assert _state.offloaded_layers == target_layers
        assert _state.host_layers == list(range(0, 16))
        assert self.manager.metrics.dropped_chunks == 0
        assert self.manager.metrics.total_chunks_transferred >= len(target_layers)

    def test_transfer_activation_chunk_zero_dropped_guarantee(self):
        rng = np.random.RandomState(42)
        tensor_data = rng.normal(0, 1.0, (1, 4, 1024)).astype(np.float32)
        raw_bytes = tensor_data.tobytes()

        success, lat_ms, crc = self.manager.transfer_activation_chunk(
            activation_data=tensor_data,
            layer_idx=12,
            seq_id=101
        )
        assert success is True
        assert lat_ms < 0.30
        assert crc == zlib.crc32(raw_bytes)
        assert self.manager.metrics.dropped_chunks == 0
        assert self.manager.metrics.bytes_transferred >= len(raw_bytes)

    def test_get_status_payload_invariants(self):
        status = self.manager.get_status()
        assert status["tb4_bridge_ip"] == TB4_BRIDGE_IP
        assert status["tb4_interface"] == TB4_INTERFACE
        assert status["latency_within_sla"] is True
        assert status["dropped_chunks"] == 0
        assert status["bandwidth_gbps"] == 40.0


class TestPrimaRingAdapterFastAPIEndpoints:
    """Integration tests for PrimaRingAdapter REST and proxy endpoints."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        r = self.client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "HEALTHY"
        assert data["service"] == "prima_ring_adapter"
        assert data["port"] == 8083

    def test_prima_status_endpoint(self):
        r = self.client.get("/prima/status")
        assert r.status_code == 200
        data = r.json()
        assert "tb4_dma_offload" in data
        assert "layer_distribution" in data
        assert data["tb4_dma_offload"]["dropped_chunks"] == 0
        assert data["tb4_dma_offload"]["latency_within_sla"] is True

    def test_prima_layers_endpoint(self):
        r = self.client.get("/prima/layers")
        assert r.status_code == 200
        data = r.json()
        assert "host_layers" in data
        assert "offloaded_layers" in data
        assert data["dropped_chunks"] == 0
        assert data["tb4_latency_ms"] < 0.30

    def test_prima_tb4_metrics_endpoint(self):
        r = self.client.get("/prima/tb4/metrics")
        assert r.status_code == 200
        data = r.json()
        assert data["tb4_interface"] == "bridge0"
        assert data["nominal_latency_ms"] == 0.27
        assert data["measured_rtt_latency_ms"] < 0.30
        assert data["dropped_chunks"] == 0

    def test_post_prima_offload_endpoint(self):
        payload = {
            "target_layers": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
            "target_node_ip": TB4_BRIDGE_IP,
            "model_id": "bloom-560m"
        }
        r = self.client.post("/prima/offload", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["action"] == "TB4_DMA_LAYER_OFFLOAD"
        assert data["dropped_chunks"] == 0
        assert data["dma_latency_ms"] < 0.30
        assert data["offloaded_layers"] == payload["target_layers"]

    def test_post_prima_migrate_endpoint(self):
        payload = {
            "from_node": "mac_host",
            "to_node": "macbook_pro",
            "start_layer": 10,
            "end_layer": 24,
            "model_id": "bloom-560m"
        }
        r = self.client.post("/prima/migrate", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["zero_dropped_chunks_verified"] is True
        assert data["tb4_latency_ms"] < 0.30
        assert data["migrated_layers_count"] == 14

    def test_post_prima_tb4_forward_chunk_binary(self):
        dummy_tensor = np.ones((1, 2, 1024), dtype=np.float32)
        raw_bytes = dummy_tensor.tobytes()

        r = self.client.post(
            "/prima/tb4/forward_chunk",
            content=raw_bytes,
            headers={
                "Content-Type": "application/octet-stream",
                "X-Layer-Index": "16",
                "X-Chunk-Seq": "42"
            }
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["layer_idx"] == 16
        assert data["seq_id"] == 42
        assert data["bytes_received"] == len(raw_bytes)
        assert data["crc32"] == zlib.crc32(raw_bytes)
        assert data["zero_drop_verified"] is True
        assert data["dma_latency_ms"] < 0.30

    def test_v1_models_endpoint(self):
        r = self.client.get("/v1/models")
        assert r.status_code == 200
        data = r.json()
        assert "data" in data
        model_ids = [m["id"] for m in data["data"]]
        assert "bloom-560m" in model_ids
        assert "kimi-dev-72b" in model_ids

    def test_v1_chat_completions_proxy_fallback(self):
        payload = {
            "model": "bloom-560m",
            "messages": [{"role": "user", "content": "Benchmark TB4 DMA layer offload"}],
            "stream": False
        }
        r = self.client.post("/v1/chat/completions", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "tb4_dma_metadata" in data
        assert data["tb4_dma_metadata"]["dropped_chunks"] == 0
        assert data["tb4_dma_metadata"]["rtt_latency_ms"] < 0.30


class TestModuleLevelHelperFunctions:
    """Validates module-level convenience APIs."""

    def test_get_tb4_status_helper(self):
        st = get_tb4_status()
        assert isinstance(st, dict)
        assert st["tb4_interface"] == "bridge0"
        assert st["dropped_chunks"] == 0

    def test_offload_to_tb4_helper(self):
        ok = offload_to_tb4(list(range(12, 24)))
        assert ok is True

    def test_migrate_layers_helper(self):
        ok = migrate_layers("mac_host", "macbook_pro", 16, 24)
        assert ok is True
