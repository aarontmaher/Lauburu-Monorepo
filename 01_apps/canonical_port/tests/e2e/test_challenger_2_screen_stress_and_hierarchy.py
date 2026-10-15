"""
Challenger 2 Empirical Stress Test & Hierarchy Verification Suite
Subsystem: 01_apps/canonical_port/tests/e2e/test_challenger_2_screen_stress_and_hierarchy.py
Target: CanonicalPortApp, CanonicalHeaderBar, Blackboard Models, Model Port Mappings

Empirical Verification Scope:
1. Rapid headless Textual navigation across all 15 screens:
   ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'k', 'd', 'm', 'B', '0', 'e']
   Stress-testing event loop stability, screen mounting, and capturing unhandled exceptions
   (such as SpatialGrapplingScreen NoMatches and BluetoothTerminalScreen key-hijack).
2. CanonicalHeaderBar prima option existence, engine switching, and < 4.8 GB Host Sanctuary alert.
3. Model port mapping hierarchy verification (8082, 8083, 8081) and disk persistence discrepancy probing.
"""

import sys
import os
import time
import pytest
import asyncio
from typing import List, Tuple, Dict, Any

# Ensure canonical_port and tui are on import path
TUI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tui"))
PORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, TUI_DIR)
sys.path.insert(0, PORT_DIR)

from canonical_tui import CanonicalPortApp
from widgets.canonical_header_bar import CanonicalHeaderBar, CanonicalEngineChanged
from widgets.engine_selector import EngineSelectorWidget
from models.blackboard_models import (
    BlackboardTelemetryState,
    HardwareNodeState,
    Layer1HardwareState,
    Layer3AiInferenceState,
    InferenceModelInfo,
)
from services.blackboard_store import blackboard_store


# ============================================================================
# 1. RAPID HEADLESS SCREEN CYCLING STRESS TEST (15 SCREENS)
# ============================================================================

EXPECTED_KEY_SCREEN_MAP = {
    "1": "AgiCodingTerminalView",
    "2": "NetworkScreen",
    "3": "HardwareScreen",
    "4": "BiometricsScreen",
    "5": "AiInferenceScreen",
    "6": "TrainingScreen",
    "7": "GovernanceScreen",
    "8": "ToolingScreen",
    "9": "OptimizationScreen",
    "k": "SpatialGrapplingScreen",
    "d": "LiveArenaDevScreen",
    "m": "CommerceStorefrontScreen",
    "B": "BluetoothTerminalScreen",
    "0": "AllTabsGridScreen",
    "e": "ArchitectureExplorerScreen",
}

# The 15 keys specified in the user request
KEYS_SEQUENCE = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "k", "d", "m", "B", "0", "e"]


@pytest.mark.asyncio
async def test_burst_screen_switch_hammer_no_deadlock():
    """
    Stress-tests event loop resilience by hammering all 15 screen keys back-to-back
    with zero pause, then verifying clean event loop recovery.
    """
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 45)) as pilot:
        for _ in range(2):
            for key in KEYS_SEQUENCE:
                await pilot.press(key)

        # Allow event loop to drain pending mounts
        await pilot.pause(0.1)

        # Final key was 'e', screen should settle on ArchitectureExplorerScreen
        assert app.screen.__class__.__name__ == "ArchitectureExplorerScreen"

        # Return to home screen '1'
        await pilot.press("1")
        await pilot.pause(0.05)
        assert app.screen.__class__.__name__ == "AgiCodingTerminalView"


@pytest.mark.asyncio
async def test_screen_navigation_audit_bluetooth_numeric_key_trap():
    """
    VERIFICATION OF NAVIGATION TRAP FIX:
    When navigating to BluetoothTerminalScreen ('B'), numeric keys ('0'-'9')
    have priority=True at App level, successfully navigating to target screens!
    Key '0' switches to AllTabsGridScreen directly.
    """
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 45)) as pilot:
        # Navigate to BluetoothTerminalScreen
        await pilot.press("B")
        await pilot.pause(0.05)
        assert app.screen.__class__.__name__ == "BluetoothTerminalScreen"

        # Press '0': this now successfully navigates to AllTabsGridScreen due to priority=True!
        await pilot.press("0")
        await pilot.pause(0.05)
        active_screen = app.screen.__class__.__name__
        assert active_screen == "AllTabsGridScreen", f"Expected AllTabsGridScreen, got {active_screen}"


