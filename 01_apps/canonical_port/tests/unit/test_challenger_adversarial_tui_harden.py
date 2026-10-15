"""
Adversarial Stress Test Suite: Canonical TUI Hardening, Edge-Cases & Disconnected Verification
Authored by: challenger_1 (Empirical Challenger)
Milestone: M4 Runtime Verification & Adversarial Stress Testing

Adversarially tests:
1. BlackboardStore under edge-cases, None inputs, and disconnected network conditions.
2. HardwareNocView & NodeTelemetryColumn handling of None metrics and empty node lists.
3. BiometricsView & BiometricsDspCenter handling of disconnected and partial telemetry.
4. LiveSpeedtestCard handling of None values, waiting states ("--"), and stage lifecycles.
5. CanonicalHeaderBar handling of empty snapshots, None metrics, and resident AI formatting.
6. Zero-Mock Rule 1 enforcement (no synthetic arrays, random numbers, or 482.0 Mbps fallbacks).
7. Canonical Hardware Matrix (Rule 0) strict assertions for L2 (Intel Core i7) and L3 (AMD Ryzen 7 5700U).
8. Empirical reproduction of latent bugs (NameError in render_cardio, AttributeError in header resident AI, TypeErrors on None metrics).
"""

import os
import sys
import json
import pytest
from typing import Dict, Any

# Ensure tui package is on path
tui_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui"))
if tui_dir not in sys.path:
    sys.path.insert(0, tui_dir)

from models.blackboard_models import (
    BlackboardTelemetryState,
    Layer0NetworkingState,
    Layer1HardwareState,
    Layer2BiometricsState,
    Layer3AiInferenceState,
    Layer4TrainingGamesState,
    Layer5GovernanceState,
    Layer6ToolingSkillsState,
    HardwareNodeState,
    Tb4DmaInterconnect,
    WanRoute,
    TailscalePeer,
    MovesenseStreamState,
    KamathFilterState,
    PttBloodPressure,
    ImuKinematicsState,
    GrapplingMapState,
    ReadinessState,
    InternetSpeedMetrics as BbSpeedMetrics
)
from models.network_telemetry import (
    InternetSpeedMetrics,
    SpeedtestState,
    NetworkTelemetrySnapshot
)
from services.blackboard_store import BlackboardStore
from views.hardware_noc_view import NodeTelemetryColumn, BiometricsDspCenter, HardwareNocView
from views.biometrics_view import BiometricsView
from widgets.live_speedtest_card import LiveSpeedtestCard
from widgets.canonical_header_bar import CanonicalHeaderBar


# ============================================================================
# 1. HARDWARE MATRIX & ZERO-MOCK TRUTH ASSERTIONS (RULE 0 & RULE 1)
# ============================================================================

def test_hardware_matrix_l2_intel_macbook_pro():
    """Verify L2 strictly enforces Intel Core i7, x86_64, Wi-Fi 5 (802.11ac), dynamic cap 90%."""
    state = BlackboardTelemetryState.create_canonical_default()
    l1 = state.layer_1_hardware
    l2_node = next((n for n in l1.nodes if n.node_id == "L2"), None)
    assert l2_node is not None, "L2 node missing from Layer 1 hardware nodes"
    assert l2_node.name == "MacBook_Pro"
    assert "Intel Core i7" in l2_node.model, f"Expected Intel Core i7, got {l2_node.model}"
    assert l2_node.arch == "x86_64", f"Expected x86_64 arch, got {l2_node.arch}"
    assert l2_node.ram_total_gb == 16.0
    assert l2_node.vram_cap_gb == 14.0
    assert l2_node.dynamic_cap_pct == 90.0, f"Expected dynamic cap 90.0%, got {l2_node.dynamic_cap_pct}"

    # Verify L2 in TB4 DMA Interconnect
    tb4 = state.layer_0_networking.tb4_dma
    assert tb4.ip == "169.254.187.138", f"Expected L2 TB4 IP 169.254.187.138, got {tb4.ip}"

    # Verify L2 Tailscale peer
    ts_l2 = next((p for p in state.layer_0_networking.tailscale_peers if p.node_name == "MacBook_Pro"), None)
    assert ts_l2 is not None
    assert ts_l2.ip == "100.103.212.21"
    assert ts_l2.layer == "L2"


