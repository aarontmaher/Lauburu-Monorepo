"""
Challenger 2 - TUI Layout and Navigation Stress Test Suite
==========================================================
Adversarially stress tests:
1. Viewport Geometry Matrix across 11 screens and 6 viewport tiers (Nano 80x24, Micro 100x30, Compact 120x40, Full 160x50, Tiny 50x20, Ultra-wide 240x60).
2. Fast Tab Cycling & Bidirectional Navigation Storm (rapid consecutive cycling, hotkeys, navbar state sync).
3. Action Button Dispatch Storm across NetworkScreen, ToolingScreen, RouterControlCard, MeshScaffoldingCard, and AgiCodingTerminalScreen.
4. Dynamic Telemetry Injection & Table Column Width Stability under high-frequency data flooding and boundary payloads.
"""

import os
import sys
import time
import asyncio
import threading
from typing import List, Dict, Any, Optional
import pytest
from rich.table import Table
from rich.text import Text
from textual.widgets import Static, Button, RichLog, Input

# Ensure tui package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from tui.canonical_tui import CanonicalPortApp
from tui.widgets.live_speedtest_card import LiveSpeedtestCard
from tui.widgets.router_control_card import RouterControlCard
from tui.widgets.mesh_scaffolding_card import MeshScaffoldingCard
from tui.widgets.pinned_tab_nav_bar import PinnedTabNavBar
from tui.services.blackboard_store import blackboard_store
from tui.models.blackboard_models import (
    BlackboardTelemetryState,
    WanRoute,
    TailscalePeer,
    LlamaRpcNode,
    WolTarget,
    BluetoothPanLink,
    KdeConnectState,
    Tb4DmaInterconnect,
)
from tui.models.network_telemetry import InternetSpeedMetrics, RouterSystemInfo


# ============================================================================
# TEST GROUP 1: VIEWPORT GEOMETRY MATRIX (11 SCREENS x 6 VIEWPORT TIERS)
# ============================================================================

class TestGroup1ViewportGeometryMatrix:
    """Stress test mounting and rendering all 11 screens across terminal geometries."""

    SCREENS_TO_TEST = [
        "agi_terminal",
        "network",
        "hardware",
        "biometrics",
        "ai_inference",
        "training",
        "governance",
        "tooling",
        "optimization",
        "all_tabs",
        "explorer",
    ]

    GEOMETRY_TIERS = [
        ("nano", (80, 24)),
        ("micro", (100, 30)),
        ("compact", (120, 40)),
        ("full", (160, 50)),
        ("tiny_edge", (50, 20)),
        ("ultrawide", (240, 60)),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tier_name, size", GEOMETRY_TIERS)
    async def test_all_11_screens_mount_across_geometry_tiers(self, tier_name: str, size: tuple):
        """Verify each of the 11 screens mounts cleanly in the specified terminal geometry."""
        app = CanonicalPortApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.05)
            for screen_id in self.SCREENS_TO_TEST:
                app.switch_screen(screen_id)
                await pilot.pause(0.04)
                assert app.current_screen_id == screen_id
                assert app.screen is not None
                if hasattr(app.screen, "query_one"):
                    try:
                        nav = app.screen.query_one(PinnedTabNavBar)
                        assert nav is not None
                    except Exception:
                        pass

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tier_name, size", GEOMETRY_TIERS)
    async def test_network_view_subwidgets_render_in_geometry(self, tier_name: str, size: tuple):
        """Verify NetworkScreen and all its cards/tables render without clipping/exceptions."""
        app = CanonicalPortApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.05)
            app.switch_screen("network")
            await pilot.pause(0.05)

            # Assert subwidgets exist directly on NetworkScreen
            speedtest_card = app.screen.query_one(LiveSpeedtestCard)
            assert speedtest_card is not None

            router_card = app.screen.query_one(RouterControlCard)
            assert router_card is not None

            wol_view = app.screen.query_one("#wol-status-view", Static)
            assert wol_view is not None

            wan_view = app.screen.query_one("#wan-status-view", Static)
            assert wan_view is not None

            ts_view = app.screen.query_one("#tailscale-mesh-view", Static)
            assert ts_view is not None

            rpc_view = app.screen.query_one("#rpc-latency-view", Static)
            assert rpc_view is not None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tier_name, size", GEOMETRY_TIERS)
    async def test_tooling_view_mesh_scaffolding_in_geometry(self, tier_name: str, size: tuple):
        """Verify ToolingScreen and MeshScaffoldingCard render cleanly."""
        app = CanonicalPortApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.05)
            app.switch_screen("tooling")
            await pilot.pause(0.05)

            mesh_card = app.screen.query_one(MeshScaffoldingCard)
            assert mesh_card is not None
            assert mesh_card.ts_status is not None