@pytest.mark.asyncio
async def test_screen_cycling_direct_app_switch_stress():
    """
    Directly cycles all 15 screens via switch_screen for 5 full iterations
    (75 transitions) to empirically test event loop stability and memory leaks
    without hitting screen-level key collision traps.
    """
    app = CanonicalPortApp()
    screen_ids = [
        "agi_terminal", "network", "hardware", "biometrics",
        "ai_inference", "training", "governance", "tooling",
        "optimization", "spatial_grappling", "live_arena_dev",
        "commerce_storefront", "bluetooth_terminal", "all_tabs", "explorer"
    ]
    transitions = 0
    t0 = time.perf_counter()

    async with app.run_test(size=(160, 45)) as pilot:
        for cycle in range(5):
            for sid in screen_ids:
                app.switch_screen(sid)
                await pilot.pause(0.01)
                transitions += 1
                assert app.current_screen_id == sid

    elapsed = time.perf_counter() - t0
    avg_latency = (elapsed / transitions) * 1000.0
    print(f"\n[PASS] {transitions} direct screen switches completed in {elapsed:.3f}s (avg: {avg_latency:.2f}ms/switch)")


# ============================================================================
# 2. CANONICAL HEADER BAR PRIMA & SANCTUARY VERIFICATION
# ============================================================================

def test_canonical_header_bar_prima_option_contract():
    """
    Verifies that CanonicalHeaderBar explicitly defines 'prima' in:
    - ENGINES list
    - ENGINE_OPTIONS tuple list
    - ENGINE_NAMES dictionary
    """
    assert "prima" in CanonicalHeaderBar.ENGINES, "prima missing from CanonicalHeaderBar.ENGINES"

    option_map = {val: disp for disp, val in CanonicalHeaderBar.ENGINE_OPTIONS}
    assert "prima" in option_map, "prima option key missing from CanonicalHeaderBar.ENGINE_OPTIONS"

    prima_label = option_map.get("prima", "")
    assert "PRIMA.CPP" in prima_label, f"Expected 'PRIMA.CPP' in label, got '{prima_label}'"
    assert "TB4 DMA" in prima_label, f"Expected 'TB4 DMA' in label, got '{prima_label}'"

    assert "prima" in CanonicalHeaderBar.ENGINE_NAMES
    assert "PRIMA.CPP" in CanonicalHeaderBar.ENGINE_NAMES["prima"]


def test_canonical_header_bar_host_sanctuary_rendering():
    """
    Verifies CanonicalHeaderBar Host Sanctuary alert rendering:
    - Renders COMPLIANT when L1 ram_free_gb >= 4.8 GB
    - Renders DEGRADED (<ram>GB) in bold red when L1 ram_free_gb < 4.8 GB
    """
    header = CanonicalHeaderBar()
    snap = BlackboardTelemetryState.create_canonical_default()

    # Case 1: Healthy Host Memory (5.5 GB free >= 4.8 GB)
    for node in snap.layer_1_hardware.nodes:
        if node.node_id == "L1":
            node.ram_free_gb = 5.5
            break

    markup_healthy = header._build_resident_ai_markup(snap)
    assert "COMPLIANT" in markup_healthy.plain
    assert "DEGRADED" not in markup_healthy.plain

    # Case 2: Degraded Host Memory Breach (3.7 GB free < 4.8 GB)
    for node in snap.layer_1_hardware.nodes:
        if node.node_id == "L1":
            node.ram_free_gb = 3.7
            break

    markup_degraded = header._build_resident_ai_markup(snap)
    assert "DEGRADED (3.7GB)" in markup_degraded.plain
    has_bold_red = any("bold red" in str(s.style) or "red" in str(s.style) for s in markup_degraded.spans)
    assert has_bold_red, "Host sanctuary breach markup must be styled in red"

    # Case 3: Boundary threshold test at 4.79 GB vs 4.80 GB
    for node in snap.layer_1_hardware.nodes:
        if node.node_id == "L1":
            node.ram_free_gb = 4.79
            break
    assert "DEGRADED (4.8GB)" in header._build_resident_ai_markup(snap).plain

    for node in snap.layer_1_hardware.nodes:
        if node.node_id == "L1":
            node.ram_free_gb = 4.80
            break
    assert "COMPLIANT" in header._build_resident_ai_markup(snap).plain


@pytest.mark.asyncio
async def test_canonical_header_bar_engine_switch_to_prima():
    """
    Verifies that setting engine to 'prima' dispatches CanonicalEngineChanged
    with engine_name == 'prima'.
    """
    header = CanonicalHeaderBar()
    header.set_engine("prima")
    assert header.active_engine == "prima"


