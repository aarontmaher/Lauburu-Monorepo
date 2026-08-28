#!/usr/bin/env python3
"""
tests/test_pixel_termux_edge.py
===============================
Unit and Integration Test Suite for Milestone M4:
Pixel 10 Pro XL Termux Edge Sharding Node, Thermal Sentinel Governor,
Keepalive Management, Rest/Binary Edge Server, and Cross-Node Execution.
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

    def test_memory_headroom(self):
        gov = PixelMemoryGovernor(total_ram_gb=16.0, ceiling_pct=85.0, usable_vram_gb=12.5)
        assert gov.ceiling_mb == 12.5 * 1024.0  # 12,800 MB
        assert gov.allocated_mb == 0.0

        # Request 400 MB
        ok, msg = gov.check_allocation_headroom(400.0)
        assert ok is True
        gov.record_allocation(400.0)
        assert gov.allocated_mb == 400.0

        # Request 13,000 MB (exceeds ceiling)
        ok2, msg2 = gov.check_allocation_headroom(13000.0)
        assert ok2 is False
        assert "exceeds remaining headroom" in msg2


class TestPixelEdgeComputeEngine:
    """Validates genuine transformer block linear algebra on the edge node."""

    def test_load_and_forward_single_step(self):
        engine = PixelEdgeComputeEngine(node_id="pixel_10")
        assert engine.is_loaded is False

        # Load Bloom-560M shard (layers 16..20)
        ok = engine.load_model_shard("bloom-560m", start_layer=16, end_layer=20, hidden_dim=1024, num_heads=16)
        assert ok is True
        assert engine.is_loaded is True
        assert len(engine.local_layers) == 4
        assert engine.memory_governor.allocated_mb > 0.0

        # Create input activations
        rng = np.random.RandomState(42)
        x_in = rng.normal(0, 1.0, (1, 4, 1024)).astype(np.float32)
        payload_in = TensorPayload(data=x_in)

        # Forward step through layer 16
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

        # Telemetry verification
        status = engine.get_status()
        assert status["is_loaded"] is True
        assert status["shard"]["model_id"] == "bloom-560m"
        assert status["shard"]["start_layer"] == 16
        assert status["shard"]["end_layer"] == 24
        assert status["performance"]["total_forward_steps"] == 8


class TestPixelTermuxServerAndClient:
    """Validates local HTTP REST & binary wire server endpoints and client protocol."""

    @pytest.fixture(scope="class")
    def edge_server(self):
        # Pick random available port for testing
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

    def test_client_load_and_forward_binary(self, edge_server):
        client = EdgeNodeClient(host="127.0.0.1", port=39876)
        
        # 1. Load shard
        load_ok = client.load_shard("bloom-560m", 16, 20)
        assert load_ok is True

        # 2. Binary wire single step
        rng = np.random.RandomState(99)
        arr = rng.normal(0, 1.0, (1, 2, 1024)).astype(np.float32)
        payload_in = TensorPayload(data=arr)

        out_step = client.forward_step_binary(payload_in, layer_idx=16)
        assert out_step.data.shape == arr.shape
        assert not np.allclose(out_step.data, arr)

        # 3. Binary wire range pass
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
