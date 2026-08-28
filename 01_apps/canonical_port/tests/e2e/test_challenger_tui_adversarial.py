"""
Adversarial Empirical Stress Test Suite — Challenger 2 (Textual TUI & Headless Store)
Exhaustively stress-tests:
1. Rapid keypress bursts, interleaving, and re-entrant navigation
2. NetworkScreen button hammering and asynchronous refresh handling
3. Socket timeout anomalies, blackhole IPs, port boundaries, and DNS resolution failures
4. Concurrent multi-threaded / async store polling and cache TTL safety
5. Dataclass serialization / deserialization under malformed, empty, or boundary inputs
6. Rich table rendering resilience against extreme values, empty states, and markup injection
7. Extreme terminal viewport resizing stress on NetworkScreen
"""

import pytest
import asyncio
import sys
import os
import json
import time
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

# Ensure tui package is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tui"))
from canonical_tui import CanonicalPortTUI
from screens.agi_coding_terminal_screen import AgiCodingTerminalScreen
from screens.governance_screen import GovernanceScreen
from screens.network_screen import NetworkScreen
from screens.optimization_screen import OptimizationScreen
from screens.training_screen import TrainingScreen
from models.network_telemetry import (
    WanRoute,
    TailscalePeer,
    Tb4DmaInterconnect,
    LlamaRpcNode,
    NetworkTelemetrySnapshot
)
from services.network_telemetry_store import NetworkTelemetryStore, network_telemetry_store
from textual.widgets import Button, Static


# ===========================================================================
# 1. RAPID KEYPRESS BURSTS & INTERLEAVED NAVIGATION STRESS
# ===========================================================================

@pytest.mark.asyncio
async def test_adversarial_rapid_keypress_burst_and_interleaving():
    """
    Stress test TUI event loop with rapid key bursts specifically targeting NetworkScreen (n).
    Sequence: ["n", "g", "o", "t", "n", "n", "r"] repeated 15 times (105 keypresses).
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(140, 70)) as pilot:
        assert isinstance(app.screen, (AgiCodingTerminalScreen, NetworkScreen))
        
        burst_sequence = ["n", "g", "o", "t", "n", "n", "r"] * 15
        for key in burst_sequence:
            await pilot.press(key)
        
        await pilot.pause(0.05)
        # Should be running stably
        assert app.is_running
        # Final state should be NetworkScreen due to sequence ending with 'r' on 'n'
        await pilot.press("n")
        assert isinstance(app.screen, NetworkScreen)


@pytest.mark.asyncio
async def test_adversarial_rapid_unbound_and_modifier_keys():
    """Test pressing unbound keys and rapid alternating shortcuts during network screen operation."""
    app = CanonicalPortTUI()
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.press("n")
        assert isinstance(app.screen, NetworkScreen)
        
        # Burst of valid + unbound keys
        chaotic_keys = ["x", "z", "1", "2", "3", "space", "tab", "n", "r", "enter", "escape", "n"] * 5
        for k in chaotic_keys:
            await pilot.press(k)
        
        await pilot.pause(0.02)
        assert app.is_running
        assert isinstance(app.screen, NetworkScreen)


# ===========================================================================
# 2. NETWORK SCREEN BUTTON HAMMERING & ASYNC PROBE RESILIENCE
# ===========================================================================

@pytest.mark.asyncio
async def test_adversarial_network_screen_button_hammering():
    """
    Empirically hammer all 4 action buttons on NetworkScreen 10 times in rapid succession.
    Verifies that repeated force_probe triggers do not block the event loop or crash on notification toasts.
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(140, 80)) as pilot:
        await pilot.press("n")
        assert isinstance(app.screen, NetworkScreen)
        
        buttons = ["btn-ping-tb4", "btn-probe-rpc", "btn-refresh-net", "btn-wol-revive"]
        
        # Hammer loop
        for round_num in range(10):
            for b_id in buttons:
                btn = app.screen.query_one(f"#{b_id}", Button)
                assert btn is not None
                btn.scroll_visible()
                await pilot.click(f"#{b_id}")
            await pilot.pause(0.01)
            
        assert app.is_running
        assert isinstance(app.screen, NetworkScreen)


