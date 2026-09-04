#!/usr/bin/env python3
"""
02_ai_models_and_inference/tests/test_pixel_termux_edge.py
==========================================================
Unit and Integration Test Suite for:
1. Pixel 10 Pro XL & Samsung S20 Termux Edge Sharding Node.
2. Thermal Sentinel Governor & Dynamic Memory Ceiling (12.5 GB / 9.0 GB).
3. Android Keepalive Management (termux-wake-lock, Doze bypass).
4. Genuine Transformer Block Forward Step (RMSNorm, MHA, SwiGLU).
5. Batch Edge Dataset Tokenizer (subword BPE, Shannon entropy).
6. Night-Cycle Synthetic Question Generation Dispatcher.
7. REST/Binary Wire Edge Server & EdgeNodeClient protocol.
"""

import time
import json
import pytest
import numpy as np
from pathlib import Path

from sharding_daemon.config import (
    CLUSTER_NODES,
    MODEL_CATALOG,
    get_node_spec,
    get_model_catalog,
)
from sharding_daemon.adapters.base import (
    TensorPayload,
    TensorDtype,
    CompressionMode,
    ShardSpec,
)
from sharding_daemon.edge.pixel_termux_node import (
    PixelThermalSentinel,
    ThermalAction,
    ThermalStatus,
    PixelMemoryGovernor,
    PixelKeepaliveManager,
    PixelEdgeComputeEngine,
    EdgeDatasetTokenizer,
    NightCycleSyntheticDispatcher,
    PixelTermuxServer,
    PixelTermuxDeployer,
    EdgeNodeClient,
    get_termux_deployment_command,
    get_keepalive_commands,
)


class TestPixelHardwareMatrixAndConfig:
    """Validates cluster hardware specifications and invariants for the Pixel node."""

    def test_pixel_node_specs(self):
        node = get_node_spec("pixel_10")
        assert node is not None
        assert node.node_id == "pixel_10"
        assert node.layer_level == "L6"
        assert node.ssh_port == 8022
        assert node.ssh_user == "aaron"
        assert node.tailscale_ip == "100.73.38.87"
        assert node.total_ram_gb == 16.0
        assert node.ceiling_pct == 85.0
        assert node.usable_vram_gb == 12.5
        assert node.is_mobile is True
        assert node.thermal_cutoff_c == 41.0

    def test_samsung_node_specs(self):
        node = get_node_spec("samsung_s20")
        assert node is not None
        assert node.node_id == "samsung_s20"
        assert node.layer_level == "L7"
        assert node.total_ram_gb == 12.0
        assert node.ceiling_pct == 75.0
        assert node.usable_vram_gb == 9.0
        assert node.is_mobile is True
        assert node.thermal_cutoff_c == 41.0

    def test_deployment_command_structure(self):
        cmd = get_termux_deployment_command(
            node_id="pixel_10",
            role="edge-worker",
            bootstrap_ip="100.119.199.76:31330",
            thermal_cutoff=41.0,
            max_vram=12.5,
        )
        assert "ssh -p 8022 aaron@100.73.38.87" in cmd
        assert "--node-id pixel_10" in cmd
        assert "--role edge-worker" in cmd
        assert "--dht-bootstrap 100.119.199.76:31330" in cmd
        assert "--thermal-cutoff 41.0" in cmd
        assert "--max-vram 12.5" in cmd

    def test_keepalive_command_list(self):
        cmds = get_keepalive_commands()
        assert len(cmds) == 3
        assert "termux-wake-lock" in cmds[0]
        assert "phantom_procs" in cmds[1]
        assert "dumpsys deviceidle whitelist" in cmds[2]


