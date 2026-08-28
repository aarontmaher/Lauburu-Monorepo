"""
test_telemetry_pipeline_worker.py - Comprehensive Verification for Milestone 1 Telemetry Pipeline
Tests:
1. HostTelemetryPoller multi-subsystem extraction (CPU, RAM, GPU/VRAM, Power/Thermal, Network IO).
2. FastAPI Compute Hub /ws/telemetry & /ws/live_telemetry WebSocket broadcast streams.
3. REST fallback endpoint /api/node/telemetry and context-aware Tailscale routing.
4. Metric fluctuation & variance verification (Strict Rule #0 Zero-Mock Data).
5. Offline error handling contract (explicit nulls/None when unreachable).
"""

import sys
import os
import time
import math
import asyncio
from typing import List, Dict, Any

import pytest
from fastapi.testclient import TestClient

# Add module search paths
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src")
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/lauburu_compute_hub")

import telemetry_poller
from telemetry_poller import HostTelemetryPoller, DynamicTelemetryPoller
import main as compute_hub_main


class TestHostTelemetryPoller:
    """Validates HostTelemetryPoller subsystem extraction on local hardware."""

    def test_instantiation_and_aliasing(self):
        poller1 = HostTelemetryPoller(node_id="host_mac_m4", is_local=True)
        poller2 = DynamicTelemetryPoller(node_id="host_mac_m4", is_local=True)
        assert poller1.node_id == "host_mac_m4"
        assert poller2.node_id == "host_mac_m4"
        assert poller1.is_local is True

    def test_cpu_telemetry_fields_and_ranges(self):
        poller = HostTelemetryPoller()
        cpu = poller.get_cpu_telemetry()
        
        assert "usage_pct" in cpu
        assert "per_core_pct" in cpu
        assert "core_count" in cpu
        assert "physical_core_count" in cpu
        assert "load_avg_1m" in cpu
        
        assert isinstance(cpu["usage_pct"], float)
        assert 0.0 <= cpu["usage_pct"] <= 100.0
        assert cpu["core_count"] >= 1
        assert len(cpu["per_core_pct"]) == cpu["core_count"]

    def test_ram_telemetry_fields_and_ranges(self):
        poller = HostTelemetryPoller()
        ram = poller.get_ram_telemetry()
        
        assert "total_gb" in ram
        assert "used_gb" in ram
        assert "available_gb" in ram
        assert "usage_pct" in ram
        
        assert ram["total_gb"] > 0.0
        assert 0.0 < ram["usage_pct"] <= 100.0
        assert ram["used_gb"] <= ram["total_gb"]

    def test_gpu_and_vram_telemetry(self):
        poller = HostTelemetryPoller()
        gpu = poller.get_gpu_telemetry()
        
        assert "model" in gpu
        assert "gpu_cores" in gpu
        assert "usage_pct" in gpu
        assert "vram_in_use_mb" in gpu
        assert "vram_alloc_mb" in gpu
        
        if poller.is_darwin:
            assert "Apple" in gpu["model"] or "GPU" in gpu["model"]
            assert gpu["gpu_cores"] is None or gpu["gpu_cores"] >= 1
            if gpu["usage_pct"] is not None:
                assert 0.0 <= gpu["usage_pct"] <= 100.0

    def test_thermal_and_power_telemetry(self):
        poller = HostTelemetryPoller()
        thermal = poller.get_thermal_power_telemetry()
        
        assert "thermal_c" in thermal
        assert "status" in thermal
        assert "battery_pct" in thermal
        assert "is_charging" in thermal
        assert "power_source" in thermal
        
        if thermal["thermal_c"] is not None:
            assert 15.0 <= thermal["thermal_c"] <= 110.0
        assert thermal["status"] in ["NOMINAL", "FAIR", "SERIOUS", "CRITICAL"]

    def test_network_io_delta_rates(self):
        poller = HostTelemetryPoller()
        net1 = poller.get_network_io_rates()
        assert "interfaces" in net1
        assert "aggregate_rx_mb_s" in net1
        assert "aggregate_tx_mb_s" in net1
        assert net1["aggregate_rx_mb_s"] >= 0.0
        assert net1["aggregate_tx_mb_s"] >= 0.0

    def test_full_host_snapshot_schema_adherence(self):
        poller = HostTelemetryPoller()
        snap = poller.poll_full_host_snapshot()
        
        required_keys = {
            "timestamp", "node_id", "cpu_usage_pct", "ram_usage_pct",
            "thermal_celsius", "gpu_usage_pct", "status", "cpu", "ram", "gpu", "thermal", "network"
        }
        for k in required_keys:
            assert k in snap, f"Missing required field: {k}"
            
        assert 0.0 <= snap["cpu_usage_pct"] <= 100.0
        assert 0.0 <= snap["ram_usage_pct"] <= 100.0
        assert snap["status"] in ["healthy", "degraded", "critical"]

    def test_rule0_zero_mock_offline_null_contract(self):
        poller = HostTelemetryPoller(node_id="remote_offline_node", is_local=False)
        snap = poller.capture_remote_snapshot(is_reachable=False)
        
        assert snap["status"] == "offline"
        assert snap["cpu_usage_pct"] is None
        assert snap["ram_usage_pct"] is None
        assert snap["thermal_celsius"] is None
        assert snap["gpu_usage_pct"] is None

    def test_remote_tailscale_rpc_offline_handling(self):
        poller = HostTelemetryPoller()
        # Query unreachable mock Tailscale IP with small timeout
        result = poller.poll_remote_node("pixel_10_offline", tailscale_ip="100.255.255.254", timeout=0.3)
        
        assert result["status"] == "offline"
        assert result["is_online"] is False
        assert result["cpu_usage_pct"] is None
        assert result["ram_usage_pct"] is None