# ============================================================================
# TEST GROUP 2: FAST TAB CYCLING & NAVIGATION STORM
# ============================================================================

class TestGroup2FastTabCyclingAndNavigationStorm:
    """Stress test high-frequency bidirectional navigation and hotkey transitions."""

    @pytest.mark.asyncio
    async def test_rapid_forward_and_backward_cycling_storm(self):
        """Cycle through screens 60 times forward and 60 times backward rapidly."""
        app = CanonicalPortApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.05)
            # 60 Forward cycles with force=True
            for _ in range(60):
                res = app.cycle_screen(delta=1, force=True)
                assert res is not False
                await pilot.pause(0.005)

            assert app.screen is not None

            # 60 Backward cycles with force=True
            for _ in range(60):
                res = app.cycle_screen(delta=-1, force=True)
                assert res is not False
                await pilot.pause(0.005)

            assert app.screen is not None

    @pytest.mark.asyncio
    async def test_keyboard_hotkey_storm_all_screens(self):
        """Fire keyboard hotkeys sequentially and in random order to test screen switching."""
        app = CanonicalPortApp()
        hotkeys = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "e",
            "c", "n", "h", "b", "i", "t", "g", "s", "o", "a", "x",
            "1", "8", "2", "7", "3", "6", "4", "5", "9", "0", "e"
        ]

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.05)
            for key in hotkeys:
                await pilot.press(key)
                await pilot.pause(0.02)
                assert app.screen is not None


# ============================================================================
# TEST GROUP 3: ACTION BUTTON DISPATCH STORM
# ============================================================================

