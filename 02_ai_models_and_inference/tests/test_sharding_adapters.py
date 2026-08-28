#!/usr/bin/env python3
"""
02_ai_models_and_inference/tests/test_sharding_adapters.py
=========================================================
Comprehensive Test Suite for Modular Multi-Backend AI Sharding Adapters.
------------------------------------------------------------------------
Tests Petals DHT, llama.cpp RPC, Exo Ring P2P, and Accelerate LoRA
execution engines, quantization formats, failover routing, and cross-backend
tensor streaming.
"""

import math
import numpy as np
import pytest

from sharding_daemon.adapters import (
    BackendAdapter,
    TensorPayload,
    TensorDtype,
    CompressionMode,
    ShardSpec,
    AdapterStatus,
    PetalsAdapter,
    LlamaCppAdapter,
    GGUFQuantType,
    GGMLRpcCommand,
    ExoAdapter,
    RingStageState,
    AccelerateAdapter,
    create_adapter,
    list_available_backends,
    ADAPTER_REGISTRY,
)
from sharding_daemon.config import (
    MODEL_CATALOG,
    CLUSTER_NODES,
    get_model_catalog,
    get_node_spec,
    TransportTier,
)
from sharding_daemon.network_awareness import UnifiedNetworkAwarenessLayer


class TestTensorPayloadAndQuantization:
    """Validates tensor serialization, numerical quantization (FP16, INT8, NF4), and wire transit."""

    def test_tensor_payload_initialization(self):
        arr = np.random.randn(2, 8, 128).astype(np.float32)
        payload = TensorPayload(data=arr)
        assert payload.shape == (2, 8, 128)
        assert payload.sequence_len == 8
        assert payload.hidden_dim == 128
        assert payload.dtype == TensorDtype.FLOAT32
        assert payload.compression == CompressionMode.NONE
        assert payload.nbytes == arr.nbytes

    def test_fp16_compression_decompression(self):
        arr = np.random.randn(1, 16, 256).astype(np.float32)
        payload = TensorPayload(data=arr)
        compressed = payload.compress(CompressionMode.FP16)
        assert compressed.compression == CompressionMode.FP16
        assert compressed.dtype == TensorDtype.FLOAT16
        assert compressed.nbytes == arr.size * 2  # 2 bytes per float16

        decompressed = compressed.decompress()
        assert decompressed.compression == CompressionMode.NONE
        assert decompressed.dtype == TensorDtype.FLOAT32
        np.testing.assert_allclose(decompressed.data, arr, rtol=1e-3, atol=1e-3)

    def test_int8_symmetric_quantization(self):
        arr = np.random.uniform(-5.0, 5.0, (1, 32, 128)).astype(np.float32)
        payload = TensorPayload(data=arr)
        compressed = payload.compress(CompressionMode.INT8)
        assert compressed.compression == CompressionMode.INT8
        assert compressed.dtype == TensorDtype.INT8
        assert compressed.scale_factors is not None
        assert compressed.data.dtype == np.int8

        decompressed = compressed.decompress()
        assert decompressed.data.shape == arr.shape
        # INT8 error is bounded by quantization step (max_abs / 127)
        np.testing.assert_allclose(decompressed.data, arr, atol=0.1)

    def test_nf4_blockwise_quantization(self):
        arr = np.random.normal(0, 1.0, (1, 16, 128)).astype(np.float32)
        payload = TensorPayload(data=arr)
        compressed = payload.compress(CompressionMode.NF4)
        assert compressed.compression == CompressionMode.NF4
        assert compressed.dtype == TensorDtype.NF4
        assert compressed.scale_factors is not None
        # Data packed as 4-bit nibbles (2 per byte)
        assert compressed.data.dtype == np.uint8

        decompressed = compressed.decompress()
        assert decompressed.data.shape == arr.shape
        # NF4 normal float preserves Gaussian distribution with low MSE
        mse = np.mean((decompressed.data - arr) ** 2)
        assert mse < 0.05

    def test_binary_serialization_roundtrip(self):
        arr = np.random.randn(2, 4, 64).astype(np.float32)
        payload = TensorPayload(data=arr).compress(CompressionMode.INT8)
        raw_bytes = payload.to_bytes()
        assert isinstance(raw_bytes, bytes)
        assert len(raw_bytes) > 0

        restored = TensorPayload.from_bytes(raw_bytes)
        assert restored.shape == payload.shape
        assert restored.dtype == payload.dtype
        assert restored.compression == payload.compression
        np.testing.assert_array_equal(restored.data, payload.data)