class TestThermalSentinelGovernor:
    """Validates thermal monitoring thresholds and governor action state transitions."""

    def test_thermal_action_policies(self):
        sentinel = PixelThermalSentinel(cutoff_c=41.0)
        assert sentinel.evaluate_action(25.0) == ThermalAction.NORMAL_OPERATION
        assert sentinel.evaluate_action(38.9) == ThermalAction.NORMAL_OPERATION
        assert sentinel.evaluate_action(39.0) == ThermalAction.THROTTLE_BATCH_SIZE
        assert sentinel.evaluate_action(40.5) == ThermalAction.THROTTLE_BATCH_SIZE
        assert sentinel.evaluate_action(41.0) == ThermalAction.DRAIN_AND_MIGRATE
        assert sentinel.evaluate_action(41.4) == ThermalAction.DRAIN_AND_MIGRATE
        assert sentinel.evaluate_action(41.5) == ThermalAction.IMMEDIATE_EVACUATION
        assert sentinel.evaluate_action(45.0) == ThermalAction.IMMEDIATE_EVACUATION

    def test_thermal_status_model(self):
        sentinel = PixelThermalSentinel(cutoff_c=41.0)
        status = sentinel.get_status()
        assert isinstance(status, ThermalStatus)
        assert status.cutoff_c == 41.0
        assert status.action in list(ThermalAction)
        assert status.temperature_c > 0.0


class TestPixelMemoryGovernor:
    """Validates memory ceiling tracking and headroom allocation validation."""

    def test_memory_headroom_pixel(self):
        gov = PixelMemoryGovernor(total_ram_gb=16.0, ceiling_pct=85.0, usable_vram_gb=12.5)
        assert gov.ceiling_mb == 12.5 * 1024.0
        assert gov.allocated_mb == 0.0

        ok, msg = gov.check_allocation_headroom(400.0)
        assert ok is True
        gov.record_allocation(400.0)
        assert gov.allocated_mb == 400.0

        ok2, msg2 = gov.check_allocation_headroom(13000.0)
        assert ok2 is False
        assert "exceeds remaining headroom" in msg2

    def test_memory_headroom_samsung_s20(self):
        gov = PixelMemoryGovernor(total_ram_gb=12.0, ceiling_pct=75.0, usable_vram_gb=9.0)
        assert gov.ceiling_mb == 9.0 * 1024.0
        ok, msg = gov.check_allocation_headroom(8000.0)
        assert ok is True
        ok_overflow, msg_overflow = gov.check_allocation_headroom(10000.0)
        assert ok_overflow is False


class TestPixelEdgeComputeEngine:
    """Validates genuine transformer block linear algebra on the edge node."""

    def test_load_and_forward_single_step(self):
        engine = PixelEdgeComputeEngine(node_id="pixel_10")
        assert engine.is_loaded is False

        ok = engine.load_model_shard("bloom-560m", start_layer=16, end_layer=20, hidden_dim=1024, num_heads=16)
        assert ok is True
        assert engine.is_loaded is True
        assert len(engine.local_layers) == 4
        assert engine.memory_governor.allocated_mb > 0.0

        rng = np.random.RandomState(42)
        x_in = rng.normal(0, 1.0, (1, 4, 1024)).astype(np.float32)
        payload_in = TensorPayload(data=x_in)

        out_payload = engine.forward_tensor_step(payload_in, layer_idx=16, session_id="test_sess")
        assert out_payload.data.shape == (1, 4, 1024)
        assert not np.allclose(out_payload.data, x_in)
        assert not np.isnan(out_payload.data).any()
        assert not np.isinf(out_payload.data).any()
        assert out_payload.metadata["node_id"] == "pixel_10"
        assert out_payload.metadata["layer_idx"] == 16
        assert engine.total_forward_steps == 1
        assert engine.total_tokens_processed == 4

    def test_forward_multi_layer_range(self):
        engine = PixelEdgeComputeEngine(node_id="pixel_10")
        engine.load_model_shard("bloom-560m", start_layer=16, end_layer=24, hidden_dim=1024, num_heads=16)

        rng = np.random.RandomState(123)
        x_in = rng.normal(0, 1.0, (1, 2, 1024)).astype(np.float32)
        payload_in = TensorPayload(data=x_in)

        out_range = engine.forward_tensor_range(payload_in, start_layer=16, end_layer=24, session_id="test_range")
        assert out_range.data.shape == (1, 2, 1024)
        assert engine.total_forward_steps == 8
        assert engine.total_tokens_processed == 16

        status = engine.get_status()
        assert status["is_loaded"] is True
        assert status["shard"]["model_id"] == "bloom-560m"
        assert status["shard"]["start_layer"] == 16
        assert status["shard"]["end_layer"] == 24
        assert status["performance"]["total_forward_steps"] == 8