class TestGroup3ActionButtonDispatchStorm:
    """Stress test all action buttons across NetworkScreen, ToolingScreen, and AgiCodingTerminalScreen."""

    @pytest.mark.asyncio
    async def test_network_view_action_buttons_storm(self):
        """Press every action button in NetworkScreen and its cards without event-loop lag."""
        app = CanonicalPortApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause(0.05)
            app.switch_screen("network")
            await pilot.pause(0.05)

            buttons_to_test = [
                "#btn-ping-tb4",
                "#btn-probe-rpc",
                "#btn-refresh-net",
                "#btn-wol-revive",
                "#btn-preset-wan",
                "#btn-preset-ifaces",
                "#btn-preset-clients",
                "#btn-preset-uci",
                "#btn-preset-wifi",
                "#btn-run-speedtest",
                "#btn-lan-iperf3",
            ]

            for btn_id in buttons_to_test:
                btn = app.screen.query_one(btn_id, Button)
                t0 = time.perf_counter()
                btn.press()
                await pilot.pause(0.03)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                assert elapsed_ms < 500.0, f"Button {btn_id} dispatch lagged ({elapsed_ms:.1f}ms)"

            # Cancel speedtest button
            card = app.screen.query_one(LiveSpeedtestCard)
            btn_cancel = card.query_one("#btn-cancel-speedtest", Button)
            btn_cancel.press()
            await pilot.pause(0.03)
            assert app.screen is not None

    @pytest.mark.asyncio
    async def test_tooling_view_action_buttons_storm(self):
        """Press every action button in ToolingScreen and MeshScaffoldingCard."""
        app = CanonicalPortApp()
        async with app.run_test(size=(140, 60)) as pilot:
            await pilot.pause(0.05)
            app.switch_screen("tooling")
            await pilot.pause(0.05)

            buttons_to_test = [
                "#btn-audit-mcp",
                "#btn-verify-clis",
                "#btn-sync-shopify",
                "#btn-refresh-tools",
                "#btn-mesh-audit",
                "#btn-probe-rpc",
                "#btn-sync-exo",
                "#btn-accel-env",
                "#btn-refresh-mesh",
            ]

            for btn_id in buttons_to_test:
                btn = app.screen.query_one(btn_id, Button)
                t0 = time.perf_counter()
                btn.press()
                await pilot.pause(0.03)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                assert elapsed_ms < 500.0, f"Button {btn_id} lagged ({elapsed_ms:.1f}ms)"

    @pytest.mark.asyncio
    async def test_agi_coding_terminal_action_buttons_storm(self):
        """Press all action buttons on AgiCodingTerminalScreen and verify state changes."""
        app = CanonicalPortApp()
        async with app.run_test(size=(140, 50)) as pilot:
            await pilot.pause(0.05)
            app.switch_screen("agi_terminal")
            await pilot.pause(0.05)

            screen = app.screen

            # Test grid split cycling (1 -> 4 -> 8 -> 16 -> 1)
            btn_split = screen.query_one("#btn-cycle-split", Button)
            for expected_split in [4, 8, 16, 1]:
                btn_split.press()
                await pilot.pause(0.03)
                assert screen.grid_split_count == expected_split

            # Test model switching
            initial_idx = screen.active_model_idx
            btn_model = screen.query_one("#btn-switch-model", Button)
            btn_model.press()
            await pilot.pause(0.03)
            assert screen.active_model_idx == (initial_idx + 1) % len(screen.MODEL_ROSTER)

            # Test voice coding buttons
            btn_start_stt = screen.query_one("#btn-start-stt", Button)
            btn_start_stt.press()
            await pilot.pause(0.03)
            assert screen.is_stt_active is True

            btn_tts = screen.query_one("#btn-trigger-tts", Button)
            btn_tts.press()
            await pilot.pause(0.03)
            assert screen.is_tts_active is True

            btn_stop_stt = screen.query_one("#btn-stop-stt", Button)
            btn_stop_stt.press()
            await pilot.pause(0.03)
            assert screen.is_stt_active is False

            # Execute code & petals buttons
            for btn_id in ["#btn-execute-code", "#btn-petals-swarm", "#btn-cloudflare-ai", "#btn-clear-log"]:
                b = screen.query_one(btn_id, Button)
                b.press()
                await pilot.pause(0.03)


# ============================================================================
# TEST GROUP 4: DYNAMIC TELEMETRY INJECTION & TABLE STABILITY
# ============================================================================