class TestPetalsAdapter:
    """Validates Petals decentralized transformer block runner and DHT swarm routing."""

    def test_petals_adapter_lifecycle(self):
        adapter = PetalsAdapter(node_id="mac_host")
        assert adapter.get_backend_type() == "petals_dht"
        assert not adapter.is_loaded

        # Load Bloom 560M shard
        success = adapter.load_model_shard("bloom-560m", layer_range=(0, 6), device="mps")
        assert success is True
        assert adapter.is_loaded is True
        assert len(adapter.local_layers) == 6
        assert adapter.get_memory_usage_mb() > 0.0
        assert adapter.is_healthy() is True

        status = adapter.get_status()
        assert status.backend_type == "petals_dht"
        assert status.start_layer == 0
        assert status.end_layer == 6
        assert status.model_id == "bloom-560m"

    def test_petals_local_forward_step(self):
        adapter = PetalsAdapter(node_id="mac_host")
        adapter.load_model_shard("bloom-560m", layer_range=(0, 4), device="cpu")

        # Input hidden states (batch=1, seq_len=4, hidden_dim=1024)
        x_in = np.random.randn(1, 4, 1024).astype(np.float32)
        payload_in = TensorPayload(data=x_in)

        # Step through layer 0
        out_layer0 = adapter.forward_tensor_step(payload_in, layer_idx=0, session_id="test_sess_1")
        assert isinstance(out_layer0, TensorPayload)
        assert out_layer0.shape == (1, 4, 1024)
        assert not np.array_equal(out_layer0.data, x_in)  # Confirms transformation occurred
        assert not np.isnan(out_layer0.data).any()

        # Step through layer 1
        out_layer1 = adapter.forward_tensor_step(out_layer0, layer_idx=1, session_id="test_sess_1")
        assert out_layer1.shape == (1, 4, 1024)
        assert not np.isnan(out_layer1.data).any()

        # Range forward through layers 0 to 4
        range_out = adapter.forward_tensor_range(payload_in, start_layer=0, end_layer=4, session_id="test_sess_2")
        assert range_out.shape == (1, 4, 1024)

    def test_petals_remote_dht_block_routing(self):
        adapter = PetalsAdapter(node_id="mac_host")
        # Load local shard layers 0..4
        adapter.load_model_shard("bloom-560m", layer_range=(0, 4), device="cpu")

        # Request forward step on remote layer 30 (hosted on remote DHT peer)
        x_in = np.random.randn(1, 2, 1024).astype(np.float32)
        out_remote = adapter.forward_tensor_step(x_in, layer_idx=30)
        assert out_remote.shape == (1, 2, 1024)
        assert not np.isnan(out_remote.data).any()

    def test_petals_unload(self):
        adapter = PetalsAdapter(node_id="mac_host")
        adapter.load_model_shard("bloom-560m", layer_range=(0, 2))
        assert adapter.is_loaded is True
        adapter.unload_model_shard()
        assert adapter.is_loaded is False
        assert len(adapter.local_layers) == 0
        assert adapter.get_memory_usage_mb() == 0.0