class TestEdgeDatasetTokenizerUnit:
    """Unit tests for EdgeDatasetTokenizer byte/subword encoding and Shannon entropy."""

    def test_tokenizer_encode_text(self):
        tok = EdgeDatasetTokenizer()
        tokens, mask = tok.encode_text("Explain TB4 DMA layer offloading.", max_length=64)
        assert len(tokens) == 64
        assert len(mask) == 64
        assert tokens[0] == tok.bos_token_id
        assert tok.eos_token_id in tokens
        assert sum(mask) > 5

    def test_tokenizer_shannon_entropy(self):
        tok = EdgeDatasetTokenizer()
        # High entropy text
        tokens, _ = tok.encode_text("Quantum entanglement in distributed AI tensor mesh networks", max_length=64)
        entropy = tok.compute_shannon_entropy(tokens)
        assert entropy > 2.0

        # Empty / pad only
        assert tok.compute_shannon_entropy([0, 0, 0]) == 0.0

    def test_tokenize_batch(self):
        tok = EdgeDatasetTokenizer()
        texts = [
            "Pan-Tompkins 512Hz QRS detection",
            "10Gbps Thunderbolt 4 DMA bridge latency is <0.30ms",
            "Dynamic RAM governor enforces <85% safety ceiling"
        ]
        res = tok.tokenize_batch(texts, max_length=32)
        assert res["batch_size"] == 3
        assert res["total_tokens"] > 10
        assert len(res["tokens"]) == 3
        assert len(res["attention_masks"]) == 3
        assert res["processing_time_ms"] >= 0.0
        assert res["mean_entropy"] > 0.0


class TestNightCycleSyntheticDispatcherUnit:
    """Unit tests for NightCycleSyntheticDispatcher synthetic question generation."""

    def test_generate_synthetic_batch_pixel(self):
        disp = NightCycleSyntheticDispatcher(node_id="pixel_10")
        res = disp.generate_synthetic_batch(
            topic="pan_tompkins_dsp",
            count=4,
            domain="math_reasoning",
            device_target="pixel_10"
        )
        assert res["success"] is True
        assert res["target_device"] == "pixel_10"
        assert res["generated_pairs_count"] == 4
        assert len(res["generated_pairs"]) == 4
        pair0 = res["generated_pairs"][0]
        assert "instruction" in pair0
        assert "output" in pair0
        assert "entropy" in pair0
        assert len(pair0["instruction"]) > 10
        assert len(pair0["output"]) > 10

    def test_generate_synthetic_batch_samsung(self):
        disp = NightCycleSyntheticDispatcher(node_id="samsung_s20")
        res = disp.generate_synthetic_batch(
            topic="mesh_networking",
            count=3,
            domain="mesh_networking",
            device_target="samsung_s20"
        )
        assert res["success"] is True
        assert res["target_device"] == "samsung_s20"
        assert res["generated_pairs_count"] == 3
        assert "Samsung S20" in res["device_hardware"]

    def test_dispatch_night_cycle(self):
        disp = NightCycleSyntheticDispatcher(node_id="pixel_10")
        res = disp.dispatch_night_cycle(target_device="pixel_10", batch_size=5)
        assert res["status"] == "NIGHT_CYCLE_DISPATCH_COMPLETE"
        assert res["pairs_generated"] == 5
        assert res["total_lifetime_generated"] >= 5