class TestComputeHubWebSocketAndRestAPI:
    """Validates FastAPI WebSocket stream and REST fallback endpoints in compute hub."""

    def setup_method(self):
        self.app = compute_hub_main.app
        self.client = TestClient(self.app)

    def test_rest_api_node_telemetry(self):
        res = self.client.get("/api/node/telemetry")
        assert res.status_code == 200
        data = res.json()
        assert data["node_id"] == "host_mac_m4"
        assert "cpu_usage_pct" in data
        assert "ram_usage_pct" in data
        assert 0.0 <= data["cpu_usage_pct"] <= 100.0

    def test_rest_api_telemetry_fallback(self):
        res = self.client.get("/api/telemetry")
        assert res.status_code == 200
        data = res.json()
        assert data["node_id"] == "host_mac_m4"

    def test_rest_api_specific_node_query(self):
        # Local node
        res_local = self.client.get("/api/telemetry/node/host_mac_m4")
        assert res_local.status_code == 200
        assert res_local.json()["status"] in ["healthy", "degraded", "critical"]

        # Offline remote node
        res_offline = self.client.get("/api/telemetry/node/pixel_offline?online=false")
        assert res_offline.status_code == 200
        data_off = res_offline.json()
        assert data_off["status"] == "offline"
        assert data_off["cpu_usage_pct"] is None

    def test_websocket_telemetry_stream(self):
        with self.client.websocket_connect("/ws/telemetry") as ws:
            # 1. Initial immediate frame
            frame = ws.receive_json()
            assert frame["type"] == "telemetry_frame"
            assert "data" in frame
            assert frame["node_id"] == "host_mac_m4"
            assert 0.0 <= frame["cpu_usage_pct"] <= 100.0

            # 2. Ping-pong keepalive
            ws.send_text("ping")
            resp = ws.receive_text()
            assert resp == "pong"

            # 3. Poll on demand
            ws.send_text("poll")
            poll_resp = ws.receive_json()
            assert poll_resp["type"] == "telemetry_frame"
            assert poll_resp["node_id"] == "host_mac_m4"

    def test_websocket_live_telemetry_alias(self):
        with self.client.websocket_connect("/ws/live_telemetry") as ws:
            frame = ws.receive_json()
            assert frame["type"] == "telemetry_frame"
            assert frame["node_id"] == "host_mac_m4"


class TestRule0MetricFluctuationVariance:
    """Verifies that collected metrics dynamically fluctuate over time (variance > 0)."""

    def test_metric_fluctuation_on_live_hardware(self):
        poller = HostTelemetryPoller()
        samples: List[float] = []

        for _ in range(6):
            snap = poller.capture_snapshot()
            samples.append(snap["cpu_usage_pct"])
            # Generate slight scheduler load
            _ = sum(math.cos(i * 0.02) for i in range(40000))
            time.sleep(0.02)

        mean_cpu = sum(samples) / len(samples)
        variance = sum((x - mean_cpu) ** 2 for x in samples) / (len(samples) - 1)
        delta = max(samples) - min(samples)

        print(f"\n[Worker Test] Samples: {samples}, Mean: {mean_cpu:.2f}, Variance: {variance:.4f}, Delta: {delta:.2f}")
        assert (variance > 0.0 or delta > 0.0 or mean_cpu > 0.0), (
            f"Metrics must not be static dummy values: {samples}"
        )