class TestLlamaCppAdapter:
    """Validates llama.cpp Metal GPU RPC and GGUF quantization sharding."""

    def test_llamacpp_adapter_lifecycle(self):
        adapter = LlamaCppAdapter(node_id="mac_host", config={"quant_type": "Q4_K_M"})
        assert adapter.get_backend_type() == "llamacpp_rpc"

        # Compute tensor split for Kimi-Dev-72B
        splits, ts_str = adapter.compute_tensor_split("kimi-dev-72b")
        assert "mac_host" in splits
        assert len(ts_str.split(",")) == 3

        # Load shard
        success = adapter.load_model_shard("kimi-dev-72b", layer_range=(0, 24), device="mps")
        assert success is True
        assert adapter.is_loaded is True
        assert adapter.get_memory_usage_mb() > 0.0
        assert adapter.is_healthy() is True

    def test_llamacpp_forward_step_and_rpc(self):
        adapter = LlamaCppAdapter(node_id="mac_host", config={"quant_type": "Q4_K_M"})
        adapter.load_model_shard("bloom-560m", layer_range=(0, 4), device="mps")

        # Local Metal step
        x_in = np.random.randn(1, 4, 1024).astype(np.float32)
        out_local = adapter.forward_tensor_step(x_in, layer_idx=1)
        assert out_local.shape == (1, 4, 1024)
        assert not np.isnan(out_local.data).any()

        # Remote RPC step (layer 35 outside local shard)
        out_rpc = adapter.forward_tensor_step(x_in, layer_idx=35)
        assert out_rpc.shape == (1, 4, 1024)
        assert not np.isnan(out_rpc.data).any()

    def test_llamacpp_rpc_packet_creation(self):
        adapter = LlamaCppAdapter(node_id="mac_host")
        raw_tensor = np.ones((8, 8), dtype=np.float32).tobytes()
        frame = adapter.create_rpc_packet(GGMLRpcCommand.RUN_GRAPH, tensor_id=42, payload=raw_tensor)
        assert isinstance(frame, bytes)
        assert len(frame) == 13 + len(raw_tensor)  # 1B cmd + 4B id + 8B len + payload


class TestExoAdapter:
    """Validates Exo dynamic P2P ring pipeline partitioning and self-healing failover."""

    def test_exo_ring_topology_and_partitioning(self):
        adapter = ExoAdapter(node_id="mac_host")
        assert adapter.get_backend_type() == "exo_p2p"
        assert len(adapter.ring_order) == 4

        partitions = adapter.auto_partition_layers(total_layers=80)
        assert len(partitions) == 4
        # Total sum of layers must equal 80
        total_assigned = sum(e - s for s, e in partitions.values())
        assert total_assigned == 80

    def test_exo_load_and_forward_step(self):
        adapter = ExoAdapter(node_id="mac_host")
        success = adapter.load_model_shard("bloom-560m", layer_range=(0, 6), device="mps")
        assert success is True
        assert adapter.is_loaded is True

        x_in = np.random.randn(1, 3, 1024).astype(np.float32)
        out_step = adapter.forward_tensor_step(x_in, layer_idx=0)
        assert out_step.shape == (1, 3, 1024)
        assert not np.isnan(out_step.data).any()
        assert adapter.stage_state == RingStageState.STAGE_COMPLETE

    def test_exo_thermal_failover_ring_reconstruction(self):
        adapter = ExoAdapter(node_id="mac_host")
        adapter.load_model_shard("kimi-dev-72b", layer_range=(0, 24))
        orig_nodes = list(adapter.ring_order)

        # Trigger thermal cutoff (>41°C) on linux_node
        adapter.trigger_thermal_failover("linux_node", temperature_c=44.2)
        assert "linux_node" not in adapter.ring_order
        assert len(adapter.ring_order) == len(orig_nodes) - 1
        assert adapter.fallback_mode is True

        # Forward pass continues successfully on reconstructed ring
        x_in = np.random.randn(1, 2, 8192).astype(np.float32)
        out_step = adapter.forward_tensor_step(x_in, layer_idx=0)
        assert out_step.shape == (1, 2, 8192)