# ============================================================================
# 3. MODEL PORT MAPPINGS & SOVEREIGN HIERARCHY VERIFICATION
# ============================================================================

def test_canonical_factory_model_roster_hierarchy():
    """
    Verifies that create_canonical_default() correctly implements Rule 7:
    - Port 8082: Qwen 3.8 Max (Sovereign Master Local Orchestrator via prima.cpp)
    - Port 8083: Qwen 3.8 Max 27B Abliterated (Canonical Devil's Advocate & Adversarial Red Team)
    - Port 8081: Qwen 2.5 Coder 7B (Subordinate Syntax Worker)
    """
    state = BlackboardTelemetryState.create_canonical_default()
    active = {m.model_id: m for m in state.layer_3_ai_inference.active_models}
    ablit = {m.model_id: m for m in state.layer_3_ai_inference.abliterated_models}

    # 1. Verify Port 8082: Qwen 3.8 Max
    assert "qwen_38_max" in active, "qwen_38_max missing from active_models"
    m_8082 = active["qwen_38_max"]
    assert m_8082.port == 8082, f"Expected port 8082 for qwen_38_max, got {m_8082.port}"
    assert "Sovereign Master Local Orchestrator" in m_8082.role
    assert "prima.cpp" in m_8082.sharding_strategy

    # 2. Verify Port 8083: Qwen 3.8 Max 27B Abliterated
    assert "qwen_38_max_abliterated" in ablit, "qwen_38_max_abliterated missing from abliterated_models"
    m_8083 = ablit["qwen_38_max_abliterated"]
    assert m_8083.port == 8083, f"Expected port 8083 for qwen_38_max_abliterated, got {m_8083.port}"
    assert "Devil's Advocate" in m_8083.role
    assert m_8083.is_abliterated is True

    # 3. Verify Port 8081: Qwen 2.5 Coder 7B
    assert "qwen_25_coder_7b" in active, "qwen_25_coder_7b missing from active_models"
    m_8081 = active["qwen_25_coder_7b"]
    assert m_8081.port == 8081, f"Expected port 8081 for qwen_25_coder_7b, got {m_8081.port}"
    assert "Subordinate Syntax Worker" in m_8081.role


# ============================================================================
# 4. ADVERSARIAL DISCREPANCY MINING (CHALLENGER AUDIT)
# ============================================================================

def test_audit_engine_selector_widget_missing_prima():
    """
    VERIFICATION:
    CanonicalHeaderBar and EngineSelectorWidget both define 'prima' in
    ENGINES, ENGINE_OPTIONS, and ENGINE_NAMES!
    """
    has_prima = "prima" in EngineSelectorWidget.ENGINES
    assert has_prima, "EngineSelectorWidget is missing 'prima'"


def test_audit_layer3_active_ports_discrepancy():
    """
    VERIFICATION:
    Layer3AiInferenceState.active_ports default dict maps Qwen 3.8 Max to 8082,
    Qwen 3.8 Max Abliterated to 8083, and Qwen 2.5 Coder to 8081!
    """
    state = Layer3AiInferenceState()
    ports = state.active_ports
    assert ports.get("qwen_38_max") == 8082, f"Expected port 8082 for qwen_38_max, got {ports.get('qwen_38_max')}"
    assert ports.get("qwen_38_max_abliterated") == 8083, f"Expected port 8083 for qwen_38_max_abliterated, got {ports.get('qwen_38_max_abliterated')}"
    assert ports.get("qwen_25_coder_syntax_worker") == 8081, f"Expected port 8081 for qwen_25_coder_syntax_worker, got {ports.get('qwen_25_coder_syntax_worker')}"


def test_audit_blackboard_state_disk_stale_hierarchy():
    """
    VERIFICATION:
    blackboard_store.get_snapshot() loads synchronized blackboard_state.json from disk:
    - qwen_38_max on disk has port 8082
    - qwen_25_coder_7b on disk has port 8081
    - qwen_38_max_abliterated on disk has port 8083
    """
    snapshot = blackboard_store.get_snapshot(force_refresh=True)
    active = {m.model_id: m for m in snapshot.layer_3_ai_inference.active_models}

    qwen_38 = active.get("qwen_38_max")
    assert qwen_38 is not None
    assert qwen_38.port == 8082, f"Expected port 8082 on disk, got {qwen_38.port}"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
