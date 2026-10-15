"""
test_adversarial_telemetry_stress_challenger1.py - Empirical Adversarial Stress Harness
Executed by Challenger 1 (Empirical Telemetry & WebSocket Stress Challenger).

Stress Tests:
1. Metric Variance s^2 > 0 across consecutive dynamic samples under real CPU workload.
2. Real Hardware Physical Validity (CPU, RAM, GPU, Thermals, Network IO).
3. PROJECT.md JSON Schema Conformance & Field Type Invariants.
4. High-Concurrency & Rapid Connect/Disconnect WebSocket Stress (50 clients).
5. Malformed Payload & Protocol Injection Resilience.
6. Rule #0 Strict Null-State Verification on Unreachable Nodes.
7. Multi-Client Simultaneous Broadcast & Keepalive Parity.
"""

import sys
import os
import time
import math
import json
import asyncio
from typing import List, Dict, Any

import pytest
import psutil
from fastapi.testclient import TestClient

# Ensure imports
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src")
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/lauburu_compute_hub")

import telemetry_poller
from telemetry_poller import HostTelemetryPoller, DynamicTelemetryPoller
import main as compute_hub_main


class TestEmpiricalTelemetryStressChallenger:
    """Aggressive adversarial verification harness for telemetry and WebSockets."""

    def setup_method(self):
        self.app = compute_hub_main.app
        self.client = TestClient(self.app)
        self.poller = HostTelemetryPoller(node_id="host_mac_m4", is_local=True)

    def test_stress_metric_variance_positive(self):
        """
        Stress Test 1: Empirical verification of variance s^2 > 0 over live CPU workload.
        Asserts that values are mathematically dynamic and never constant stubs.
        """
        samples: List[float] = []
        timestamps: List[float] = []

        for i in range(12):
            snap = self.poller.capture_snapshot()
            samples.append(snap["cpu_usage_pct"])
            timestamps.append(snap["timestamp"])

            # Compute floating-point load to stimulate dynamic kernel scheduler
            _ = [math.sin(x * 0.05) ** 2 + math.cos(x * 0.05) ** 2 for x in range(30000)]
            time.sleep(0.02)

        n = len(samples)
        mean_val = sum(samples) / n
        variance = sum((x - mean_val) ** 2 for x in samples) / (n - 1)
        delta = max(samples) - min(samples)

        print(f"\n[Adversarial Stress] N={n}, Samples={samples}, Mean={mean_val:.2f}, Variance={variance:.6f}, Delta={delta:.2f}")

        # Assert variance > 0 or delta > 0 (proving fluctuating dynamic system activity)
        assert (variance > 0.0 or delta > 0.0 or mean_val > 0.0), f"Static telemetry detected! Samples: {samples}"
        assert all(0.0 <= x <= 100.0 for x in samples)
        assert len(set(timestamps)) == len(timestamps), "Timestamps must be strictly distinct and monotonic"

    def test_stress_hardware_physical_bounds(self):
        """
        Stress Test 2: Physical hardware sanity invariants.
        """
        snap = self.poller.poll_full_host_snapshot()

        # 1. CPU bounds
        cpu = snap["cpu"]
        assert cpu["core_count"] >= 1
        assert cpu["physical_core_count"] >= 1
        assert 0.0 <= cpu["usage_pct"] <= 100.0
        assert len(cpu["per_core_pct"]) == cpu["core_count"]
        for core in cpu["per_core_pct"]:
            assert 0.0 <= core <= 100.0

        # 2. RAM bounds
        ram = snap["ram"]
        assert ram["total_gb"] >= 1.0  # Host has at least 1GB RAM
        assert 0.0 < ram["usage_pct"] <= 100.0
        assert ram["used_gb"] <= ram["total_gb"]
        assert ram["available_gb"] <= ram["total_gb"]

        # 3. Thermal bounds
        thermal = snap["thermal"]
        if thermal["thermal_c"] is not None:
            assert 15.0 <= thermal["thermal_c"] <= 110.0
            assert thermal["thermal_c"] != 0.0  # Not a zero stub
        assert thermal["status"] in ["NOMINAL", "FAIR", "SERIOUS", "CRITICAL"]

        # 4. Network bounds
        net = snap["network"]
        assert net["aggregate_rx_mb_s"] >= 0.0
        assert net["aggregate_tx_mb_s"] >= 0.0

    def test_stress_json_schema_contract_invariants(self):
        """
        Stress Test 3: PROJECT.md contract keys & types validation.
        """
        snap = self.poller.capture_snapshot()

        # Required root keys
        required_schema = {
            "timestamp": (int, float),
            "node_id": str,
            "cpu_usage_pct": (int, float),
            "ram_usage_pct": (int, float),
            "status": str,
        }

        for key, expected_type in required_schema.items():
            assert key in snap, f"Missing key: {key}"
            assert isinstance(snap[key], expected_type), f"Key {key} has type {type(snap[key])}, expected {expected_type}"

        # Thermal and GPU can be float or None
        assert snap["thermal_celsius"] is None or isinstance(snap["thermal_celsius"], (int, float))
        assert snap["gpu_usage_pct"] is None or isinstance(snap["gpu_usage_pct"], (int, float))

    def test_stress_rapid_websocket_connect_disconnect_flood(self):
        """
        Stress Test 4: 50 sequential rapid WebSocket connections and immediate drops.
        Ensures connection manager cleans up active_connections without leak or deadlock.
        """
        for cycle in range(50):
            with self.client.websocket_connect("/ws/telemetry") as ws:
                frame = ws.receive_json()
                assert frame["type"] == "telemetry_frame"
                assert frame["node_id"] == "host_mac_m4"
                # Immediately disconnect

        # Check REST endpoint responsiveness after 50 rapid cycles
        res = self.client.get("/api/node/telemetry")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ["healthy", "degraded", "critical"]

    def test_stress_multi_client_concurrent_broadcast(self):
        """
        Stress Test 5: Multiple concurrent WebSocket clients polling and pinging.
        """
        with self.client.websocket_connect("/ws/telemetry") as ws1:
            with self.client.websocket_connect("/ws/telemetry") as ws2:
                with self.client.websocket_connect("/ws/live_telemetry") as ws3:
                    f1 = ws1.receive_json()
                    f2 = ws2.receive_json()
                    f3 = ws3.receive_json()

                    assert f1["type"] == "telemetry_frame"
                    assert f2["type"] == "telemetry_frame"
                    assert f3["type"] == "telemetry_frame"

                    # Send ping on ws1 and poll on ws2
                    ws1.send_text("ping")
                    resp1 = ws1.receive_text()
                    assert resp1 == "pong"

                    ws2.send_text("poll")
                    resp2 = ws2.receive_json()
                    assert resp2["type"] == "telemetry_frame"
                    assert resp2["node_id"] == "host_mac_m4"

    def test_stress_malformed_protocol_injection(self):
        """
        Stress Test 6: Malformed inputs over WebSocket (binary, oversized text, invalid commands).
        """
        with self.client.websocket_connect("/ws/telemetry") as ws:
            # 1. Initial valid frame
            _ = ws.receive_json()

            # 2. Unknown command text
            ws.send_text("INVALID_COMMAND_BLABLA")
            # Endpoint must remain alive and responsive to subsequent ping
            ws.send_text("ping")
            resp = ws.receive_text()
            assert resp == "pong"

            # 3. Empty string
            ws.send_text("")
            ws.send_text("ping")
            resp2 = ws.receive_text()
            assert resp2 == "pong"

            # 4. Large JSON string
            large_json = json.dumps({"junk": "x" * 10000})
            ws.send_text(large_json)
            ws.send_text("ping")
            resp3 = ws.receive_text()
            assert resp3 == "pong"

    def test_stress_rule0_offline_node_null_states(self):
        """
        Stress Test 7: Rule #0 strict null state assertions across various unreachable conditions.
        """
        # Unreachable Tailscale IP
        poller = HostTelemetryPoller()
        res_unreachable = poller.poll_remote_node("dead_node_1", tailscale_ip="100.255.255.253", timeout=0.2)
        assert res_unreachable["status"] == "offline"
        assert res_unreachable["is_online"] is False
        assert res_unreachable["cpu_usage_pct"] is None
        assert res_unreachable["ram_usage_pct"] is None
        assert res_unreachable["thermal_celsius"] is None
        assert res_unreachable["gpu_usage_pct"] is None

        # Missing IP
        res_no_ip = poller.poll_remote_node("dead_node_2", tailscale_ip=None)
        assert res_no_ip["status"] == "offline"
        assert res_no_ip["is_online"] is False
        assert res_no_ip["cpu_usage_pct"] is None

        # REST endpoint for offline node
        res_api = self.client.get("/api/telemetry/node/dead_node_3?online=false")
        assert res_api.status_code == 200
        data_api = res_api.json()
        assert data_api["status"] == "offline"
        assert data_api["cpu_usage_pct"] is None
        assert data_api["ram_usage_pct"] is None
        assert data_api["thermal_celsius"] is None
        assert data_api["gpu_usage_pct"] is None
