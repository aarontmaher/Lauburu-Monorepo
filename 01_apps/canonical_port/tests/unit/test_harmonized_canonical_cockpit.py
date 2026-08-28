"""
Unit Tests for Harmonized Canonical Cockpit Components (Milestone 4 Harmonization Blueprint)
Version: 4.0.0-HARMONIZED
Tests:
1. CanonicalHeaderBar (7-Node Mesh Pills, Pooled RAM/VRAM Meters, 8-Engine Selector, WAN badge)
2. CanonicalPromptBar (Slash command dispatcher, history buffer, inference routing)
3. ChatIdeView & ChatIdeScreen (Left 65% Chat/Code split, Right 35% Gauges & HUDs, Safe Runner)
4. HardwareNocView (3-Column Bento Box, Daemon Supervisor HUD, Biometrics DSP, Action buttons)
"""

import pytest
import asyncio
import os
import sys
from textual.app import App, ComposeResult
from textual.widgets import TextArea, RichLog, Select

# Ensure tui is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from widgets.canonical_header_bar import CanonicalHeaderBar, CanonicalEngineChanged
from widgets.canonical_prompt_bar import CanonicalPromptBar, PromptSubmitted
from views.chat_ide_view import ChatIdeView, MultiAgentChatStream, ActiveCodeBuffer, DebateConsensusGauge
from views.hardware_noc_view import HardwareNocView, NodeTelemetryColumn, BiometricsDspCenter, DaemonSupervisorHud, BottomEventDock
from screens.chat_ide_screen import ChatIdeScreen
from services.blackboard_store import blackboard_store
from services.inference_router import UnifiedInferenceRouter


# ============================================================================
# 1. TEST CANONICAL HEADER BAR
# ============================================================================

class HeaderBarTestApp(App):
    def compose(self) -> ComposeResult:
        yield CanonicalHeaderBar(active_engine="auto", id="test-header")


@pytest.mark.asyncio
async def test_canonical_header_bar_composition_and_metrics():
    app = HeaderBarTestApp()
    async with app.run_test() as pilot:
        header = app.query_one(CanonicalHeaderBar)
        assert header is not None
        assert header.active_engine == "auto"

        # Verify 8 supported engines in options
        assert len(header.ENGINES) == 8
        assert "auto" in header.ENGINES
        assert "llama_rpc" in header.ENGINES
        assert "gemini" in header.ENGINES
        assert "cloudflare" in header.ENGINES
        assert "julien" in header.ENGINES

        # Verify cycle engine
        next_eng = header.cycle_engine(1)
        assert next_eng == "llama_rpc"
        assert header.active_engine == "llama_rpc"

        # Verify set engine
        header.set_engine("cloudflare")
        assert header.active_engine == "cloudflare"

        # Verify update_view updates metrics
        header.update_view(ttft_ms=12.5, tok_per_sec=78.4, engine_status="ONLINE")
        assert header.ttft_ms == 12.5
        assert header.tok_per_sec == 78.4
        assert header.engine_status == "ONLINE"


# ============================================================================
# 2. TEST CANONICAL PROMPT BAR & SLASH COMMANDS
# ============================================================================

class PromptBarTestApp(App):
    def __init__(self):
        super().__init__()
        self.system_messages = []
        self.user_messages = []

    def compose(self) -> ComposeResult:
        yield CanonicalPromptBar(
            on_system_message=self._on_sys,
            on_user_message=self._on_user,
            id="test-prompt-bar"
        )

    def _on_sys(self, msg: str):
        self.system_messages.append(msg)

    def _on_user(self, msg: str):
        self.user_messages.append(msg)


@pytest.mark.asyncio
async def test_canonical_prompt_bar_slash_commands():
    app = PromptBarTestApp()
    async with app.run_test() as pilot:
        pbar = app.query_one(CanonicalPromptBar)
        assert pbar is not None

        # Test /help
        pbar.execute_slash_command("/help")
        assert any("Available Canonical Slash Commands" in m for m in app.system_messages)

        # Test /nodes
        app.system_messages.clear()
        pbar.execute_slash_command("/nodes")
        assert any("7-Layer Node Hardware Matrix Telemetry" in m for m in app.system_messages)
        assert any("RAM:" in m and "VRAM:" in m for m in app.system_messages)

        # Test /biometrics
        app.system_messages.clear()
        pbar.execute_slash_command("/biometrics")
        assert any("Live Biometrics DSP Telemetry" in m for m in app.system_messages)
        assert any("Zone 2 DFA-alpha1" in m for m in app.system_messages)

        # Test /audit
        app.system_messages.clear()
        pbar.execute_slash_command("/audit")
        assert any("SWARM TRUTH VERIFICATION AUDIT" in m for m in app.system_messages)
        assert any("Rule #0 Zero-Mock" in m for m in app.system_messages)

        # Test /scc
        app.system_messages.clear()
        pbar.execute_slash_command("/scc")
        assert any("Tarjan SCC Audit" in m for m in app.system_messages)

        # Test /engine status and /engine <name>
        app.system_messages.clear()
        pbar.execute_slash_command("/engine status")
        assert any("Multi-Engine Inference Statuses" in m for m in app.system_messages)

        app.system_messages.clear()
        pbar.execute_slash_command("/engine cloudflare")
        assert pbar.inference_router.active_engine == "cloudflare"

        # Test /key
        app.system_messages.clear()
        pbar.execute_slash_command("/key secret12345678")
        assert os.environ.get("GEMINI_API_KEY") == "secret12345678"
        assert any("sec...5678" in m for m in app.system_messages)

        # Test /duel
        app.system_messages.clear()
        pbar.execute_slash_command("/duel Latency vs Memory")
        assert any("Tri-Orchestrator Debate Duel" in m for m in app.system_messages)

        # Test /clear
        app.system_messages.clear()
        pbar.execute_slash_command("/clear")
        assert any("__CLEAR_CHAT__" in m for m in app.system_messages)


