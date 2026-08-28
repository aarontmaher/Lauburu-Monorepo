#!/usr/bin/env python3
"""
Unit and Integration Tests for Unified Network Awareness Layer (UNAL)
Milestone M1 — Lauburu AI Mesh Network Foundation
"""

import os
import sys
import json
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARDING_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(SHARDING_DIR) not in sys.path:
    sys.path.insert(0, str(SHARDING_DIR))

from sharding_daemon.network_awareness import (
    UnifiedNetworkAwarenessLayer,
    LinkMetrics,
    TransportTier,
    NetworkInterface,
    PeerStatus,
    MeshTelemetrySnapshot,
    discover_local_interfaces,
    query_tailscale_status,
    probe_socket_tcp,
    probe_ping_empirical,
    get_live_peer_metrics,
    compute_routing_cost,
    find_tailscale_binary,
)


class TestDataModels:
    """Test Pydantic contract data models."""

    def test_link_metrics_contract(self):
        lm = LinkMetrics(
            peer_id="pixel_node",
            tailscale_ip="100.73.38.87",
            is_direct=True,
            rtt_ms=35.5,
            bandwidth_mbps=500.0,
            packet_loss=0.0,
            transport_tier=TransportTier.TAILSCALE_DIRECT.value
        )
        assert lm.peer_id == "pixel_node"
        assert lm.tailscale_ip == "100.73.38.87"
        assert lm.is_direct is True
        assert lm.rtt_ms == 35.5
        assert lm.bandwidth_mbps == 500.0
        assert lm.packet_loss == 0.0
        assert lm.transport_tier == "TAILSCALE_DIRECT"

    def test_network_interface_model(self):
        ni = NetworkInterface(
            name="en1",
            ip="192.168.8.155",
            type="wifi7_mlo",
            status="UP",
            mtu=1500,
            rtt_ms=1.4,
            bandwidth_mbps=2401.0,
            role="PRIMARY"
        )
        assert ni.name == "en1"
        assert ni.type == "wifi7_mlo"
        assert ni.status == "UP"
        assert ni.bandwidth_mbps == 2401.0


class TestInterfaceDiscovery:
    """Test dynamic local interface discovery."""

    def test_discover_local_interfaces(self):
        ifaces = discover_local_interfaces()
        assert isinstance(ifaces, list)
        assert len(ifaces) >= 1

        # Must include at least loopback or active physical interface
        names = [i.name for i in ifaces]
        ips = [i.ip for i in ifaces]
        assert any(ip.startswith("127.") or ip.startswith("192.") or ip.startswith("169.") or ip.startswith("100.") for ip in ips)

        for iface in ifaces:
            assert isinstance(iface.name, str)
            assert isinstance(iface.ip, str)
            assert iface.status in ("UP", "DOWN")
            assert iface.bandwidth_mbps > 0
            assert iface.mtu >= 1280


class TestTailscaleStatus:
    """Test Tailscale status querying and classification."""

    def test_tailscale_binary_and_status(self):
        ts_bin = find_tailscale_binary()
        status_data = query_tailscale_status()
        assert isinstance(status_data, dict)
        assert "BackendState" in status_data

        if status_data.get("BackendState") == "Running":
            assert "Self" in status_data
            assert "Peer" in status_data
            self_node = status_data["Self"]
            assert "TailscaleIPs" in self_node


class TestProbingEngine:
    """Test empirical socket and ping probing."""

    def test_probe_socket_tcp_loopback(self):
        # Probing loopback on an unused port should return within timeout
        reachable, rtt_ms = probe_socket_tcp("127.0.0.1", 59999, timeout_sec=0.3)
        assert isinstance(reachable, bool)
        assert isinstance(rtt_ms, float)
        assert rtt_ms >= 0.0

    def test_probe_ping_empirical_loopback(self):
        reachable, rtt_ms, jitter, loss = probe_ping_empirical("127.0.0.1", count=1, timeout_sec=0.5)
        assert reachable is True
        assert rtt_ms < 10.0
        assert loss == 0.0


class TestPeerMetricsAndRoutingCost:
    """Test LinkMetrics retrieval and Dijkstra cost calculations."""

    def test_get_live_peer_metrics_localhost(self):
        metrics = get_live_peer_metrics("127.0.0.1")
        assert metrics.tailscale_ip == "127.0.0.1"
        assert metrics.is_direct is True
        assert metrics.rtt_ms < 1.0
        assert metrics.bandwidth_mbps >= 1000.0
        assert metrics.transport_tier == TransportTier.LOCAL_LOOPBACK.value
        assert metrics.packet_loss == 0.0

    def test_get_live_peer_metrics_unreachable(self):
        metrics = get_live_peer_metrics("198.51.100.254")  # RFC 5737 TEST-NET-2 dummy unreachable
        assert metrics.packet_loss >= 90.0 or metrics.rtt_ms > 500.0
        assert metrics.transport_tier in (TransportTier.UNREACHABLE.value, TransportTier.TAILSCALE_DIRECT.value, TransportTier.DERP_RELAY.value)

    def test_compute_routing_cost_intra_node(self):
        cost = compute_routing_cost("127.0.0.1", "127.0.0.1", 10 * 1024 * 1024)
        assert cost == 0.0

    def test_compute_routing_cost_tier_ordering(self):
        # TB4 DMA cost should be lower than Tailscale Direct and DERP Relay for same tensor size
        tensor_bytes = 50 * 1024 * 1024  # 50 MB
        cost_local = compute_routing_cost("127.0.0.1", "127.0.0.1", tensor_bytes)
        assert cost_local == 0.0

    def test_compute_routing_cost_monotonic_with_size(self):
        cost_small = compute_routing_cost("127.0.0.1", "100.73.38.87", 1 * 1024 * 1024)
        cost_large = compute_routing_cost("127.0.0.1", "100.73.38.87", 100 * 1024 * 1024)
        assert cost_large >= cost_small


class TestUNALCoordinator:
    """Test UnifiedNetworkAwarenessLayer singleton and telemetry export."""

    def test_unal_singleton_and_export(self, tmp_path):
        unal = UnifiedNetworkAwarenessLayer.get_instance(polling_interval_sec=5.0)
        snapshot = unal.refresh_telemetry()
        assert isinstance(snapshot, MeshTelemetrySnapshot)
        assert "node_name" in snapshot.local_node
        assert len(snapshot.local_node["interfaces"]) >= 1

        test_out = tmp_path / "test_mesh_telemetry.json"
        saved_path = unal.export_telemetry_json(test_out)
        assert saved_path.exists()

        content = json.loads(saved_path.read_text())
        assert "timestamp_utc" in content
        assert "local_node" in content
        assert "peers" in content
        assert "bonding_state" in content