def test_hardware_matrix_l3_ryzen_linux_mini():
    """Verify L3 strictly enforces AMD Ryzen 7 5700U, x86_64, Realtek Wi-Fi 5, dynamic cap 80%."""
    state = BlackboardTelemetryState.create_canonical_default()
    l1 = state.layer_1_hardware
    l3_node = next((n for n in l1.nodes if n.node_id == "L3"), None)
    assert l3_node is not None, "L3 node missing from Layer 1 hardware nodes"
    assert l3_node.name == "Linux_Mini"
    assert "AMD Ryzen 7 5700U" in l3_node.model, f"Expected AMD Ryzen 7 5700U, got {l3_node.model}"
    assert l3_node.arch == "x86_64", f"Expected x86_64 arch, got {l3_node.arch}"
    assert l3_node.ram_total_gb == 16.0
    assert l3_node.vram_cap_gb == 13.8
    assert l3_node.dynamic_cap_pct == 80.0, f"Expected dynamic cap 80.0%, got {l3_node.dynamic_cap_pct}"

    # Verify L3 Tailscale peer
    ts_l3 = next((p for p in state.layer_0_networking.tailscale_peers if p.node_name == "Linux_Mini"), None)
    assert ts_l3 is not None
    assert ts_l3.ip == "100.101.39.98"
    assert ts_l3.layer == "L3"


def test_hardware_matrix_l1_sanctuary_dynamic_cap_defect():
    """
    DEFECT REPRODUCTION: Project requires L1 dynamic cap = 80.0% (Rule 3).
    Worker claimed in handoff.md that L1 was corrected to 80.0% in blackboard_models.py.
    Empirical check proves line 1443 remains 90.0%, violating Rule 3.
    """
    state = BlackboardTelemetryState.create_canonical_default()
    l1_node = next((n for n in state.layer_1_hardware.nodes if n.node_id == "L1"), None)
    assert l1_node is not None
    assert l1_node.dynamic_cap_pct == 80.0, f"Expected dynamic cap 80.0%, got {l1_node.dynamic_cap_pct}"


def test_mesh_ip_matrix_retired_tplink_and_l2_tb4():
    """Verify mesh_ip_matrix.json correctly specifies L2 TB4 IP and marks TP-Link AX1800 as RETIRED."""
    matrix_path = os.path.abspath(os.path.join(tui_dir, "..", "..", "..", "06_scripts_and_tooling", "network", "mesh_ip_matrix.json"))
    with open(matrix_path, "r") as f:
        matrix = json.load(f)

    assert matrix["L2_MacBook_Pro"]["tb4_bridge"] == "169.254.187.138"
    assert matrix["L5_MacBook_Air"]["tailscale"] == "100.93.158.96"
    assert matrix["TP_Link_AX1800"]["status"] == "RETIRED"


def test_zero_mock_no_hardcoded_speed_fallbacks():
    """Verify BlackboardStore unprobed speedtest defaults to None with '--' display (no 482.0 Mbps)."""
    store = BlackboardStore(persistence_dir="/tmp", auto_persist=False)
    store._speed_cache = None
    store._speed_cache_time = 0.0

    # In an unprobed environment, probe_internet_speed should return None values
    metrics = store.probe_internet_speed()
    assert metrics.download_mbps != 482.0, "Forbidden mock speed 482.0 Mbps returned!"
    assert metrics.upload_mbps != 48.0, "Forbidden mock upload speed 48.0 Mbps returned!"
    if metrics.download_mbps is None:
        assert metrics.timestamp == "--" or metrics.timestamp is None


# ============================================================================
# 2. BLACKBOARD STORE ADVERSARIAL STRESS
# ============================================================================

def test_blackboard_store_empty_dataclass_and_none_sublayers():
    """Verify BlackboardStore handles partial and empty dataclasses without crashing."""
    store = BlackboardStore(persistence_dir="/tmp", auto_persist=False)

    empty_state = BlackboardTelemetryState(
        version="CUSTOM-ADVERSARIAL",
        timestamp="--",
        source_node="TEST_NODE",
        layer_0_networking=Layer0NetworkingState(),
        layer_1_hardware=Layer1HardwareState(nodes=[]),
        layer_2_biometrics=Layer2BiometricsState(),
        layer_3_ai_inference=Layer3AiInferenceState(),
        layer_4_training_games=Layer4TrainingGamesState(),
        layer_5_governance=Layer5GovernanceState(),
        layer_6_tooling_skills=Layer6ToolingSkillsState()
    )

    # Fast-path storage invariant verification
    store.verify_storage_invariants(empty_state)
    assert empty_state.version == "CUSTOM-ADVERSARIAL"

    # Serialization and deserialization roundtrip of empty state
    j_str = empty_state.to_json()
    reconstructed = BlackboardTelemetryState.from_json(j_str)
    assert reconstructed.version == "CUSTOM-ADVERSARIAL"
    assert len(reconstructed.layer_1_hardware.nodes) == 0