@pytest.mark.asyncio
async def test_adversarial_interleaved_keys_and_button_clicks():
    """Interleave rapid screen switching with button clicking on NetworkScreen."""
    app = CanonicalPortTUI()
    async with app.run_test(size=(140, 80)) as pilot:
        for _ in range(5):
            await pilot.press("n")
            assert isinstance(app.screen, NetworkScreen)
            btn = app.screen.query_one("#btn-ping-tb4", Button)
            btn.scroll_visible()
            await pilot.pause(0.01)
            await pilot.click("#btn-ping-tb4")
            
            await pilot.press("g")
            assert isinstance(app.screen, GovernanceScreen)
            
            await pilot.press("n")
            assert isinstance(app.screen, NetworkScreen)
            btn = app.screen.query_one("#btn-probe-rpc", Button)
            btn.scroll_visible()
            await pilot.pause(0.01)
            await pilot.click("#btn-probe-rpc")
            
            await pilot.press("o")
            assert isinstance(app.screen, OptimizationScreen)
            
            await pilot.press("n")
            assert isinstance(app.screen, NetworkScreen)
            btn = app.screen.query_one("#btn-refresh-net", Button)
            btn.scroll_visible()
            await pilot.pause(0.01)
            await pilot.click("#btn-refresh-net")
            
        assert app.is_running


# ===========================================================================
# 3. SOCKET TIMEOUT ANOMALIES, BOUNDARIES & OFFLINE ENDPOINTS
# ===========================================================================

def test_adversarial_socket_probes_unreachable_and_blackhole_ips():
    """
    Test probe_socket_latency with unreachable, non-routable, and reserved blackhole IPs.
    Must return None safely without raising uncaught exceptions (Rule #0).
    """
    store = NetworkTelemetryStore()
    
    # TEST-NET-1 (RFC 5737 - guaranteed non-routable)
    rtt = store.probe_socket_latency("192.0.2.1", 50052, timeout=0.05)
    assert rtt is None
    
    # Class E reserved / blackhole
    rtt = store.probe_socket_latency("240.0.0.1", 50052, timeout=0.05)
    assert rtt is None
    
    # Localhost inactive high port (fast connection refused)
    rtt = store.probe_socket_latency("127.0.0.1", 58888, timeout=0.05)
    assert rtt is None


def test_adversarial_socket_probes_invalid_hostnames_and_ports():
    """Test socket probe against invalid hostnames, DNS failures, and port boundaries."""
    store = NetworkTelemetryStore()
    
    # Non-existent hostname
    assert store.probe_socket_latency("nonexistent-node.invalid.domain.lauburu", 50052, timeout=0.05) is None
    
    # Empty string host
    assert store.probe_socket_latency("", 50052, timeout=0.05) is None
    
    # Port boundaries: 0, 65535, negative, overflow
    assert store.probe_socket_latency("127.0.0.1", 0, timeout=0.05) is None
    assert store.probe_socket_latency("127.0.0.1", 65535, timeout=0.05) is None
    assert store.probe_socket_latency("127.0.0.1", -1, timeout=0.05) is None
    assert store.probe_socket_latency("127.0.0.1", 99999, timeout=0.05) is None
    
    # Timeout boundaries: 0.0, negative
    assert store.probe_socket_latency("127.0.0.1", 50052, timeout=0.0) is None
    assert store.probe_socket_latency("127.0.0.1", 50052, timeout=-1.0) is None


# ===========================================================================
# 4. CONCURRENT POLLING & CACHE TTL SAFETY
# ===========================================================================