# ============================================================================
# 3. TEST CHAT IDE VIEW & SCREEN 1
# ============================================================================

class ChatIdeTestApp(App):
    def compose(self) -> ComposeResult:
        yield ChatIdeView(id="test-chat-ide-view")


@pytest.mark.asyncio
async def test_chat_ide_view_composition_and_execution():
    app = ChatIdeTestApp()
    async with app.run_test() as pilot:
        view = app.query_one(ChatIdeView)
        assert view is not None

        # Verify Left Main Pane (Chat + Code Buffer)
        chat = view.query_one(MultiAgentChatStream)
        assert chat is not None
        code_buf = view.query_one(ActiveCodeBuffer)
        assert code_buf is not None

        # Verify Right Sidebar (Debate Gauge + HUDs)
        gauge = view.query_one(DebateConsensusGauge)
        assert gauge is not None
        assert gauge.accordance == 0.9892

        # Verify chat appending
        chat.append_message("kimi", "Proposing TB4 DMA tensor sharding.")
        chat.append_message("qwen", "Verifying bounds.")
        chat.append_message("user", "Run the test suite.")

        # Verify code execution in safe runner
        sample_code = "print('TEST_OUTPUT_CANONICAL_SWARM_42')"
        view.execute_code(sample_code)
        await pilot.pause(0.1)

        # Toggle diff view
        code_buf.action_toggle_diff()
        assert code_buf.is_diff_view is True
        code_buf.action_toggle_diff()
        assert code_buf.is_diff_view is False


# ============================================================================
# 4. TEST HARDWARE NOC VIEW (TRACK ALPHA)
# ============================================================================

class HardwareNocTestApp(App):
    def compose(self) -> ComposeResult:
        yield HardwareNocView(id="test-noc-view")


@pytest.mark.asyncio
async def test_hardware_noc_view_3_column_bento():
    app = HardwareNocTestApp()
    async with app.run_test() as pilot:
        noc = app.query_one(HardwareNocView)
        assert noc is not None

        # Check Column 1: Node Telemetry Column
        col_tel = noc.query_one(NodeTelemetryColumn)
        assert col_tel is not None

        # Check Column 2: Biometrics DSP Center
        col_bio = noc.query_one(BiometricsDspCenter)
        assert col_bio is not None

        # Check Column 3: Daemon Supervisor HUD
        col_dae = noc.query_one(DaemonSupervisorHud)
        assert col_dae is not None

        # Check Bottom Event Ticker
        ticker = noc.query_one(BottomEventDock)
        assert ticker is not None
        ticker.add_event("OK", "TB4 DMA Interconnect latency verified: 0.277ms.")
        assert any("TB4 DMA" in ev for ev in ticker.event_log)

        # Refresh all views
        noc.refresh_all_views(force_refresh=False)


# ============================================================================
# 5. TEST NON-BLOCKING EVENT LOOP & RAPID SWITCHING
# ============================================================================

@pytest.mark.asyncio
async def test_harmonized_screen_navigation():
    from canonical_tui import CanonicalPortApp
    app = CanonicalPortApp()
    async with app.run_test() as pilot:
        # Initial screen should be agi_terminal / chat_ide
        assert app.current_screen_id == "agi_terminal"

        # Switch to Hardware
        app.switch_screen("hardware")
        assert app.current_screen_id == "hardware"

        # Switch to Biometrics
        app.switch_screen("biometrics")
        assert app.current_screen_id == "biometrics"

        # Switch to Explorer (Obsidian Graph)
        app.switch_screen("explorer")
        assert app.current_screen_id == "explorer"

        # Switch back to AGI Terminal
        app.switch_screen("agi_terminal")
        assert app.current_screen_id == "agi_terminal"
