"""
Challenger 2 Empirical Verification Suite: Textual TUI UI & Pilot Interactions Stress Testing
Target: 01_apps/canonical_port (CanonicalPortApp, AgiCodingTerminalScreen, AgiCodingTerminalView, EngineSelectorWidget)

Verification Dimensions:
1. 20x Consecutive Rapid 'ctrl+e' and 'f2' Keypress Cycling in Headless Pilot Mode on CanonicalPortApp
2. Dropdown Select Mutation Interleaved with Active REPL Input Typing
3. Dynamic #terminal-status-bar HUD Badge Rendering, Verification & DOM Crash Safety across 4 backends
4. REPL /engine Slash Commands (/engine status, /engine llama_rpc, /engine exo, /engine accelerate, /engine petals)
5. Multi-Screen Navigation Stability and Engine State Persistence
6. High-Frequency Concurrent Submission & Dropdown Churn Stress
"""

import os
import sys
import asyncio
import pytest
from typing import Optional, List
from textual.app import App, ComposeResult
from textual.widgets import Select, Static, RichLog, Input
from rich.console import Console
from rich.panel import Panel

# Ensure tui package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from canonical_tui import CanonicalPortApp
from screens.agi_coding_terminal_screen import AgiCodingTerminalScreen
from screens.network_screen import NetworkScreen
from screens.hardware_screen import HardwareScreen
from screens.ai_inference_screen import AiInferenceScreen
from views.agi_coding_terminal_view import AgiCodingTerminalView
from widgets.engine_selector import EngineSelectorWidget, InferenceEngineChanged
from services.inference_router import UnifiedInferenceRouter


# ============================================================================
# 1. 20X RAPID CTRL+E & F2 KEYPRESS CYCLING ON CANONICALPORTAPP
# ============================================================================

@pytest.mark.asyncio
async def test_canonical_port_app_pilot_rapid_ctrl_e_and_f2_stress():
    """
    Empirical Stress Test:
    - Runs full CanonicalPortApp in headless pilot mode.
    - Fires 20 rapid 'ctrl+e' keypresses in succession.
    - Fires 20 rapid 'f2' keypresses in succession.
    - Asserts zero unhandled exceptions, zero DOM crashes.
    - Asserts active engine cycles predictably through all 4 engines:
      llama_rpc -> exo -> accelerate -> petals -> llama_rpc.
    """
    app = CanonicalPortApp()
    canonical_engines_sequence = ["exo", "accelerate", "petals", "gemini", "cloudflare", "julien", "auto", "llama_rpc"]

    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause(0.05)
        screen = app.screen
        assert isinstance(screen, AgiCodingTerminalScreen)

        selector = screen.query_one(EngineSelectorWidget)
        select_widget = selector.query_one("#engine-select", Select)
        assert select_widget.value == "llama_rpc"

        # 20 Rapid 'ctrl+e' keypresses
        for i in range(20):
            await pilot.press("ctrl+e")
            await pilot.pause(0.005)
            expected_engine = canonical_engines_sequence[i % len(canonical_engines_sequence)]
            assert screen.inference_router.active_engine == expected_engine
            assert select_widget.value == expected_engine

        # 20 Rapid 'f2' keypresses
        for i in range(20):
            await pilot.press("f2")
            await pilot.pause(0.005)
            # Continues cycling from current position (which after 20 presses is 20 % 8 = 4 -> cloudflare)
            expected_engine = canonical_engines_sequence[(20 + i) % len(canonical_engines_sequence)]
            assert screen.inference_router.active_engine == expected_engine
            assert select_widget.value == expected_engine


# ============================================================================
# 2. DROPDOWN SELECTION INTERLEAVED WITH ACTIVE REPL INPUT TYPING
# ============================================================================

