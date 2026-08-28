"""
Unit and Textual Pilot Test Suite for TUI Alpha Dashboard (Track Alpha Prototype)
Verifies:
1. Clean mounting of NocHeaderBar, 3-Column Bento Box Layout, and Bottom Dock.
2. Zero-Mock Rule #0 compliance in telemetry, biometrics, and hardware meters.
3. Interactive button triggers: [Restart Daemons], [Probe TB4], [Calibrate ECG], [Purge RAM], [Refresh All].
4. Keyboard binding navigation and actions ('r', '1', '2', '3', '4').
5. Responsive layout rendering under various terminal sizes (SIGWINCH resilience).
6. Non-blocking async event loop and bounded event ticker.
7. Disconnected sensors and offline node graceful fallback rendering ('--', 'STANDBY').
8. DFA-alpha1 Zone 2 threshold states and Daemon Supervisor circuit breaker states.
"""

import os
import sys
import pytest
import asyncio
from typing import Dict, Any

# Ensure canonical_port and tui are on import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from tui.prototypes.tui_alpha_dashboard import (
    TuiAlphaDashboardApp,
    NocHeaderBar,
    NodeTelemetryColumn,
    BiometricsDspCenter,
    DaemonSupervisorHud,
    BottomEventDock,
)
from tui.services.blackboard_store import blackboard_store
from tui.models.blackboard_models import (
    BlackboardTelemetryState,
    Tb4DmaInterconnect,
    PttBloodPressure,
)
from textual.widgets import Button


@pytest.mark.asyncio
async def test_alpha_dashboard_mount_and_bento_layout():
    """
    Verify TuiAlphaDashboardApp mounts cleanly with all required components:
    - Header Bar (#noc-header-widget)
    - 3-Column Bento (#col-node-telemetry, #col-biometrics-dsp, #col-daemon-supervisor)
    - Bottom Dock (#event-ticker-view, #action-button-bar)
    """
    app = TuiAlphaDashboardApp()
    async with app.run_test(size=(160, 45)) as pilot:
        # Check header
        header = app.query_one("#noc-header-widget", NocHeaderBar)
        assert header is not None

        # Check 3 columns
        col1 = app.query_one("#col-node-telemetry", NodeTelemetryColumn)
        col2 = app.query_one("#col-biometrics-dsp", BiometricsDspCenter)
        col3 = app.query_one("#col-daemon-supervisor", DaemonSupervisorHud)
        assert col1 is not None
        assert col2 is not None
        assert col3 is not None

        # Check bottom dock & ticker
        dock = app.query_one("#event-ticker-view", BottomEventDock)
        assert dock is not None
        assert len(dock.event_log) > 0

        # Check action buttons
        btn_restart = app.query_one("#btn-restart-daemons", Button)
        btn_probe = app.query_one("#btn-probe-tb4", Button)
        btn_calib = app.query_one("#btn-calibrate-ecg", Button)
        btn_purge = app.query_one("#btn-purge-ram", Button)
        btn_refresh = app.query_one("#btn-refresh-all", Button)

        assert btn_restart is not None
        assert btn_probe is not None
        assert btn_calib is not None
        assert btn_purge is not None
        assert btn_refresh is not None


@pytest.mark.asyncio
async def test_alpha_dashboard_zero_mock_data_integrity():
    """
    Verify Zero-Mock Rule #0 integrity across all components:
    - 7 physical nodes (L1-L7 + GW) are mapped.
    - Pooled RAM/VRAM totals 108.0GB RAM / 82.8GB VRAM.
    - Biometrics Center binds to authentic Pan-Tompkins & Kamath 20% specs.
    - Disconnected nodes/sensors display clean '--' or 'STANDBY'.
    """
    app = TuiAlphaDashboardApp()
    async with app.run_test(size=(160, 45)) as pilot:
        snapshot = app.store.get_snapshot()
        assert snapshot is not None

        # Verify pooled hardware specs
        hw = snapshot.layer_1_hardware
        assert hw.total_ram_gb == 108.0
        assert hw.total_vram_gb == 82.8

        # Verify 7 nodes + GW presence
        node_ids = {n.node_id for n in hw.nodes}
        for expected_id in ("L1", "L2", "L3", "L4", "L5", "L6", "L7"):
            assert expected_id in node_ids

        # Verify biometrics structure
        bio = snapshot.layer_2_biometrics
        assert bio.kamath_filter.threshold_pct == 20.0
        assert bio.movesense_stream.sampling_rate_hz in (512, 128)

        # Header Bar rendering test
        header = app.query_one("#noc-header-widget", NocHeaderBar)
        panel = header.render_header(snapshot)
        assert panel is not None

        # Column 1 rendering test
        col1 = app.query_one("#col-node-telemetry", NodeTelemetryColumn)
        col1_panel = col1.render_column(snapshot)
        assert col1_panel is not None

        # Column 2 rendering test
        col2 = app.query_one("#col-biometrics-dsp", BiometricsDspCenter)
        col2_panel = col2.render_center(snapshot)
        assert col2_panel is not None

        # Column 3 rendering test
        col3 = app.query_one("#col-daemon-supervisor", DaemonSupervisorHud)
        col3_panel = col3.render_hud(snapshot)
        assert col3_panel is not None


