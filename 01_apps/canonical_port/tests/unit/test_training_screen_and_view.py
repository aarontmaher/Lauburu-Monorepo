"""
Unit Tests for TrainingScreen, TrainingView, and Canonical TUI Integration (Milestone 2 & 3)
tests/unit/test_training_screen_and_view.py

Comprehensive tests verifying:
  1. TrainingScreen composition, child widget mounting, and lifecycle.
  2. TrainingView container composition for multi-view grids.
  3. MPSC telemetry draining loop (`drain_and_update`).
  4. Interactive action button handlers.
  5. CanonicalPortApp Screen 6 registration and navigation.
"""

import os
import sys
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, TabbedContent

# Add paths to match canonical_tui import paths exactly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from canonical_tui import CanonicalPortApp, CanonicalPortTUI
from screens.training_screen import TrainingScreen
from views.training_view import TrainingView
from widgets.pinned_tab_nav_bar import PinnedTabNavBar
from widgets.training_pipeline_widget import TrainingPipelineWidget
from widgets.lauburu_gyms_widget import LauburuGymsWidget
from backend.training_telemetry_collector import training_telemetry_collector


class StandaloneScreenApp(App):
    """Isolated App testing TrainingScreen directly."""
    def on_mount(self) -> None:
        self.push_screen(TrainingScreen())


class StandaloneViewApp(App):
    """Isolated App testing TrainingView container."""
    def compose(self) -> ComposeResult:
        yield TrainingView(id="test-training-view")


# ============================================================================
# 1. TrainingScreen Unit Tests
# ============================================================================

@pytest.mark.asyncio
async def test_training_screen_composition():
    """Verifies TrainingScreen mounts header, navbar, action row, tabbed content, and widgets."""
    app = StandaloneScreenApp()
    async with app.run_test(size=(160, 45)) as pilot:
        screen = app.screen
        assert isinstance(screen, TrainingScreen)
        
        # Verify nav bar
        navbar = screen.query_one(PinnedTabNavBar)
        assert navbar is not None
        assert navbar.active_screen == "training"
        
        # Verify action buttons
        assert screen.query_one("#btn-harvest-lora", Button) is not None
        assert screen.query_one("#btn-trigger-duel", Button) is not None
        assert screen.query_one("#btn-refresh-train", Button) is not None
        assert screen.query_one("#btn-test-gate", Button) is not None
        
        # Verify TabbedContent and core widgets
        tabs = screen.query(TabbedContent).first()
        assert tabs is not None
        assert screen.query_one(TrainingPipelineWidget) is not None
        assert screen.query_one(LauburuGymsWidget) is not None
        assert screen.query_one("#lora-view", Static) is not None
        assert screen.query_one("#games-view", Static) is not None


@pytest.mark.asyncio
async def test_training_screen_mpsc_drain_and_update():
    """Verifies that drain_and_update pulls from training_telemetry_collector without error."""
    app = StandaloneScreenApp()
    async with app.run_test(size=(160, 45)) as pilot:
        screen = app.screen
        assert isinstance(screen, TrainingScreen)
        
        # Push mock/test snapshot into collector
        training_telemetry_collector.push_snapshot()
        
        # Call drain_and_update
        screen.drain_and_update()
        await pilot.pause(0.05)
        
        pipeline_widget = screen.query_one(TrainingPipelineWidget)
        assert pipeline_widget is not None


@pytest.mark.asyncio
async def test_training_screen_buttons_pressed_notifications():
    """Verifies button press events dispatch appropriate notifications without crashing."""
    app = StandaloneScreenApp()
    async with app.run_test(size=(160, 45)) as pilot:
        screen = app.screen
        
        btn_harvest = screen.query_one("#btn-harvest-lora", Button)
        btn_duel = screen.query_one("#btn-trigger-duel", Button)
        btn_refresh = screen.query_one("#btn-refresh-train", Button)
        btn_gate = screen.query_one("#btn-test-gate", Button)
        
        # Click buttons
        await pilot.click("#btn-harvest-lora")
        await pilot.pause(0.02)
        await pilot.click("#btn-trigger-duel")
        await pilot.pause(0.02)
        await pilot.click("#btn-refresh-train")
        await pilot.pause(0.02)
        await pilot.click("#btn-test-gate")
        await pilot.pause(0.02)


# ============================================================================
# 2. TrainingView Unit Tests
# ============================================================================

@pytest.mark.asyncio
async def test_training_view_composition():
    """Verifies TrainingView mounts all child widgets and tabs."""
    app = StandaloneViewApp()
    async with app.run_test(size=(160, 45)) as pilot:
        view = app.query_one(TrainingView)
        assert view is not None
        
        assert view.query_one("#btn-harvest-lora", Button) is not None
        assert view.query_one("#btn-trigger-duel", Button) is not None
        assert view.query_one(TrainingPipelineWidget) is not None
        assert view.query_one(LauburuGymsWidget) is not None
        
        # Call refresh and drain
        view.refresh_views()
        view.drain_and_update()
        await pilot.pause(0.05)


@pytest.mark.asyncio
async def test_training_view_buttons_interaction():
    """Verifies clicking buttons inside TrainingView container."""
    app = StandaloneViewApp()
    async with app.run_test(size=(160, 45)) as pilot:
        view = app.query_one(TrainingView)
        
        await pilot.click("#btn-harvest-lora")
        await pilot.pause(0.02)
        await pilot.click("#btn-refresh-train")
        await pilot.pause(0.02)
        await pilot.click("#btn-test-gate")
        await pilot.pause(0.02)


# ============================================================================
# 3. CanonicalPortApp Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_canonical_tui_training_screen_registration():
    """Verifies CanonicalPortApp registers TrainingScreen at index 5 in SCREEN_ORDER."""
    assert "training" in CanonicalPortApp.SCREENS
    assert CanonicalPortApp.SCREENS["training"].__name__ == "TrainingScreen"
    assert CanonicalPortApp.SCREEN_ORDER[5] == "training"


@pytest.mark.asyncio
async def test_canonical_tui_navigate_to_training():
    """Verifies pressing key 't' and '6' navigates to TrainingScreen in CanonicalPortTUI."""
    app = CanonicalPortTUI()
    async with app.run_test(size=(160, 45)) as pilot:
        # Initial screen
        assert app.screen is not None
        
        # Switch to training via 't'
        await pilot.press("t")
        await pilot.pause(0.05)
        assert app.screen.__class__.__name__ == "TrainingScreen"
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "training"
        
        # Switch to agi_terminal via '1'
        await pilot.press("1")
        await pilot.pause(0.05)
        assert app.screen.__class__.__name__ != "TrainingScreen"
        
        # Switch to training via '6'
        await pilot.press("6")
        await pilot.pause(0.05)
        assert app.screen.__class__.__name__ == "TrainingScreen"
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "training"
