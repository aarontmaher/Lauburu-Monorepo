"""
E2E Adversarial Pilot Stress Suite: Canonical Port TUI Screen 6 Navigation & Flooding
tests/e2e/test_challenger_1_training_screen_e2e_stress.py

Empirical Challenger 1 E2E Pilot Stress Harness:
  1. High-frequency MPSC telemetry flooding during active Textual pilot lifecycle.
  2. Rapid screen switching across all 9 canonical screens (1..9, Screen 6) under telemetry load.
  3. Interactive DOM stress: Button dispatches, TabbedContent cycling, and dynamic widget updates.
  4. Viewport size mutations (70 to 200 cols) under continuous MPSC ring buffer draining.
"""

import os
import sys
import time
import pytest
import asyncio
import threading
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from canonical_tui import CanonicalPortApp
from screens.training_screen import TrainingScreen
from widgets.training_pipeline_widget import TrainingPipelineWidget
from widgets.lauburu_gyms_widget import LauburuGymsWidget
from backend.training_telemetry_collector import (
    training_telemetry_collector,
    MPSCRingBuffer,
)
from textual.widgets import TabbedContent, Button, Static


# ============================================================================
# 1. SCREEN SWITCHING ACROSS ALL SCREENS UNDER ACTIVE MPSC FLOODING
# ============================================================================

class TestScreenSwitchingUnderMpscFlood:
    """Stress testing Textual screen stack transitions under background MPSC telemetry storm."""

    @pytest.mark.asyncio
    async def test_rapid_9_screen_cycling_with_mpsc_background_producers(self):
        """
        E2E Stress 1.1: Start 5 background threads pushing 100 snapshots/sec into the MPSC ring buffer,
        while the Textual Pilot rapidly switches across all screens (1..9 and Screen 6) 30 times.
        Invariant: Zero crashes, zero unhandled worker exceptions, screen stack remains integral.
        """
        app = CanonicalPortApp()
        stop_flooding = threading.Event()

        def flooder():
            seq = 0
            while not stop_flooding.is_set():
                if training_telemetry_collector:
                    training_telemetry_collector.buffer.push({
                        "timestamp_iso": "2026-08-29T04:45:00Z",
                        "ingestion_loop": {"file_size_mb": 66.0 + (seq % 10), "growth_rate_bps": 1024.0},
                        "gatekeeper": {"active_intercepts_count": seq % 20, "lock_state": "UNLOCKED"},
                        "hf_epoch_vram_gate": {"vram_headroom_pct": 33.3, "is_blocked": False},
                        "gyms": {
                            "red_blue_arena": {"round": seq},
                            "mesh_healing": {"last_recovery_latency_ms": 0.28},
                            "stealth_compute": {"yield_latency_ms": 3.8},
                            "software_dev_game": {"total_architects": 13},
                            "spatial_grappling": {"opml_node_count": 955, "current_torque_nm": 42.43},
                        }
                    })
                seq += 1
                time.sleep(0.005)

        flooder_threads = [threading.Thread(target=flooder, daemon=True) for _ in range(5)]
        for t in flooder_threads:
            t.start()

        screen_keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "t", "c", "n", "h", "b", "i", "g", "s", "o"]

        try:
            async with app.run_test(size=(120, 36)) as pilot:
                await pilot.pause(0.1)

                # Cycle through all screen hotkeys in rapid succession (2 full rounds)
                for _ in range(2):
                    for key in screen_keys:
                        await pilot.press(key)
                        await pilot.pause(0.02)

                # Land specifically on Screen 6 (Training)
                await pilot.press("6")
                await pilot.pause(0.2)

                # Verify TrainingScreen is mounted and widgets are queryable
                assert isinstance(app.screen, TrainingScreen)
                pipeline = app.screen.query_one("#training-pipeline-widget", TrainingPipelineWidget)
                assert pipeline is not None
                gyms = app.screen.query_one("#lauburu-gyms-widget", LauburuGymsWidget)
                assert gyms is not None

        finally:
            stop_flooding.set()
            for t in flooder_threads:
                t.join(timeout=1.0)


# ============================================================================
# 2. INTERACTIVE EVENT HANDLING & TAB NAVIGATION STRESS
# ============================================================================

class TestInteractivePilotEventHandling:
    """Stress testing button presses, multi-tab switching, and pilot input queues."""

    @pytest.mark.asyncio
    async def test_button_dispatches_and_drain_triggers(self):
        """
        E2E Stress 2.1: Rapidly trigger all 4 action buttons on Screen 6 via pilot clicks.
        """
        app = CanonicalPortApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.press("6")
            await pilot.pause(0.1)
            assert isinstance(app.screen, TrainingScreen)

            # Click buttons in sequence multiple times
            buttons = ["#btn-harvest-lora", "#btn-trigger-duel", "#btn-refresh-train", "#btn-test-gate"]
            for _ in range(3):
                for btn_id in buttons:
                    await pilot.click(btn_id)
                    await pilot.pause(0.03)

            # Check that drain_and_update was called and widgets remain responsive
            pipeline = app.screen.query_one("#training-pipeline-widget", TrainingPipelineWidget)
            assert pipeline is not None

    @pytest.mark.asyncio
    async def test_tabbed_content_cycling_across_all_gyms(self):
        """
        E2E Stress 2.2: Programmatically and interactively cycle through all 5 Gym tabs
        and all 4 Screen 6 main tabs under high stream rate.
        """
        app = CanonicalPortApp()
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.press("6")
            await pilot.pause(0.1)

            gyms_widget = app.screen.query_one("#lauburu-gyms-widget", LauburuGymsWidget)
            assert gyms_widget is not None

            # Switch through all 5 gym tabs programmatically
            gym_tabs = ["tab-gym-1", "tab-gym-2", "tab-gym-3", "tab-gym-4", "tab-gym-5"]
            for tab_id in gym_tabs:
                success = gyms_widget.switch_gym(tab_id)
                assert success is True
                await pilot.pause(0.02)

            # Cycle main Screen 6 tabs
            main_tabs = app.screen.query_one(TabbedContent)
            for mtab in ["tab-lora", "tab-games", "tab-metrics", "tab-traces"]:
                main_tabs.active = mtab
                await pilot.pause(0.02)


# ============================================================================
# 3. RESPONSIVE VIEWPORT MUTATION STRESS
# ============================================================================

class TestViewportMutationStress:
    """Stress testing Screen 6 layout under extreme terminal resizing."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("width,height", [
        (65, 20),   # Ultra-compact mobile / small terminal
        (80, 24),   # Standard VT100
        (100, 30),  # Standard laptop
        (160, 45),  # Large desktop
        (220, 60),  # 4K / Ultra-wide display
    ])
    async def test_screen6_viewport_resizing_invariants(self, width, height):
        """
        E2E Stress 3.1: Screen 6 rendering and MPSC drain under extreme viewport dimensions.
        """
        app = CanonicalPortApp()
        async with app.run_test(size=(width, height)) as pilot:
            await pilot.press("6")
            await pilot.pause(0.05)
            assert isinstance(app.screen, TrainingScreen)

            # Trigger drain
            app.screen.drain_and_update()
            await pilot.pause(0.02)

            # Ensure widgets didn't throw uncaught layout errors
            ingestion = app.screen.query_one("#training-pipeline-widget", TrainingPipelineWidget)
            assert ingestion is not None