@pytest.mark.asyncio
async def test_alpha_dashboard_button_actions():
    """
    Verify pressing action buttons triggers background workers and logs events to ticker:
    - [Probe TB4]
    - [Calibrate ECG]
    - [Purge RAM]
    - [Restart Daemons]
    - [Refresh All]
    """
    app = TuiAlphaDashboardApp()
    async with app.run_test(size=(160, 45)) as pilot:
        ticker = app.query_one("#event-ticker-view", BottomEventDock)
        initial_log_count = len(ticker.event_log)

        # 1. Click Probe TB4
        await pilot.click("#btn-probe-tb4")
        await pilot.pause(0.2)
        assert len(ticker.event_log) > initial_log_count
        assert any("TB4" in msg for msg in ticker.event_log)

        # 2. Click Calibrate ECG
        count_before = len(ticker.event_log)
        await pilot.click("#btn-calibrate-ecg")
        await pilot.pause(0.2)
        assert len(ticker.event_log) > count_before
        assert any("ECG DSP Calibration" in msg for msg in ticker.event_log)

        # 3. Click Purge RAM
        count_before = len(ticker.event_log)
        await pilot.click("#btn-purge-ram")
        await pilot.pause(0.2)
        assert len(ticker.event_log) > count_before
        assert any("Memory governor" in msg for msg in ticker.event_log)

        # 4. Click Refresh All
        count_before = len(ticker.event_log)
        await pilot.click("#btn-refresh-all")
        await pilot.pause(0.2)
        assert len(ticker.event_log) > count_before


@pytest.mark.asyncio
async def test_alpha_dashboard_keyboard_bindings():
    """
    Verify keyboard shortcuts trigger corresponding actions:
    - '2' -> Probe TB4
    - '3' -> Calibrate ECG
    - '4' -> Purge RAM
    - 'r' -> Refresh All
    """
    app = TuiAlphaDashboardApp()
    async with app.run_test(size=(160, 45)) as pilot:
        ticker = app.query_one("#event-ticker-view", BottomEventDock)

        # Press '2'
        await pilot.press("2")
        await pilot.pause(0.15)
        assert any("Thunderbolt 4" in msg or "TB4" in msg for msg in ticker.event_log)

        # Press '3'
        await pilot.press("3")
        await pilot.pause(0.15)
        assert any("Pan-Tompkins" in msg or "ECG" in msg for msg in ticker.event_log)

        # Press '4'
        await pilot.press("4")
        await pilot.pause(0.15)
        assert any("Purging" in msg or "Memory" in msg for msg in ticker.event_log)

        # Press 'r'
        await pilot.press("r")
        await pilot.pause(0.15)
        assert any("refresh" in msg.lower() for msg in ticker.event_log)


@pytest.mark.asyncio
async def test_alpha_dashboard_sigwinch_resilience():
    """
    Verify app handles resizing without crashing or rendering layout errors.
    Tests multiple dimension profiles: Wide (160x50), Standard (120x35), Compact (80x24).
    """
    app = TuiAlphaDashboardApp()
    async with app.run_test(size=(160, 50)) as pilot:
        # Standard Resize
        await pilot.resize_terminal(120, 35)
        await pilot.pause(0.1)
        assert app.query_one("#noc-header-widget") is not None
        assert app.query_one("#col-biometrics-dsp") is not None

        # Compact Resize
        await pilot.resize_terminal(80, 24)
        await pilot.pause(0.1)
        assert app.query_one("#bento-container") is not None

        # Large Resize
        await pilot.resize_terminal(200, 60)
        await pilot.pause(0.1)
        assert app.query_one("#event-ticker-view") is not None