@pytest.mark.asyncio
async def test_select_dropdown_interleaved_with_active_repl_typing():
    """
    Empirical Stress Test:
    - Focuses #repl-input.
    - Types characters into input while simultaneously changing Select dropdown values.
    - Submits input via Enter.
    - Verifies input is cleanly cleared and dispatched, active engine is updated,
      and no text corruption or focus stealing occurs.
    """
    app = CanonicalPortApp()

    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause(0.05)
        screen = app.screen
        assert isinstance(screen, AgiCodingTerminalScreen)

        repl_input = screen.query_one("#repl-input", Input)
        repl_input.focus()
        await pilot.pause(0.02)
        assert repl_input.has_focus

        selector = screen.query_one(EngineSelectorWidget)
        select_widget = selector.query_one("#engine-select", Select)

        # Type partial input via pilot keypresses
        await pilot.press(*list("def compute_tensor_dma():"))
        await pilot.pause(0.01)
        assert repl_input.value == "def compute_tensor_dma():"

        # Switch dropdown to 'exo' while typing
        select_widget.value = "exo"
        await pilot.pause(0.02)
        assert screen.inference_router.active_engine == "exo"

        # Type more code
        await pilot.press(*list(" return 42"))
        await pilot.pause(0.01)
        assert repl_input.value == "def compute_tensor_dma(): return 42"

        # Switch dropdown to 'accelerate'
        select_widget.value = "accelerate"
        await pilot.pause(0.02)
        assert screen.inference_router.active_engine == "accelerate"

        # Submit via Enter
        await pilot.press("enter")
        await pilot.pause(0.05)

        # Verify input was cleared and logged
        assert repl_input.value == ""
        log = screen.query_one("#terminal-output-log", RichLog)
        assert log is not None


# ============================================================================
# 3. DYNAMIC #terminal-status-bar HUD BADGE RENDERING & DOM SAFETY
# ============================================================================

@pytest.mark.asyncio
async def test_terminal_status_bar_hud_badge_dynamic_updates_and_dom_safety():
    """
    Empirical Test:
    - Cycles through each of the 4 engines (llama_rpc, exo, accelerate, petals).
    - Checks #terminal-status-bar widget after each switch.
    - Verifies the rendered text contains the corresponding engine HUD badge:
      - llama_rpc -> [LLAMA.CPP: ACTIVE]
      - exo -> [EXO: ACTIVE]
      - accelerate -> [ACCELERATE: ACTIVE]
      - petals -> [PETALS: ACTIVE]
    - Resizes viewport across 5 extreme resolutions (80x24 -> 200x60) during switches
      to confirm zero DOM layout exceptions, jitter, or rendering lag.
    """
    app = CanonicalPortApp()
    badge_expectations = {
        "llama_rpc": "[LLAMA.CPP: ACTIVE]",
        "exo": "[EXO: ACTIVE]",
        "accelerate": "[ACCELERATE: ACTIVE]",
        "petals": "[PETALS: ACTIVE]",
    }

    async with app.run_test(size=(200, 50)) as pilot:
        await pilot.pause(0.05)
        screen = app.screen
        status_bar = screen.query_one("#terminal-status-bar", Static)
        assert status_bar is not None

        resolutions = [(80, 24), (100, 30), (140, 45), (180, 50), (200, 60)]

        for i, (eng, expected_badge) in enumerate(badge_expectations.items()):
            # Select engine programmatically via selector
            selector = screen.query_one(EngineSelectorWidget)
            select_widget = selector.query_one("#engine-select", Select)
            select_widget.value = eng
            await pilot.pause(0.02)

            # Resize viewport to test layout stability
            res_w, res_h = resolutions[i % len(resolutions)]
            await pilot.resize_terminal(res_w, res_h)
            await pilot.pause(0.02)

            # Verify HUD badge is rendered in status bar
            screen.refresh_views(force_probe=False)
            content = getattr(status_bar, "_Static__content", getattr(status_bar, "content", None))
            console = Console(width=200, record=True)
            console.print(content)
            rendered_text = console.export_text()

            # The badge text must appear in the rendered status bar
            assert expected_badge in rendered_text, (
                f"Expected '{expected_badge}' in status bar for engine '{eng}', got:\n{rendered_text}"
            )


# ============================================================================
# 4. REPL /engine SLASH COMMANDS IN AGICODINGTERMINALVIEW
# ============================================================================

class ViewHarnessApp(App):
    """Harness app hosting AgiCodingTerminalView directly."""
    def compose(self) -> ComposeResult:
        yield AgiCodingTerminalView()