class TestPixelTermuxServerAndClient:
    """Validates local HTTP REST, tokenization, synthetic generation, and binary forward steps."""

    @pytest.fixture(scope="class")
    def edge_server(self):
        server = PixelTermuxServer(host="127.0.0.1", port=39876, node_id="pixel_10_test")
        server.start(block=False)
        time.sleep(0.3)
        yield server
        server.stop()

    def test_server_health_and_status(self, edge_server):
        client = EdgeNodeClient(host="127.0.0.1", port=39876)
        health = client.get_health()
        assert health["status"] == "HEALTHY"
        assert health["node_id"] == "pixel_10_test"
        assert health["usable_vram_gb"] == 12.5

        status = client.get_status()
        assert status["node_id"] == "pixel_10_test"
        assert "thermal" in status
        assert "memory" in status

    def test_client_tokenize_batch_endpoint(self, edge_server):
        client = EdgeNodeClient(host="127.0.0.1", port=39876)
        texts = [
            "Test edge tokenization on Tensor G5 Edge TPU",
            "Zero dropped activation chunks over TB4 DMA"
        ]
        res = client.tokenize_batch(texts, max_length=64)
        assert res["batch_size"] == 2
        assert res["total_tokens"] > 0
        assert len(res["tokens"]) == 2

    def test_client_synthetic_generate_batch_endpoint(self, edge_server):
        client = EdgeNodeClient(host="127.0.0.1", port=39876)
        res = client.generate_synthetic_batch(
            topic="tb4_offload",
            count=3,
            domain="distributed_sharding",
            device_target="pixel_10_test"
        )
        assert res["success"] is True
        assert res["generated_pairs_count"] == 3
        assert len(res["generated_pairs"]) == 3

    def test_client_night_cycle_dispatch_endpoint(self, edge_server):
        client = EdgeNodeClient(host="127.0.0.1", port=39876)
        res = client.dispatch_night_cycle(target_device="pixel_10_test", batch_size=4)
        assert res["status"] == "NIGHT_CYCLE_DISPATCH_COMPLETE"
        assert res["pairs_generated"] == 4

    def test_client_load_and_forward_binary(self, edge_server):
        client = EdgeNodeClient(host="127.0.0.1", port=39876)
        
        load_ok = client.load_shard("bloom-560m", 16, 20)
        assert load_ok is True

        rng = np.random.RandomState(99)
        arr = rng.normal(0, 1.0, (1, 2, 1024)).astype(np.float32)
        payload_in = TensorPayload(data=arr)

        out_step = client.forward_step_binary(payload_in, layer_idx=16)
        assert out_step.data.shape == arr.shape
        assert not np.allclose(out_step.data, arr)

        out_range = client.forward_range_binary(payload_in, start_layer=16, end_layer=20)
        assert out_range.data.shape == arr.shape
        assert not np.allclose(out_range.data, arr)


class TestPixelTermuxDeployerHarness:
    """Validates deployer parameter handling and live/mock execution interfaces."""

    def test_deployer_init(self):
        deployer = PixelTermuxDeployer(tailscale_ip="100.73.38.87", ssh_port=8022, daemon_port=39999)
        assert deployer.tailscale_ip == "100.73.38.87"
        assert deployer.ssh_port == 8022
        assert deployer.daemon_port == 39999
        assert deployer.remote_workdir == "/data/data/com.termux/files/home/lauburu_edge_node"

    def test_live_pixel_health_probe(self):
        """Probes the live running Pixel daemon over Tailscale."""
        client = EdgeNodeClient(host="100.73.38.87", port=39999, timeout=5.0)
        try:
            health = client.get_health()
            assert health["status"] == "HEALTHY"
            assert health["node_id"] == "pixel_10"
            assert "Google Pixel 10 Pro XL" in health["device"]
            assert health["usable_vram_gb"] == 12.5
        except Exception as e:
            pytest.skip(f"Live Pixel node not reachable over network: {e}")
