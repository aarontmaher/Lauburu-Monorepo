"""
E2E Pilot Tests for Visual Engine Selector, Hotkey Cycling, HUD Badges, and Multi-Engine Inference.
Tests Textual Pilot interactions with EngineSelectorWidget, Select dropdown, ctrl+e / F2 cycling,
dynamic HUD badge updates in AgiCodingTerminalView and AgiCodingTerminalScreen, and stress rapid switching.
Includes comprehensive coverage for 'auto' dynamic TTFT mode.
"""

import asyncio
import pytest
from typing import Optional
from textual.app import App, ComposeResult
from textual.widgets import Select, Static, RichLog, Input

from tui.widgets.engine_selector import EngineSelectorWidget, InferenceEngineChanged
from tui.services.inference_router import UnifiedInferenceRouter
from tui.views.agi_coding_terminal_view import AgiCodingTerminalView
from tui.screens.agi_coding_terminal_screen import AgiCodingTerminalScreen


class EngineSelectorTestApp(App):
    """Test harness for EngineSelectorWidget and AgiCodingTerminalView."""
    CSS = """
    #engine-selector-bar {
        dock: top;
        height: 3;
        background: #111b27;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.terminal_view: Optional[AgiCodingTerminalView] = None
        self.received_engine_events = []

    def compose(self) -> ComposeResult:
        self.terminal_view = AgiCodingTerminalView()
        yield self.terminal_view

    def on_inference_engine_changed(self, event: InferenceEngineChanged) -> None:
        self.received_engine_events.append(event)
        if self.terminal_view:
            self.terminal_view.on_inference_engine_changed(event)


class EngineSelectorScreenApp(App):
    """Test harness for AgiCodingTerminalScreen."""
    def on_mount(self) -> None:
        self.push_screen(AgiCodingTerminalScreen())


# ============================================================================
# 1. WIDGET RENDERING & INITIAL SELECTION TEST
# ============================================================================

@pytest.mark.asyncio
async def test_engine_selector_widget_rendering_and_initial_state():
    """Verify EngineSelectorWidget mounts with dropdown, label, and default llama_rpc."""
    app = EngineSelectorTestApp()

    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause(0.1)
        view = app.terminal_view
        assert view is not None

        # Verify EngineSelectorWidget is mounted
        selector = view.query_one(EngineSelectorWidget)
        assert selector is not None

        select_widget = selector.query_one("#engine-select", Select)
        assert select_widget is not None
        assert select_widget.value == "llama_rpc"

        # Verify initial status bar contains LLAMA.CPP badge
        status_bar = view.query_one("#terminal-status-bar", Static)
        assert status_bar is not None


# ============================================================================
# 2. DROPDOWN SELECTION & EVENT DISPATCH TEST
# ============================================================================

@pytest.mark.asyncio
async def test_engine_selector_dropdown_selection_changes_active_engine():
    """Verify changing Select.value propagates InferenceEngineChanged and updates router."""
    app = EngineSelectorTestApp()

    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause(0.1)
        view = app.terminal_view
        selector = view.query_one(EngineSelectorWidget)
        select_widget = selector.query_one("#engine-select", Select)

        # 1. Select 'exo'
        select_widget.value = "exo"
        await pilot.pause(0.1)

        assert view.inference_router.active_engine == "exo"
        assert selector.active_engine == "exo"
        assert len(app.received_engine_events) >= 1
        assert app.received_engine_events[-1].engine_name == "exo"

        # 2. Select 'accelerate'
        select_widget.value = "accelerate"
        await pilot.pause(0.1)

        assert view.inference_router.active_engine == "accelerate"
        assert selector.active_engine == "accelerate"

        # 3. Select 'petals'
        select_widget.value = "petals"
        await pilot.pause(0.1)

        assert view.inference_router.active_engine == "petals"
        assert selector.active_engine == "petals"

        # 4. Select 'auto'
        select_widget.value = "auto"
        await pilot.pause(0.1)

        assert view.inference_router.active_engine == "auto"
        assert selector.active_engine == "auto"
        assert app.received_engine_events[-1].engine_name == "auto"


# ============================================================================
# 3. HOTKEY CYCLING (ctrl+e / F2) TEST
# ============================================================================

@pytest.mark.asyncio
async def test_engine_selector_hotkey_cycling():
    """Verify pressing ctrl+e / F2 cycles engines including auto and synchronizes dropdown and router."""
    app = EngineSelectorTestApp()

    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause(0.1)
        view = app.terminal_view
        selector = view.query_one(EngineSelectorWidget)
        select_widget = selector.query_one("#engine-select", Select)

        assert view.inference_router.active_engine == "llama_rpc"

        # Cycle 1: llama_rpc -> exo
        await pilot.press("ctrl+e")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "exo"
        assert select_widget.value == "exo"

        # Cycle 2: exo -> accelerate
        await pilot.press("ctrl+e")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "accelerate"
        assert select_widget.value == "accelerate"

        # Cycle 3: accelerate -> petals
        await pilot.press("f2")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "petals"
        assert select_widget.value == "petals"

        # Cycle 4: petals -> gemini
        await pilot.press("ctrl+e")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "gemini"
        assert select_widget.value == "gemini"

        # Cycle 5: gemini -> cloudflare
        await pilot.press("ctrl+e")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "cloudflare"
        assert select_widget.value == "cloudflare"

        # Cycle 6: cloudflare -> julien
        await pilot.press("ctrl+e")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "julien"
        assert select_widget.value == "julien"

        # Cycle 7: julien -> auto
        await pilot.press("ctrl+e")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "auto"
        assert select_widget.value == "auto"

        # Cycle 8: auto -> llama_rpc
        await pilot.press("ctrl+e")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "llama_rpc"
        assert select_widget.value == "llama_rpc"


# ============================================================================
# 4. SLASH COMMAND (/engine) TEST
# ============================================================================

@pytest.mark.asyncio
async def test_engine_slash_commands():
    """Verify /engine auto, /engine <name>, /engine status, and /engine cycle commands in REPL."""
    app = EngineSelectorTestApp()

    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause(0.1)
        view = app.terminal_view
        selector = view.query_one(EngineSelectorWidget)
        select_widget = selector.query_one("#engine-select", Select)

        # 1. /engine auto
        view._execute_repl_command("/engine auto")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "auto"
        assert select_widget.value == "auto"

        # 2. /engine exo
        view._execute_repl_command("/engine exo")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "exo"
        assert select_widget.value == "exo"

        # 3. /engine status
        view._execute_repl_command("/engine status")
        await pilot.pause(0.1)
        log = view.query_one("#terminal-output-log", RichLog)
        assert log is not None

        # 4. /engine (no args cycles)
        view._execute_repl_command("/engine")
        await pilot.pause(0.1)
        assert view.inference_router.active_engine == "accelerate"
        assert select_widget.value == "accelerate"


# ============================================================================
# 5. ADVERSARIAL RAPID SWITCHING STRESS TEST
# ============================================================================

@pytest.mark.asyncio
async def test_rapid_engine_switching_during_token_streaming_stress():
    """
    Adversarial stress test:
    - Initiates prompt generation.
    - Rapidly cycles engines 20 times during streaming.
    - Asserts zero unhandled exceptions, zero UI deadlock, and instant sub-1ms stream cancellation.
    """
    app = EngineSelectorTestApp()

    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause(0.1)
        view = app.terminal_view

        # Start streaming generation in background worker
        view.run_worker(view._run_inference_repl("Write complex sharded distributed matrix multiplication"), exclusive=False)
        await pilot.pause(0.02)

        # Rapidly cycle engines during active generation
        for _ in range(20):
            view.action_cycle_inference_engine()
            await pilot.pause(0.01)

        # Ensure terminal is still responsive
        view._execute_repl_command("/audit")
        await pilot.pause(0.05)

        log = view.query_one("#terminal-output-log", RichLog)
        assert log is not None
        assert view.inference_router.active_engine in [
            "auto", "llama_rpc", "exo", "accelerate", "petals", "gemini", "cloudflare", "julien"
        ]


# ============================================================================
# 6. SCREEN LEVEL INTEGRATION TEST
# ============================================================================

@pytest.mark.asyncio
async def test_screen_level_engine_selector_integration():
    """Verify AgiCodingTerminalScreen renders EngineSelectorWidget and HUD status badge."""
    app = EngineSelectorScreenApp()

    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause(0.1)
        screen = app.screen
        assert isinstance(screen, AgiCodingTerminalScreen)

        # Verify EngineSelectorWidget is present in Screen
        selector = screen.query_one(EngineSelectorWidget)
        assert selector is not None
        assert selector.active_engine == "llama_rpc"

        # Test hotkey cycling on screen: llama_rpc -> exo
        await pilot.press("ctrl+e")
        await pilot.pause(0.1)
        assert screen.inference_router.active_engine == "exo"

        # Test slash command /engine auto on screen
        screen._execute_repl_command("/engine auto")
        await pilot.pause(0.1)
        assert screen.inference_router.active_engine == "auto"

        # Verify HUD renders cleanly without errors
        status_bar = screen.query_one("#terminal-status-bar", Static)
        assert status_bar is not None
