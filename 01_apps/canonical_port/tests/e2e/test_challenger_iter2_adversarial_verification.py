"""
Challenger Iteration 2 Adversarial Stress and Verification Harness
Subsystem: 01_apps/canonical_port/tests/e2e/test_challenger_iter2_adversarial_verification.py

Empirical stress testing:
1. BluetoothTerminalScreen: verify all numeric keys '0'-'9' navigate to their target screens.
2. HardwareView and AllTabsGridScreen: adversarial unprobed/offline telemetry where all numeric fields are None.
3. SpatialGrapplingScreen: lifecycle mounting/unmounting and rapid update_display() calls without crashing.
4. Blackboard state & nomad healer port mappings for Qwen 3.8 Max.
"""

import sys
import os
import json
import pytest
import asyncio
from typing import Dict, Any

TUI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tui"))
PORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, TUI_DIR)
sys.path.insert(0, PORT_DIR)

from canonical_tui import CanonicalPortApp
from models.blackboard_models import BlackboardTelemetryState, HardwareNodeState
from views.hardware_view import HardwareView
from screens.all_tabs_screen import AllTabsGridScreen
from screens.spatial_grappling_screen import SpatialGrapplingScreen
from services.blackboard_store import blackboard_store


EXPECTED_NAV_MAP = {
    "0": "AllTabsGridScreen",
    "1": "AgiCodingTerminalView",
    "2": "NetworkScreen",
    "3": "HardwareScreen",
    "4": "BiometricsScreen",
    "5": "AiInferenceScreen",
    "6": "TrainingScreen",
    "7": "GovernanceScreen",
    "8": "ToolingScreen",
    "9": "OptimizationScreen",
}


@pytest.mark.asyncio
async def test_bluetooth_terminal_all_numeric_keys_navigation_escape():
    """
    Empirically test that every numeric key '0' through '9' navigates away from
    BluetoothTerminalScreen to the designated screen, proving macro deck does not hijack.
    """
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 45)) as pilot:
        for key, expected_screen in EXPECTED_NAV_MAP.items():
            # First navigate into BluetoothTerminalScreen
            await pilot.press("B")
            await pilot.pause(0.05)
            assert app.screen.__class__.__name__ == "BluetoothTerminalScreen", (
                f"Failed to navigate to BluetoothTerminalScreen before pressing '{key}'"
            )

            # Now press the numeric key
            await pilot.press(key)
            await pilot.pause(0.05)
            actual_screen = app.screen.__class__.__name__
            assert actual_screen == expected_screen, (
                f"Pressing '{key}' from BluetoothTerminalScreen expected '{expected_screen}', got '{actual_screen}'"
            )


@pytest.mark.asyncio
async def test_all_tabs_grid_screen_mount_with_all_none_telemetry():
    """
    Adversarial test: Inject completely unprobed / None telemetry across all nodes
    and verify AllTabsGridScreen mounts and HardwareView renders cleanly without TypeError.
    """
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 45)) as pilot:
        # Construct adversarial state where all numeric fields are None
        snap = BlackboardTelemetryState.create_canonical_default()
        for node in snap.layer_1_hardware.nodes:
            node.thermal_c = None
            node.thermal_status = "UNKNOWN"
            node.cpu_usage_pct = None
            node.load_1m = None
            node.ram_used_gb = None
            node.ram_total_gb = None
            node.ram_usage_pct = None
            node.vram_used_gb = None
            node.vram_cap_gb = None
            node.dynamic_cap_pct = None
            node.battery_pct = None
            node.qi_power_watts = 0.0

        # Update store with adversarial state
        blackboard_store.update_layer("layer_1_hardware", snap.layer_1_hardware)

        # Mount AllTabsGridScreen
        app.switch_screen("all_tabs")
        await pilot.pause(0.1)
        assert app.screen.__class__.__name__ == "AllTabsGridScreen"

        # Also directly verify HardwareView render_nodes on adversarial state
        hw_view = HardwareView()
        # render_nodes updates internal static widget, should not raise TypeError
        hw_view.render_nodes(snap)


@pytest.mark.asyncio
async def test_spatial_grappling_screen_resilience_to_lifecycle_hammering():
    """
    Rapidly mount and unmount SpatialGrapplingScreen and invoke update_display()
    concurrently to verify no unhandled NoMatches exceptions occur.
    """
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 45)) as pilot:
        for _ in range(3):
            app.switch_screen("spatial_grappling")
            await pilot.pause(0.02)
            assert app.screen.__class__.__name__ == "SpatialGrapplingScreen"
            # Explicitly call update_display
            app.screen.update_display()
            await pilot.pause(0.02)

            # Switch away immediately
            app.switch_screen("agi_terminal")
            await pilot.pause(0.02)


def test_blackboard_state_disk_and_healer_port_8082_mapping():
    """
    Empirical check: Verify blackboard_state.json and nomad_courier_self_healer.py
    strictly map Port 8082 to Qwen 3.8 Max.
    """
    # 1. Check blackboard_state.json
    json_path = os.path.join(PORT_DIR, "blackboard_state.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    active_models = {m["model_id"]: m for m in data.get("layer_3_ai_inference", {}).get("active_models", [])}
    assert "qwen_38_max" in active_models, "qwen_38_max missing from blackboard_state.json active_models"
    qwen = active_models["qwen_38_max"]
    assert qwen["port"] == 8082, f"Expected port 8082 in blackboard_state.json, got {qwen['port']}"
    assert "Sovereign Master Local Orchestrator" in qwen["role"]

    active_ports = data.get("layer_3_ai_inference", {}).get("active_ports", {})
    assert active_ports.get("qwen_38_max") == 8082, f"active_ports['qwen_38_max'] = {active_ports.get('qwen_38_max')}"

    # 2. Check nomad_courier_self_healer.py
    healer_path = os.path.abspath(os.path.join(PORT_DIR, "../../06_scripts_and_tooling/network/nomad_courier_self_healer.py"))
    with open(healer_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "8082: {" in content
    assert '"name": "qwen_38_max"' in content
    assert '"qwen_38_max_8082": 8082' in content