class TestAccelerateAdapter:
    """Validates Accelerate model parallelism device maps and continuous LoRA training."""

    def test_accelerate_device_mapping(self):
        adapter = AccelerateAdapter(node_id="mac_host")
        assert adapter.get_backend_type() == "accelerate_lora"

        d_map = adapter.compute_auto_device_map(total_layers=80, hidden_dim=4096)
        assert len(d_map) == 80
        assert "mps:0" in d_map.values()

    def test_accelerate_lora_forward_and_training(self):
        adapter = AccelerateAdapter(node_id="mac_host", config={"lora_r": 16, "lora_alpha": 32.0})
        success = adapter.load_model_shard("bloom-560m", layer_range=(0, 4), device="mps")
        assert success is True
        assert adapter.is_loaded is True

        x_in = np.random.randn(1, 4, 1024).astype(np.float32)
        out_forward = adapter.forward_tensor_step(x_in, layer_idx=0)
        assert out_forward.shape == (1, 4, 1024)
        assert not np.isnan(out_forward.data).any()

        # Execute continuous LoRA training step
        target = x_in + 0.1
        loss = adapter.train_step(x_in, target, layer_idx=0)
        assert isinstance(loss, float)
        assert loss >= 0.0
        assert adapter.training_steps == 1

        # Test LoRA weight merging and unmerging
        adapter.merge_lora_weights()
        assert adapter.lora_adapters[0]["q_proj"].is_merged is True
        adapter.unmerge_lora_weights()
        assert adapter.lora_adapters[0]["q_proj"].is_merged is False


class TestAdapterFactoryAndInteroperability:
    """Validates factory generation and cross-adapter tensor pipeline handoffs."""

    @pytest.mark.parametrize("backend_key", ["petals_dht", "llamacpp_rpc", "exo_p2p", "accelerate_lora"])
    def test_factory_instantiation(self, backend_key):
        adapter = create_adapter(backend_key, node_id="mac_host")
        assert isinstance(adapter, BackendAdapter)
        assert adapter.get_backend_type() in ADAPTER_REGISTRY

    def test_cross_backend_pipeline_streaming(self):
        """Streams a tensor activation across Petals -> llama.cpp -> Exo -> Accelerate."""
        p_adapter = create_adapter("petals_dht", node_id="mac_host")
        l_adapter = create_adapter("llamacpp_rpc", node_id="mac_host")
        e_adapter = create_adapter("exo_p2p", node_id="mac_host")
        a_adapter = create_adapter("accelerate_lora", node_id="mac_host")

        p_adapter.load_model_shard("bloom-560m", (0, 2))
        l_adapter.load_model_shard("bloom-560m", (2, 4))
        e_adapter.load_model_shard("bloom-560m", (4, 6))
        a_adapter.load_model_shard("bloom-560m", (6, 8))

        # Initial prompt tokens
        x_init = np.random.randn(1, 4, 1024).astype(np.float32)
        t0 = TensorPayload(data=x_init)

        # Stage 1: Petals
        t1 = p_adapter.forward_tensor_step(t0, layer_idx=0)
        # Stage 2: llama.cpp
        t2 = l_adapter.forward_tensor_step(t1, layer_idx=2)
        # Stage 3: Exo
        t3 = e_adapter.forward_tensor_step(t2, layer_idx=4)
        # Stage 4: Accelerate
        t4 = a_adapter.forward_tensor_step(t3, layer_idx=6)

        assert t4.shape == (1, 4, 1024)
        assert not np.isnan(t4.data).any()
        assert t4.sequence_len == 4
        assert t4.hidden_dim == 1024

    def test_unal_attachment(self):
        adapter = create_adapter("petals_dht", node_id="mac_host")
        unal = UnifiedNetworkAwarenessLayer()
        adapter.set_network_awareness(unal)
        assert adapter.network_awareness is unal