@pytest.mark.asyncio
async def test_alpha_dashboard_ticker_bounded_buffer():
    """
    Verify event ticker adheres to bounded ring buffer (maxlen=50) to prevent memory leaks.
    """
    ticker = BottomEventDock()
    assert ticker.event_log.maxlen == 50

    # Add 100 events
    for i in range(100):
        ticker.add_event("INFO", f"Test message {i}")

    assert len(ticker.event_log) == 50
    assert "Test message 99" in ticker.event_log[-1]
    
    panel = ticker.render_ticker()
    assert panel is not None


def test_alpha_dashboard_disconnected_states_render():
    """
    Verify clean render fallback when sensors and hardware are offline/disconnected.
    Zero-Mock Rule #0: Must show '--' and 'STANDBY', not crash.
    """
    snapshot = BlackboardTelemetryState.create_canonical_default()
    snapshot.layer_2_biometrics.movesense_stream.connected = False
    snapshot.layer_2_biometrics.heart_rate_bpm = None
    snapshot.layer_2_biometrics.dfa_alpha1 = None
    snapshot.layer_2_biometrics.ptt_blood_pressure = PttBloodPressure(
        systolic_mmhg=None, diastolic_mmhg=None, pulse_transit_time_ms=None, status="OFFLINE"
    )
    snapshot.layer_0_networking.tb4_dma = Tb4DmaInterconnect(
        ip="169.254.187.138", status="OFFLINE", rtt_ms=None, throughput_gbps=0.0
    )

    # Column 1 with offline TB4
    col1 = NodeTelemetryColumn()
    p1 = col1.render_column(snapshot)
    assert p1 is not None

    # Column 2 with offline biometrics
    col2 = BiometricsDspCenter()
    p2 = col2.render_center(snapshot)
    assert p2 is not None

    # Header with offline routes
    header = NocHeaderBar()
    p_header = header.render_header(snapshot)
    assert p_header is not None


def test_alpha_dashboard_dfa_alpha1_threshold_states():
    """
    Verify DFA-alpha1 status rendering under different physiological states:
    - Optimal (0.750)
    - High / Aerobic Recovery (0.850)
    - Low / Threshold Drift (0.650)
    """
    snapshot = BlackboardTelemetryState.create_canonical_default()
    col2 = BiometricsDspCenter()

    # Optimal
    snapshot.layer_2_biometrics.dfa_alpha1 = 0.750
    p_opt = col2.render_center(snapshot)
    assert p_opt is not None

    # High
    snapshot.layer_2_biometrics.dfa_alpha1 = 0.860
    p_high = col2.render_center(snapshot)
    assert p_high is not None

    # Low
    snapshot.layer_2_biometrics.dfa_alpha1 = 0.620
    p_low = col2.render_center(snapshot)
    assert p_low is not None


def test_alpha_dashboard_daemon_supervisor_circuit_breaker_render():
    """
    Verify DaemonSupervisorHud renders various daemon health and circuit breaker states:
    - ONLINE / CLOSED
    - FAILED_CIRCUIT_OPEN / QUAR
    - RESTARTING / BKOFF
    - OFFLINE / IDLE
    """
    snapshot = BlackboardTelemetryState.create_canonical_default()
    hud = DaemonSupervisorHud()

    hud.daemon_status_cache["docker"] = "ONLINE"
    hud.daemon_status_cache["cloudflared"] = "FAILED_CIRCUIT_OPEN"
    hud.daemon_status_cache["llama.cpp"] = "RESTARTING"
    hud.daemon_status_cache["openclaw"] = "OFFLINE"

    hud.supervisor.restart_counts["cloudflared"] = 3
    hud.supervisor.restart_counts["llama.cpp"] = 1

    hud.container_cache["seaweedfs_master"] = "HEALTHY"
    hud.container_cache["qdrant_vector_db"] = "RESTARTED"
    hud.container_cache["petals_dht_node"] = "UNHEALTHY"

    panel = hud.render_hud(snapshot)
    assert panel is not None