def test_adversarial_concurrent_store_polling():
    """
    Stress test NetworkTelemetryStore with 30 concurrent threads executing get_current_snapshot(force_refresh=True).
    Verifies thread safety, lack of deadlocks or race conditions.
    """
    store = NetworkTelemetryStore()
    results = []
    errors = []

    def worker(idx: int):
        try:
            snap = store.get_current_snapshot(force_refresh=(idx % 2 == 0))
            results.append(snap)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3.0)

    assert len(errors) == 0, f"Encountered concurrency errors: {errors}"
    assert len(results) == 30
    for snap in results:
        assert isinstance(snap, NetworkTelemetrySnapshot)
        assert len(snap.wan_routes) >= 3
        assert len(snap.tailscale_peers) >= 7
        assert len(snap.llama_rpc_nodes) == 3


def test_adversarial_cache_ttl_behavior():
    """Verify cache TTL returns identical object within TTL window and refreshes when forced."""
    store = NetworkTelemetryStore()
    snap1 = store.get_current_snapshot(force_refresh=False)
    snap2 = store.get_current_snapshot(force_refresh=False)
    # Within 1.0s TTL, should return cached instance
    assert snap1 is snap2
    
    # Force refresh should produce new snapshot
    snap3 = store.get_current_snapshot(force_refresh=True)
    assert snap3 is not None


# ===========================================================================
# 5. DATACLASS SERIALIZATION & DESERIALIZATION UNDER ADVERSARIAL INPUTS
# ===========================================================================

def test_adversarial_snapshot_from_dict_empty_and_minimal():
    """Verify NetworkTelemetrySnapshot.from_dict gracefully handles empty dict or missing keys."""
    # Completely empty dict
    snap = NetworkTelemetrySnapshot.from_dict({})
    assert snap.timestamp != ""
    assert snap.wan_routes == []
    assert snap.tailscale_peers == []
    assert snap.llama_rpc_nodes == []
    assert snap.tb4_dma.status == "OFFLINE"
    assert snap.tb4_dma.ip == "169.254.187.138"
    
    # Re-serialization of empty snapshot
    d = snap.to_dict()
    assert d["wan_routes"] == []
    assert d["tailscale_peers"] == []
    assert d["llama_rpc_nodes"] == []
    assert json.loads(snap.to_json())["wan_routes"] == []


def test_adversarial_snapshot_from_dict_partial_and_malformed():
    """Verify from_dict with partial WAN, Tailscale, TB4, and RPC objects."""
    raw_data = {
        "timestamp": "05:00:00",
        "wan_routes": [
            {
                "interface": "en0_custom",
                "status": "DEGRADED",
                "rtt_ms": None,
                "drop_rate": 0.55,
                "circuit_state": "HALF_OPEN",
                "bandwidth": "10 Mbps",
                "priority": "P2"
            }
        ],
        "tailscale_peers": [
            {
                "node_name": "Ghost_Node",
                "ip": "100.99.99.99",
                "status": "OFFLINE",
                "relay": "DERP Relay",
                "layer": "L9",
                "os": "Embedded RTOS"
            }
        ],
        "tb4_dma": {
            "ip": "169.254.100.1",
            "status": "DEGRADED",
            "rtt_ms": 1.50,
            "throughput_gbps": 10.0,
            "interface": "tb1",
            "zero_copy_active": False
        },
        "llama_rpc_nodes": [
            {
                "node_name": "Remote Cluster",
                "endpoint": "100.99.99.99:50052",
                "layers_sharded": 40,
                "vram_used_gb": 24.0,
                "status": "OFFLINE",
                "latency_ms": None
            }
        ]
    }
    
    snap = NetworkTelemetrySnapshot.from_dict(raw_data)
    assert snap.wan_routes[0].rtt_ms is None
    assert snap.wan_routes[0].status == "DEGRADED"
    assert snap.tailscale_peers[0].status == "OFFLINE"
    assert snap.tb4_dma.zero_copy_active is False
    assert snap.llama_rpc_nodes[0].latency_ms is None
    
    # Round-trip JSON test
    json_str = snap.to_json()
    reconstructed = NetworkTelemetrySnapshot.from_dict(json.loads(json_str))
    assert reconstructed.wan_routes[0].interface == "en0_custom"
    assert reconstructed.llama_rpc_nodes[0].layers_sharded == 40


