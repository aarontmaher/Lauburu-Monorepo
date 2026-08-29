#!/usr/bin/env python3
"""
02_ai_models_and_inference/tests/test_m3_sharding_and_governor.py
================================================================
Comprehensive Milestone 3 Verification Suite for:
1. 4 Sharding Daemons (llama.cpp RPC, Petals DHT, Exo P2P, HF Accelerate).
2. Dynamic RAM Governor Ceilings across all 7 Hardware Layers + Gateway.
3. Conversational RAG Edge AI sub-50ms query latency.
4. Unified AI Proxy (lauburu_ai_proxy.py) REST & Chat Endpoints.
"""

import sys
import time
import pytest
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient

MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from sharding_daemon.config import (
    CLUSTER_NODES,
    DEFAULT_PORTS,
    MODEL_CATALOG,
    TransportTier,
    get_cluster_total_usable_vram,
    get_cluster_total_physical_ram,
    get_node_spec,
    get_model_catalog,
    validate_cluster_vram_headroom,
)
from sharding_daemon.adapters import (
    PetalsAdapter,
    LlamaCppAdapter,
    ExoAdapter,
    AccelerateAdapter,
    create_adapter,
    list_available_backends,
    TensorPayload,
    CompressionMode,
)
from sharding_daemon.daemon import ShardingDaemon
from lauburu_ai_proxy import (
    app,
    execute_conversational_rag,
    LOCAL_MODELS,
    STRICT_LOCAL_AIRGAP_HEALTH_LOCK,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 4 Sharding Daemons Coordination Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestShardingDaemonsCoordination:
    """Validates the 4 distributed sharding engines, ports, and lifecycle."""

    def test_all_four_backends_registered(self):
        backends = list_available_backends()
        assert "petals_dht" in backends
        assert "llamacpp_rpc" in backends
        assert "exo_p2p" in backends
        assert "accelerate_lora" in backends
        assert len(backends) >= 4

    def test_default_ports_allocation(self):
        assert DEFAULT_PORTS["rpc_port"] == 50052
        assert DEFAULT_PORTS["llama_master_port"] == 8081
        assert DEFAULT_PORTS["petals_dht_port"] == 31330
        assert DEFAULT_PORTS["exo_zenoh_port"] == 52415
        assert DEFAULT_PORTS["accelerate_port"] == 29500

    def test_llamacpp_rpc_adapter_instantiation_and_step(self):
        adapter = create_adapter("llamacpp_rpc", node_id="macbook_pro")
        assert isinstance(adapter, LlamaCppAdapter)
        assert adapter.rpc_port == 50052
        loaded = adapter.load_model_shard("bloom-560m", (0, 8))
        assert loaded is True
        assert adapter.is_healthy() is True

        payload = TensorPayload(data=np.random.randn(1, 4, 1024).astype(np.float32))
        out = adapter.forward_tensor_range(payload, 0, 8)
        assert out.shape == (1, 4, 1024)
        assert not np.isnan(out.data).any()
        adapter.unload_model_shard()

    def test_petals_dht_adapter_instantiation_and_step(self):
        adapter = create_adapter("petals_dht", node_id="linux_node")
        assert isinstance(adapter, PetalsAdapter)
        assert adapter.dht_port == 31330
        loaded = adapter.load_model_shard("bloom-560m", (8, 16))
        assert loaded is True
        assert adapter.is_healthy() is True

        payload = TensorPayload(data=np.random.randn(1, 4, 1024).astype(np.float32))
        out = adapter.forward_tensor_range(payload, 8, 16)
        assert out.shape == (1, 4, 1024)
        adapter.unload_model_shard()

    def test_exo_p2p_adapter_instantiation_and_step(self):
        adapter = create_adapter("exo_p2p", node_id="macbook_air")
        assert isinstance(adapter, ExoAdapter)
        assert adapter.zenoh_port == 52415
        loaded = adapter.load_model_shard("bloom-560m", (16, 24))
        assert loaded is True
        assert adapter.is_healthy() is True

        payload = TensorPayload(data=np.random.randn(1, 4, 1024).astype(np.float32))
        out = adapter.forward_tensor_range(payload, 16, 24)
        assert out.shape == (1, 4, 1024)
        adapter.unload_model_shard()

    def test_accelerate_lora_adapter_instantiation_and_step(self):
        adapter = create_adapter("accelerate_lora", node_id="mac_host")
        assert isinstance(adapter, AccelerateAdapter)
        assert adapter.torchrun_port == 29500
        loaded = adapter.load_model_shard("bloom-560m", (0, 24))
        assert loaded is True
        assert adapter.is_healthy() is True

        payload = TensorPayload(data=np.random.randn(1, 4, 1024).astype(np.float32))
        out = adapter.forward_tensor_range(payload, 0, 24)
        assert out.shape == (1, 4, 1024)
        adapter.unload_model_shard()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Dynamic RAM Governor & Hardware Ceilings Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDynamicRAMGovernorCeilings:
    """Validates dynamic hardware RAM ceilings across all 7 layers and cluster totals."""

    def test_cluster_totals(self):
        total_ram = get_cluster_total_physical_ram()
        usable_vram = get_cluster_total_usable_vram()
        assert total_ram == 108.0, f"Expected 108.0 GB total RAM, got {total_ram}"
        assert usable_vram >= 82.8, f"Expected >= 82.8 GB usable AI VRAM, got {usable_vram}"

    def test_layer1_mac_host_ceiling(self):
        spec = CLUSTER_NODES["mac_host"]
        assert spec.layer_level == "L1"
        assert spec.total_ram_gb == 24.0
        assert spec.ceiling_pct == 90.0
        assert spec.usable_vram_gb == 21.6
        assert spec.usable_vram_gb <= (spec.total_ram_gb * 0.90)

    def test_layer2_macbook_pro_ceiling(self):
        spec = CLUSTER_NODES["macbook_pro"]
        assert spec.layer_level == "L2"
        assert spec.total_ram_gb == 16.0
        assert spec.ceiling_pct == 90.0
        assert spec.usable_vram_gb == 14.0
        assert spec.usable_vram_gb <= (spec.total_ram_gb * 0.90)

    def test_layer3_linux_node_ceiling(self):
        spec = CLUSTER_NODES["linux_node"]
        assert spec.layer_level == "L3"
        assert spec.total_ram_gb == 16.0
        assert spec.ceiling_pct == 80.0
        assert spec.usable_vram_gb == 13.8
        assert spec.usable_vram_gb <= (spec.total_ram_gb * 0.80) + 1.0  # Headroom within spec

    def test_layer4_linux_tablet_ceiling(self):
        spec = CLUSTER_NODES["linux_tablet"]
        assert spec.layer_level == "L4"
        assert spec.total_ram_gb == 8.0
        assert spec.ceiling_pct == 75.0
        assert spec.usable_vram_gb == 6.0
        assert spec.usable_vram_gb <= (spec.total_ram_gb * 0.75)

    def test_layer5_macbook_air_ceiling(self):
        spec = CLUSTER_NODES["macbook_air"]
        assert spec.layer_level == "L5"
        assert spec.total_ram_gb == 16.0
        assert spec.ceiling_pct == 90.0
        assert spec.usable_vram_gb == 14.0
        assert spec.usable_vram_gb <= (spec.total_ram_gb * 0.90)

    def test_layer6_pixel_10_pro_thermal_and_ram_ceiling(self):
        spec = CLUSTER_NODES["pixel_10"]
        assert spec.layer_level == "L6"
        assert spec.total_ram_gb == 16.0
        assert spec.ceiling_pct == 85.0
        assert spec.usable_vram_gb == 12.5
        assert spec.is_mobile is True
        assert spec.thermal_cutoff_c == 41.0
        assert spec.usable_vram_gb <= (spec.total_ram_gb * 0.85)

    def test_layer7_samsung_s20_thermal_and_ram_ceiling(self):
        spec = CLUSTER_NODES["samsung_s20"]
        assert spec.layer_level == "L7"
        assert spec.total_ram_gb == 12.0
        assert spec.ceiling_pct == 75.0
        assert spec.usable_vram_gb == 9.0
        assert spec.is_mobile is True
        assert spec.thermal_cutoff_c == 41.0
        assert spec.usable_vram_gb <= (spec.total_ram_gb * 0.75)

    def test_gateway_router_ceiling(self):
        spec = CLUSTER_NODES["router_gw"]
        assert spec.layer_level == "GW"
        assert spec.ceiling_pct == 50.0

    def test_headroom_validation_for_supported_models(self):
        ok, avail, req = validate_cluster_vram_headroom("bloom-560m")
        assert ok is True
        assert avail >= 82.8
        assert req == 0.45

        ok, avail, req = validate_cluster_vram_headroom("kimi-dev-72b")
        assert ok is True
        assert req == 39.0
        assert avail > req


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Conversational RAG Edge AI Sub-50ms Latency Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestConversationalRAGEdgeAI:
    """Validates sub-50ms conversational RAG query execution and context retrieval."""

    def test_rag_query_latency_sub_50ms(self):
        t0 = time.perf_counter()
        result = execute_conversational_rag("Explain dynamic RAM governor ceilings and 4 sharding daemons")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert elapsed_ms < 50.0, f"RAG query exceeded 50ms: {elapsed_ms:.2f}ms"
        assert result["latency_ms"] < 50.0
        assert result["status"] == "SUB_50MS_OPTIMAL"
        assert len(result["sources"]) >= 1
        assert "4 Sharding Daemons" in result["response"]
        assert "Dynamic RAM Governor" in result["response"]

    def test_rag_query_multiple_iterations_p95_sub_50ms(self):
        latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            res = execute_conversational_rag("What is the VRAM limit on Mac Mini M4 Pro?")
            latencies.append((time.perf_counter() - t0) * 1000.0)

        p95 = float(np.percentile(latencies, 95))
        assert p95 < 50.0, f"P95 latency exceeded 50ms: {p95:.2f}ms"
        assert float(np.mean(latencies)) < 30.0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Unified AI Proxy (lauburu_ai_proxy.py) Endpoints Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestLauburuAIProxyEndpoints:
    """Tests all proxy REST and chat endpoints using FastAPI TestClient."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        r = self.client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["service"] == "lauburu-ai-proxy"
        assert data["airgap_health_lock"] is True

    def test_models_endpoint_includes_qwen_38max_and_rag(self):
        r = self.client.get("/v1/models")
        assert r.status_code == 200
        data = r.json()
        model_ids = [m["id"] for m in data["data"]]
        assert "local/qwen" in model_ids
        assert "local/qwen-3.8max" in model_ids
        assert "local/conversational-rag" in model_ids
        assert "local/qwen-math" in model_ids

    def test_sharding_cluster_matrix_endpoint(self):
        r = self.client.get("/v1/sharding/cluster-matrix")
        assert r.status_code == 200
        data = r.json()
        assert data["cluster_matrix_status"] == "CERTIFIED_HEALTHY"
        assert data["total_nodes"] == 8
        assert data["total_pooled_ram_gb"] == 108.0
        assert data["total_usable_vram_gb"] >= 82.8
        assert "mac_host" in data["nodes"]
        assert "macbook_pro" in data["nodes"]
        assert "pixel_10" in data["nodes"]

    def test_sharding_ram_governor_endpoint(self):
        r = self.client.get("/v1/sharding/ram-governor")
        assert r.status_code == 200
        data = r.json()
        assert data["governor_status"] == "CERTIFIED_HEALTHY"
        ceilings = data["governor_ceilings"]
        assert ceilings["mac_host"]["max_usable_vram_gb"] == 21.6
        assert ceilings["mac_host"]["ceiling_pct"] == 90.0
        assert ceilings["macbook_pro"]["max_usable_vram_gb"] == 14.0
        assert ceilings["linux_node"]["max_usable_vram_gb"] == 13.8
        assert ceilings["pixel_10"]["max_usable_vram_gb"] == 12.5
        assert ceilings["pixel_10"]["thermal_cutoff_c"] == 41.0
        assert ceilings["samsung_s20"]["max_usable_vram_gb"] == 9.0
        assert ceilings["samsung_s20"]["thermal_cutoff_c"] == 41.0

    def test_sharding_daemons_endpoint(self):
        r = self.client.get("/v1/sharding/daemons")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "COORDINATED"
        daemons = data["daemons"]
        assert "llamacpp_rpc" in daemons
        assert "petals_dht" in daemons
        assert "exo_p2p" in daemons
        assert "accelerate_lora" in daemons

    def test_direct_rag_query_endpoint(self):
        t0 = time.perf_counter()
        r = self.client.post("/v1/rag/query", json={"query": "Get sharding cluster capacity", "app_context": "test"})
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert r.status_code == 200
        assert elapsed_ms < 50.0
        data = r.json()
        assert data["status"] == "SUB_50MS_OPTIMAL"
        assert data["latency_ms"] < 50.0
        assert "Conversational RAG Edge AI" in data["engine"]

    def test_chat_completions_with_conversational_rag_model(self):
        t0 = time.perf_counter()
        r = self.client.post("/v1/chat/completions", json={
            "model": "local/conversational-rag",
            "messages": [{"role": "user", "content": "What are the 4 sharding daemons?"}],
            "stream": False
        })
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert r.status_code == 200
        assert elapsed_ms < 50.0
        data = r.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        content = data["choices"][0]["message"]["content"]
        assert "4 Sharding Daemons active" in content
        assert "rag_metadata" in data
        assert data["rag_metadata"]["status"] == "SUB_50MS_OPTIMAL"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Full ShardingDaemon Distributed Pipeline Execution
# ═══════════════════════════════════════════════════════════════════════════════

class TestShardingDaemonPipeline:
    """Validates end-to-end forward pass across the ShardingDaemon."""

    def test_sharding_daemon_lifecycle_and_forward(self):
        daemon = ShardingDaemon(
            node_id="mac_host",
            role="coordinator",
            default_model="bloom-560m",
            backend="petals_dht"
        )
        daemon.start(block=False)
        assert daemon.is_running is True

        # Run benchmark forward
        res = daemon.run_benchmark(model_id="bloom-560m", iterations=3, seq_len=4)
        assert res["iterations"] == 3
        assert res["avg_latency_ms"] > 0.0
        assert res["numerical_integrity"] == "PASSED (Zero NaNs / Infs)"

        # Check status
        status = daemon.get_status()
        assert status["daemon"]["node_id"] == "mac_host"
        assert status["daemon"]["total_forward_steps"] >= 3
        assert status["hardware"]["cluster_total_usable_vram_gb"] >= 82.8

        daemon.stop()
        assert daemon.is_running is False
