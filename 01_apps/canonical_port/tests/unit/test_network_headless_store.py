"""
Unit Tests: Network Telemetry Headless Models & State Store (R1, R2, R3)
Verifies dataclasses, .to_dict() and .to_json() serialization for Master AGI headless ingestion,
round-trip deserialization, zero-mock invariants, and socket probe resilience.
"""

import sys
import os
import json
import pytest
from typing import Dict, Any

# Ensure tui package is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))
from models.network_telemetry import (
    WanRoute,
    TailscalePeer,
    Tb4DmaInterconnect,
    LlamaRpcNode,
    NetworkTelemetrySnapshot
)
from services.network_telemetry_store import NetworkTelemetryStore, network_telemetry_store


def test_wan_route_dataclass_and_dict():
    route = WanRoute(
        interface="en0_wifi_wan",
        status="ACTIVE",
        rtt_ms=1.84,
        drop_rate=0.00,
        circuit_state="CLOSED",
        bandwidth="2.4 Gbps (Wi-Fi 7 MLO)",
        priority="P1"
    )
    d = route.to_dict()
    assert d["interface"] == "en0_wifi_wan"
    assert d["status"] == "ACTIVE"
    assert d["rtt_ms"] == 1.84
    assert d["drop_rate"] == 0.00
    assert d["circuit_state"] == "CLOSED"
    assert d["bandwidth"] == "2.4 Gbps (Wi-Fi 7 MLO)"
    assert d["priority"] == "P1"


def test_tailscale_peer_dataclass_and_dict():
    peer = TailscalePeer(
        node_name="Mac_Node",
        ip="100.119.199.76",
        status="ONLINE",
        relay="Direct WireGuard",
        layer="L1",
        os="macOS Darwin ARM64"
    )
    d = peer.to_dict()
    assert d["node_name"] == "Mac_Node"
    assert d["ip"] == "100.119.199.76"
    assert d["status"] == "ONLINE"
    assert d["relay"] == "Direct WireGuard"
    assert d["layer"] == "L1"


def test_tb4_dma_interconnect_dataclass_and_dict():
    tb4 = Tb4DmaInterconnect(
        ip="169.254.187.138",
        status="CONNECTED",
        rtt_ms=0.277,
        throughput_gbps=38.4,
        interface="bridge0 / tb0",
        zero_copy_active=True
    )
    d = tb4.to_dict()
    assert d["ip"] == "169.254.187.138"
    assert d["status"] == "CONNECTED"
    assert d["rtt_ms"] == 0.277
    assert d["throughput_gbps"] == 38.4
    assert d["zero_copy_active"] is True


def test_llama_rpc_node_dataclass_and_dict():
    rpc = LlamaRpcNode(
        node_name="Linux Head Node",
        endpoint="100.101.39.98:50052",
        layers_sharded=28,
        vram_used_gb=13.5,
        status="ONLINE",
        latency_ms=1.20
    )
    d = rpc.to_dict()
    assert d["node_name"] == "Linux Head Node"
    assert d["endpoint"] == "100.101.39.98:50052"
    assert d["layers_sharded"] == 28
    assert d["vram_used_gb"] == 13.5
    assert d["status"] == "ONLINE"
    assert d["latency_ms"] == 1.20


def test_network_telemetry_snapshot_serialization_and_deserialization():
    snapshot = NetworkTelemetrySnapshot.create_canonical_default()
    raw_dict = snapshot.to_dict()
    assert isinstance(raw_dict, dict)
    assert "timestamp" in raw_dict
    assert len(raw_dict["wan_routes"]) == 3
    assert len(raw_dict["tailscale_peers"]) == 7
    assert len(raw_dict["llama_rpc_nodes"]) == 3
    assert raw_dict["tb4_dma"]["ip"] == "169.254.187.138"

    # JSON serialization (R3)
    json_str = snapshot.to_json()
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed["tb4_dma"]["rtt_ms"] == 0.277

    # Deserialization from dict
    reconstructed = NetworkTelemetrySnapshot.from_dict(parsed)
    assert reconstructed.tb4_dma.ip == "169.254.187.138"
    assert len(reconstructed.tailscale_peers) == 7
    assert reconstructed.tailscale_peers[0].node_name == "Mac_Node"


def test_mesh_node_ip_invariants():
    """Verify all 7 physical mesh node Tailscale IPs match canonical architecture."""
    snapshot = NetworkTelemetrySnapshot.create_canonical_default()
    peers_by_name = {p.node_name: p.ip for p in snapshot.tailscale_peers}
    
    assert peers_by_name["Mac_Node"] == "100.119.199.76"
    assert peers_by_name["MacBook_Pro"] == "100.103.212.21"
    assert peers_by_name["Linux_Head_Node"] == "100.101.39.98"
    assert peers_by_name["Linux_Tablet"] == "100.81.92.125"
    assert peers_by_name["MacBook_Air"] == "100.93.158.96"
    assert peers_by_name["Pixel_10_Pro_XL"] == "100.73.38.87"
    assert peers_by_name["Samsung_S20"] == "100.84.40.95"


def test_llama_rpc_sharding_80_layers_split():
    """Verify Port 50052 RPC matrix implements the -ts 28,28,24 (80 layers) sharding split."""
    snapshot = NetworkTelemetrySnapshot.create_canonical_default()
    total_layers = sum(n.layers_sharded for n in snapshot.llama_rpc_nodes)
    total_vram = sum(n.vram_used_gb for n in snapshot.llama_rpc_nodes)

    assert total_layers == 80
    assert total_vram == 39.0
    for node in snapshot.llama_rpc_nodes:
        assert node.endpoint.endswith(":50052")


def test_network_telemetry_store_headless_api():
    """Verify Master AGI can query state store headlessly."""
    store = NetworkTelemetryStore()
    raw_state = store.get_raw_state_for_agi()
    assert isinstance(raw_state, dict)
    assert "wan_routes" in raw_state
    assert "tailscale_peers" in raw_state
    assert "tb4_dma" in raw_state
    assert "llama_rpc_nodes" in raw_state

    json_out = store.to_json()
    assert "169.254.187.138" in json_out
    assert "50052" in json_out


def test_socket_probe_offline_resilience():
    """Verify socket probe handles unreachable endpoints without throwing unhandled errors."""
    store = NetworkTelemetryStore()
    # Non-existent local port
    res = store.probe_socket_latency("127.0.0.1", 59999, timeout=0.05)
    assert res is None  # Authentic None / waiting state, not an exception