# ===========================================================================
# 6. RICH TABLE RENDERING RESILIENCE & MARKUP INJECTION SAFETY
# ===========================================================================

@pytest.mark.asyncio
async def test_adversarial_rendering_empty_snapshot():
    """Verify NetworkScreen renders cleanly without throwing when all telemetry lists are empty."""
    app = CanonicalPortTUI()
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.press("n")
        net_screen: NetworkScreen = app.screen
        assert isinstance(net_screen, NetworkScreen)
        
        # Empty snapshot
        empty_snap = NetworkTelemetrySnapshot.from_dict({})
        net_screen.render_wan(empty_snap)
        net_screen.render_tb4(empty_snap)
        net_screen.render_tailscale(empty_snap)
        net_screen.render_rpc(empty_snap)
        
        await pilot.pause(0.01)
        assert app.is_running


@pytest.mark.asyncio
async def test_adversarial_rendering_markup_injection_and_extreme_values():
    """
    Verify NetworkScreen renders Rich tables safely when models contain brackets,
    markup-like strings, or extreme numeric values without crashing.
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(140, 80)) as pilot:
        await pilot.press("n")
        net_screen: NetworkScreen = app.screen
        assert isinstance(net_screen, NetworkScreen)
        
        adversarial_snap = NetworkTelemetrySnapshot(
            timestamp="99:99:99",
            wan_routes=[
                WanRoute(
                    interface="en[0]_wifi_<test>",
                    status="DEGRADED",
                    rtt_ms=999999.99,
                    drop_rate=1.00,
                    circuit_state="OPEN",
                    bandwidth="0 bps [NONE]",
                    priority="P99"
                )
            ],
            tailscale_peers=[
                TailscalePeer(
                    node_name="[bold red]Hacker_Node[/bold red]",
                    ip="100.255.255.255",
                    status="OFFLINE",
                    relay="DERP [Relay #1]",
                    layer="L99",
                    os="Unknown OS <X86>"
                )
            ],
            tb4_dma=Tb4DmaInterconnect(
                ip="169.254.255.255",
                status="OFFLINE",
                rtt_ms=0.000,
                throughput_gbps=0.0
            ),
            llama_rpc_nodes=[
                LlamaRpcNode(
                    node_name="Node <Unreachable>",
                    endpoint="240.0.0.1:50052",
                    layers_sharded=0,
                    vram_used_gb=0.0,
                    status="OFFLINE",
                    latency_ms=None
                )
            ]
        )
        
        # Render adversarial snapshot
        net_screen.render_wan(adversarial_snap)
        net_screen.render_tb4(adversarial_snap)
        net_screen.render_tailscale(adversarial_snap)
        net_screen.render_rpc(adversarial_snap)
        
        await pilot.pause(0.01)
        assert app.is_running


# ===========================================================================
# 7. EXTREME TERMINAL VIEWPORT RESIZING STRESS
# ===========================================================================

@pytest.mark.asyncio
async def test_adversarial_viewport_resizing_on_network_screen():
    """
    Stress test NetworkScreen layout under extreme viewport resizing:
    Micro terminal (25x10) -> Ultrawide (250x100) -> Tall narrow (40x80) -> Standard (80x24).
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.press("n")
        assert isinstance(app.screen, NetworkScreen)
        
        viewports = [(25, 10), (250, 100), (40, 80), (80, 24), (160, 50)]
        for w, h in viewports:
            await pilot.resize_terminal(w, h)
            await pilot.pause(0.01)
            # Trigger refresh at this size via keypress 'r' and 'n'
            await pilot.press("r")
            await pilot.press("n")
            await pilot.pause(0.01)
            assert app.is_running