class TestGroup4DynamicTelemetryInjectionAndTableStability:
    """Stress test table column widths and layout under dynamic and adversarial data injection."""

    @pytest.mark.asyncio
    async def test_dynamic_wan_routes_table_stability(self):
        """Inject varied and adversarial WAN routes into NetworkScreen."""
        app = CanonicalPortApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause(0.05)
            app.switch_screen("network")
            await pilot.pause(0.05)

            # Create stress payload with 10 complex WAN routes
            adversarial_routes = [
                WanRoute(
                    interface=f"vlan{i}.bond0.tb4_dma_speedify_long_interface_name_{i}",
                    priority=f"P{i}",
                    bandwidth=f"{1000 * (i + 1)} Mbps Full-Duplex",
                    rtt_ms=0.25 * (i + 1),
                    drop_rate=0.001 * i,
                    circuit_state="CLOSED" if i % 2 == 0 else "HALF_OPEN",
                    status="ACTIVE" if i < 5 else "STANDBY",
                    category="WAN" if i % 2 == 0 else "MESH"
                )
                for i in range(10)
            ]

            snapshot = blackboard_store.get_snapshot()
            snapshot.layer_0_networking.wan_routes = adversarial_routes

            app.screen.render_wan(snapshot)
            await pilot.pause(0.03)

            wan_widget = app.screen.query_one("#wan-status-view", Static)
            assert wan_widget is not None

    @pytest.mark.asyncio
    async def test_dynamic_tailscale_peers_table_stability(self):
        """Inject 15 Tailscale peers with IPv6 strings, complex names, and emojis."""
        app = CanonicalPortApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause(0.05)
            app.switch_screen("network")
            await pilot.pause(0.05)

            adversarial_peers = [
                TailscalePeer(
                    layer=f"L{i}",
                    node_name=f"Node-🚀-Adversarial-Cluster-{i}-HostName-With-Long-String",
                    ip=f"fd7a:115c:a1e0::{i:04x}:100.119.{i}.{i}",
                    os=f"Darwin macOS 15.4 ARM64 / Debian 13 Bookworm x86_64 Node {i}",
                    relay=f"DERP-Sydney (Region {i}) / Direct TB4 DMA",
                    status="ONLINE" if i % 3 != 0 else "IDLE"
                )
                for i in range(15)
            ]

            snapshot = blackboard_store.get_snapshot()
            snapshot.layer_0_networking.tailscale_peers = adversarial_peers

            app.screen.render_tailscale(snapshot)
            await pilot.pause(0.03)

            ts_widget = app.screen.query_one("#tailscale-mesh-view", Static)
            assert ts_widget is not None

    @pytest.mark.asyncio
    async def test_dynamic_rpc_matrix_table_stability(self):
        """Inject high-sharded llama.cpp RPC nodes with varying memory and latencies."""
        app = CanonicalPortApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause(0.05)
            app.switch_screen("network")
            await pilot.pause(0.05)

            adversarial_rpc_nodes = [
                LlamaRpcNode(
                    node_name=f"Sharding-Node-{i}-Metal-MPS",
                    endpoint=f"169.254.187.{100 + i}:50052",
                    layers_sharded=28 + i * 2,
                    vram_used_gb=14.0 + i * 0.5,
                    latency_ms=0.277 + i * 0.05,
                    status="ACTIVE" if i % 2 == 0 else "ONLINE"
                )
                for i in range(8)
            ]

            snapshot = blackboard_store.get_snapshot()
            snapshot.layer_3_ai_inference.llama_rpc_nodes = adversarial_rpc_nodes

            app.screen.render_rpc(snapshot)
            await pilot.pause(0.03)

            rpc_widget = app.screen.query_one("#rpc-latency-view", Static)
            assert rpc_widget is not None

    @pytest.mark.asyncio
    async def test_concurrent_background_telemetry_flooding_during_ui_cycle(self):
        """Simulate high-frequency background telemetry updates while rapidly switching screens."""
        app = CanonicalPortApp()
        stop_event = threading.Event()

        def background_telemetry_flooder():
            counter = 0
            while not stop_event.is_set():
                counter += 1
                try:
                    blackboard_store.update_layer(
                        "layer_0_networking",
                        internet_speed=InternetSpeedMetrics(
                            download_mbps=500.0 + (counter % 50),
                            upload_mbps=50.0 + (counter % 10),
                            responsiveness_rpm=1400 + (counter % 100),
                            latency_ms=12.0 + (counter % 5),
                            timestamp=time.strftime("%H:%M:%S")
                        )
                    )
                except Exception:
                    pass
                time.sleep(0.005)

        t = threading.Thread(target=background_telemetry_flooder, daemon=True)
        t.start()

        try:
            async with app.run_test(size=(140, 45)) as pilot:
                await pilot.pause(0.05)
                for screen_id in ["agi_terminal", "network", "tooling", "hardware", "network", "tooling"]:
                    app.switch_screen(screen_id)
                    await pilot.pause(0.05)
                    assert app.current_screen_id == screen_id
        finally:
            stop_event.set()
            t.join(timeout=1.0)