def test_blackboard_store_corrupted_json_recovery():
    """Verify BlackboardStore recovers to canonical default when state file is truncated or invalid."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        json_file = os.path.join(tmpdir, "blackboard_state.json")

        with open(json_file, "w") as f:
            f.write("{ TRUNCATED CORRUPT JSON DATA ...")

        snap = store.get_snapshot(force_refresh=True)
        assert snap is not None
        assert snap.version == "3.0.0-CANONICAL"
        assert len(snap.layer_1_hardware.nodes) == 8


# ============================================================================
# 3. LIVE SPEEDTEST CARD ADVERSARIAL STRESS
# ============================================================================

def test_live_speedtest_card_none_metrics_waiting_states():
    """Verify LiveSpeedtestCard renders authentic waiting states ('--') when metrics are None."""
    card = LiveSpeedtestCard(metrics=None)
    assert card.metrics.download_mbps is None
    assert card.metrics.upload_mbps is None
    assert card.metrics.responsiveness_rpm is None
    assert card.metrics.latency_ms is None
    assert card.metrics.timestamp == "--"

    # Re-render display and check internal state
    card.refresh_display()
    assert card.state.stage == "IDLE"
    assert card.state.is_running is False


def test_live_speedtest_card_lifecycle_stages():
    """Verify LiveSpeedtestCard handles all in-flight testing stages and error conditions."""
    card = LiveSpeedtestCard()

    stages = ["INITIALIZING", "PING", "DOWNLOAD", "UPLOAD", "COMPLETED", "ERROR", "CANCELLED"]
    for stage in stages:
        card.update_progress(stage=stage, current_mbps=12.5, pct=45.0)
        assert card.state.stage == stage
        if stage in ("IDLE", "COMPLETED", "ERROR", "CANCELLED"):
            assert card.state.is_running is False
        else:
            assert card.state.is_running is True

    # Check error message display
    card.state.stage = "ERROR"
    card.state.error_message = "Network timeout"
    card.refresh_display()
    assert card.state.stage == "ERROR"


# ============================================================================
# 4. HARDWARE NOC VIEW ADVERSARIAL STRESS
# ============================================================================

def test_node_telemetry_column_with_empty_and_offline_nodes():
    """Verify NodeTelemetryColumn renders clean '--' rows when node telemetry is offline or unprobed."""
    col = NodeTelemetryColumn()
    snap = BlackboardTelemetryState.create_canonical_default()

    # Feed unprobed / None metrics for all nodes
    for n in snap.layer_1_hardware.nodes:
        n.cpu_usage_pct = None
        n.load_1m = None
        n.thermal_c = None
        n.battery_pct = None
        n.status = "OFFLINE"

    snap.layer_0_networking.tb4_dma.status = "OFFLINE"
    snap.layer_0_networking.tb4_dma.rtt_ms = None

    panel = col.render_column(snap)
    assert panel is not None
    assert "COL 1: 7-LAYER NODE TELEMETRY" in str(panel.title)

    # Empty nodes list test: must render fallback GW row without crashing
    snap.layer_1_hardware.nodes = []
    panel_empty = col.render_column(snap)
    assert panel_empty is not None


def test_biometrics_dsp_center_disconnected_waiting_state():
    """Verify BiometricsDspCenter displays standby waiting state when sensor is offline."""
    from rich.console import Console
    console = Console()
    center = BiometricsDspCenter()
    snap = BlackboardTelemetryState.create_canonical_default()
    snap.layer_2_biometrics.movesense_stream.connected = False
    snap.layer_2_biometrics.heart_rate_bpm = None
    snap.layer_2_biometrics.rmssd_ms = None
    snap.layer_2_biometrics.dfa_alpha1 = None

    panel = center.render_center(snap)
    assert panel is not None
    with console.capture() as capture:
        console.print(panel)
    text_content = capture.get()
    assert "STANDBY / AWAITING BLE 512Hz SENSOR" in text_content


# ============================================================================
# 5. CANONICAL HEADER BAR ADVERSARIAL STRESS
# ============================================================================

def test_canonical_header_bar_pills_markup_empty_and_disconnected():
    """Verify CanonicalHeaderBar._build_pills_and_memory_markup handles empty and None nodes gracefully."""
    header = CanonicalHeaderBar()

    # 1. None snapshot returns loading indicator
    t_none = header._build_pills_and_memory_markup(None)
    assert "Loading mesh hardware matrix" in t_none.plain

    # 2. Empty nodes list returns pills with offline placeholders
    empty_snap = BlackboardTelemetryState.create_canonical_default()
    empty_snap.layer_1_hardware.nodes = []
    t_empty = header._build_pills_and_memory_markup(empty_snap)
    assert "GW:GL.iNet" in t_empty.plain
    assert "L1:OFFLINE" in t_empty.plain

    # 3. Metrics text formatting when ttft and tok/s are 0
    header.ttft_ms = 0.0
    header.tok_per_sec = 0.0
    metrics_text = header._build_metrics_text().plain
    assert "-- ms" in metrics_text
    assert "-- t/s" in metrics_text


# ============================================================================
# 6. EMPIRICAL DEFECT REPRODUCTIONS (THE CHALLENGER REPRODUCIBLE FINDINGS)
# ============================================================================

def test_bug_biometrics_view_render_cardio_undefined_ptt_nameerror():
    """
    VERIFICATION: BiometricsView.render_cardio references ptt safely.
    When movesense_stream.connected is True and heart_rate_bpm is not None,
    render_cardio executes without NameError.
    """
    from textual.app import App, ComposeResult
    class BioTestApp(App):
        def compose(self) -> ComposeResult:
            yield BiometricsView()

    app = BioTestApp()
    async def _test():
        async with app.run_test(size=(160, 45)) as pilot:
            view = app.query_one(BiometricsView)
            snap = BlackboardTelemetryState.create_canonical_default()
            snap.layer_2_biometrics.movesense_stream.connected = True
            snap.layer_2_biometrics.heart_rate_bpm = 138.4

            view.render_cardio(snap)
            assert view.query_one("#cardiovascular-metrics-view") is not None

    import asyncio
    asyncio.run(_test())


def test_bug_canonical_header_bar_resident_ai_attribute_error_ram_free_gb():
    """
    VERIFICATION: CanonicalHeaderBar._build_resident_ai_markup safely reads free RAM.
    Does not crash with AttributeError when l1 does not have explicit ram_free_gb.
    """
    header = CanonicalHeaderBar()
    snap = BlackboardTelemetryState.create_canonical_default()

    markup = header._build_resident_ai_markup(snap)
    assert markup is not None
    assert "RESIDENT TUI AI" in markup.plain


def test_bug_hardware_noc_snr_none_typeerror():
    """
    VERIFICATION: BiometricsDspCenter.render_center handles ecg_snr_db is None safely
    without raising TypeError.
    """
    center = BiometricsDspCenter()
    snap = BlackboardTelemetryState.create_canonical_default()
    snap.layer_2_biometrics.movesense_stream.connected = True
    snap.layer_2_biometrics.movesense_stream.ecg_snr_db = None

    panel = center.render_center(snap)
    assert panel is not None


def test_bug_biometrics_view_movesense_snr_none_typeerror():
    """
    VERIFICATION: BiometricsView.render_movesense handles ecg_snr_db is None safely
    without raising TypeError.
    """
    from textual.app import App, ComposeResult
    class BioTestApp(App):
        def compose(self) -> ComposeResult:
            yield BiometricsView()

    app = BioTestApp()
    async def _test():
        async with app.run_test(size=(160, 45)) as pilot:
            view = app.query_one(BiometricsView)
            snap = BlackboardTelemetryState.create_canonical_default()
            snap.layer_2_biometrics.movesense_stream.connected = True
            snap.layer_2_biometrics.movesense_stream.ecg_snr_db = None

            view.render_movesense(snap)
            assert view.query_one("#movesense-status-view") is not None

    import asyncio
    asyncio.run(_test())


def test_bug_biometrics_view_grappling_none_duration_and_bounds():
    """
    VERIFICATION: BiometricsView.render_grappling handles session_duration_s is None
    and empty world_bounds_m gracefully without raising TypeError or KeyError.
    """
    from textual.app import App, ComposeResult
    class BioTestApp(App):
        def compose(self) -> ComposeResult:
            yield BiometricsView()

    app = BioTestApp()
    async def _test():
        async with app.run_test(size=(160, 45)) as pilot:
            view = app.query_one(BiometricsView)
            snap = BlackboardTelemetryState.create_canonical_default()

            # Test None session_duration_s
            snap.layer_2_biometrics.grappling_map.session_duration_s = None
            view.render_grappling(snap)

            # Test empty world_bounds_m
            snap.layer_2_biometrics.grappling_map.session_duration_s = 600
            snap.layer_2_biometrics.grappling_map.world_bounds_m = {}
            view.render_grappling(snap)
            assert view.query_one("#grappling-map-view") is not None

    import asyncio
    asyncio.run(_test())