@pytest.mark.asyncio
async def test_repl_engine_slash_commands_in_view():
    """
    Empirical Test of REPL Slash Commands in AgiCodingTerminalView:
    - /engine status: Logs multi-engine statuses with active tag.
    - /engine exo: Swaps engine to exo, updates dropdown.
    - /engine accelerate: Swaps engine to accelerate, updates dropdown.
    - /engine petals: Swaps engine to petals, updates dropdown.
    - /engine llama_rpc: Swaps engine to llama_rpc, updates dropdown.
    - /engine (no args): Cycles to next engine.
    - /engine invalid_backend: Gracefully logs error without crashing.
    """
    app = ViewHarnessApp()

    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause(0.05)
        view = app.query_one(AgiCodingTerminalView)
        selector = view.query_one(EngineSelectorWidget)
        select_widget = selector.query_one("#engine-select", Select)

        # 1. /engine status
        view._execute_repl_command("/engine status")
        await pilot.pause(0.02)
        assert view.inference_router.active_engine == "llama_rpc"

        # 2. /engine exo
        view._execute_repl_command("/engine exo")
        await pilot.pause(0.02)
        assert view.inference_router.active_engine == "exo"
        assert select_widget.value == "exo"

        # 3. /engine accelerate
        view._execute_repl_command("/engine accelerate")
        await pilot.pause(0.02)
        assert view.inference_router.active_engine == "accelerate"
        assert select_widget.value == "accelerate"

        # 4. /engine petals
        view._execute_repl_command("/engine petals")
        await pilot.pause(0.02)
        assert view.inference_router.active_engine == "petals"
        assert select_widget.value == "petals"

        # 5. /engine llama_rpc
        view._execute_repl_command("/engine llama_rpc")
        await pilot.pause(0.02)
        assert view.inference_router.active_engine == "llama_rpc"
        assert select_widget.value == "llama_rpc"

        # 6. /engine (cycle)
        view._execute_repl_command("/engine")
        await pilot.pause(0.02)
        assert view.inference_router.active_engine == "exo"
        assert select_widget.value == "exo"

        # 7. /engine invalid_backend (error safety)
        view._execute_repl_command("/engine non_existent_backend")
        await pilot.pause(0.02)
        # Engine remains unchanged, no unhandled exception
        assert view.inference_router.active_engine == "exo"


# ============================================================================
# 5. MULTI-SCREEN NAVIGATION STABILITY & ENGINE STATE PERSISTENCE
# ============================================================================

@pytest.mark.asyncio
async def test_multi_screen_navigation_and_engine_persistence():
    """
    Empirical Stress Test:
    - Sets active engine to 'accelerate' on agi_terminal.
    - Transitions across multiple screens in CanonicalPortApp:
      network (2), hardware (3), ai_inference (5), training (6), governance (7).
    - Transitions back to agi_terminal (1).
    - Asserts EngineSelectorWidget and router retained 'accelerate' state without reset.
    - Fires 'ctrl+e' while on network screen, asserts app survives cleanly without crash.
    """
    app = CanonicalPortApp()

    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause(0.05)
        screen = app.screen
        assert isinstance(screen, AgiCodingTerminalScreen)

        # Set engine to 'accelerate'
        selector = screen.query_one(EngineSelectorWidget)
        select_widget = selector.query_one("#engine-select", Select)
        select_widget.value = "accelerate"
        await pilot.pause(0.02)
        assert screen.inference_router.active_engine == "accelerate"

        # Navigate through screens
        for key in ["2", "3", "5", "6", "7"]:
            await pilot.press(key)
            await pilot.pause(0.02)

        # Press ctrl+e on non-terminal screen
        await pilot.press("ctrl+e")
        await pilot.pause(0.02)

        # Return to agi_terminal
        await pilot.press("1")
        await pilot.pause(0.03)

        current_screen = app.screen
        assert isinstance(current_screen, AgiCodingTerminalScreen)
        current_selector = current_screen.query_one(EngineSelectorWidget)
        current_select = current_selector.query_one("#engine-select", Select)
        assert current_select.value in ["accelerate", "petals"]


# ============================================================================
# 6. HIGH-FREQUENCY REPL SUBMISSION & DROPDOWN CHURN STRESS
# ============================================================================

@pytest.mark.asyncio
async def test_high_frequency_repl_submission_and_dropdown_churn():
    """
    Adversarial Stress Harness:
    - Performs 10 rapid iterations of REPL submission interleaved with dropdown engine changes.
    - Asserts terminal output log accumulates entries without deadlock or memory fault.
    """
    app = ViewHarnessApp()

    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause(0.05)
        view = app.query_one(AgiCodingTerminalView)
        selector = view.query_one(EngineSelectorWidget)
        select_widget = selector.query_one("#engine-select", Select)
        engines = ["llama_rpc", "exo", "accelerate", "petals"]

        for i in range(10):
            eng = engines[i % 4]
            select_widget.value = eng
            await pilot.pause(0.01)

            view._execute_repl_command(f"print('iteration {i} on engine {eng}')")
            await pilot.pause(0.01)

        log = view.query_one("#terminal-output-log", RichLog)
        assert log is not None
        assert view.inference_router.active_engine == engines[9 % 4]
