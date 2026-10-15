#!/usr/bin/env python3
"""
Canonical Port - Headless Python Textual TUI Command Center
Version: 4.0.0-HARMONIZED
Unified terminal user interface for the Lauburu 7-layer mesh ecosystem.
Implements the 9-Screen Stability Hierarchy with Victor Harmonization:
- Screen 1: ChatIdeView / AgiCodingTerminalView (Key 'c' or '1') — Harmonized Swarm IDE & Chat Shell
- Screen 2: NetworkView (Layer 0 Primary) — Key 'n' or '2'
- Screen 3: HardwareView (Layer 1 NOC Cockpit) — Key 'h' or '3'
- Screen 4: BiometricsView (Layer 2 Medical DSP) — Key 'b' or '4'
- Screen 5: AiInferenceView (Layer 3 Model Mesh) — Key 'i' or '5'
- Screen 6: TrainingView (Layer 4 LoRA & Games Arena) — Key 't' or '6'
- Screen 7: GovernanceView (Layer 5 Infinite Debate) — Key 'g' or '7'
- Screen 8: ToolingView (Layer 6 Daemons & MCP) — Key 's' or '8'
- Screen 9: OptimizationView (Shells) — Key 'o' or '9'
- Screen 0 / 'a': AllTabsGridView
- Screen 'e' / 'x': ArchitectureExplorerView (Obsidian Vault Graph Explorer)
"""

import sys
import os
import time
from typing import Dict, Any, Type, Union, List
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual.screen import Screen
from textual.containers import Container

# Ensure tui directory is on import path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from views.chat_ide_view import ChatIdeView
    from views.agi_coding_terminal_view import AgiCodingTerminalView
    from views.network_view import NetworkView
    from views.hardware_view import HardwareView
    from views.biometrics_view import BiometricsView
    from views.ai_inference_view import AiInferenceView
    from views.training_view import TrainingView
    from views.governance_view import GovernanceView
    from views.swarm_audit_view import SwarmAuditView

    from views.tooling_view import ToolingView
    from views.optimization_view import OptimizationView
    from views.all_tabs_view import AllTabsGridView
    from views.architecture_explorer_view import ArchitectureExplorerView
    from views.commercialization_view import CommercializationView
    from views.live_arena_dev_view import LiveArenaDevView
    from views.chat_ide_view import ChatIdeView
    from views.hardware_noc_view import HardwareNocView
    from views.biometrics_view import BiometricsView
    from views.architecture_explorer_view import ArchitectureExplorerView
    from widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from widgets.canonical_header_bar import CanonicalHeaderBar, CanonicalEngineChanged
    from widgets.canonical_prompt_bar import CanonicalPromptBar
    from widgets.engine_selector import EngineSelectorWidget, InferenceEngineChanged
except ImportError:
    from tui.screens.chat_ide_view import ChatIdeView
    from tui.screens.agi_coding_terminal_view import AgiCodingTerminalView
    from tui.screens.network_view import NetworkView
    from tui.screens.hardware_view import HardwareView
    from tui.screens.biometrics_view import BiometricsView
    from tui.screens.ai_inference_view import AiInferenceView
    from tui.screens.training_view import TrainingView
    from tui.screens.governance_view import GovernanceView
    from tui.screens.tooling_view import ToolingView
    from tui.screens.optimization_view import OptimizationView
    from tui.screens.all_tabs_view import AllTabsGridView
    from tui.screens.architecture_explorer_view import ArchitectureExplorerView
    from tui.views.chat_ide_view import ChatIdeView
    from tui.views.hardware_noc_view import HardwareNocView
    from tui.views.biometrics_view import BiometricsView
    from tui.views.architecture_explorer_view import ArchitectureExplorerView
    from tui.widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from tui.widgets.canonical_header_bar import CanonicalHeaderBar, CanonicalEngineChanged
    from tui.widgets.canonical_prompt_bar import CanonicalPromptBar
    from tui.widgets.engine_selector import EngineSelectorWidget, InferenceEngineChanged


class CanonicalPortApp(App):
    """
    Main Canonical Port Textual Application.
    Provides 9-Screen Stability Hierarchy navigation, non-blocking telemetry streaming,
    and Unyielding Consensus Multi-Orchestrator AI Debate integration.
    """
    
    TITLE = "CANONICAL PORT — LAUBURU MESH TUI"
    SUB_TITLE = "7-Layer Mesh Command Center — 108 GB RAM / 82.8 GB VRAM Pooled AI Governor (7 Nodes)"
    
    CSS = """
Screen {
    background: #070b12;
    color: #e2e8f0;
}
Header {
    dock: top;
    height: 1;
    background: #0b111c;
}
Footer {
    dock: bottom;
    height: 1;
    background: #070b12;
    border-top: solid #1e293b;
}
"""

    def _wrap_in_screen(container_cls: Type[Container]) -> Type[Screen]:
        class WrapperScreen(Screen):
            def compose(self):
                yield container_cls(id="content_container")
        return WrapperScreen

    SCREENS: Dict[str, Type[Screen]] = {
        "chat_ide": _wrap_in_screen(ChatIdeView),
        "agi_terminal": _wrap_in_screen(AgiCodingTerminalView),
        "network": _wrap_in_screen(NetworkView),
        "hardware": _wrap_in_screen(HardwareView),
        "biometrics": _wrap_in_screen(BiometricsView),
        "ai_inference": _wrap_in_screen(AiInferenceView),
        "training": _wrap_in_screen(TrainingView),
        "governance": _wrap_in_screen(GovernanceView),
        "tooling": _wrap_in_screen(ToolingView),
        "optimization": _wrap_in_screen(OptimizationView),
        "all_tabs": _wrap_in_screen(AllTabsGridView),
        "explorer": _wrap_in_screen(ArchitectureExplorerView),
        "commercialization": _wrap_in_screen(CommercializationView),
        "live_arena_dev": _wrap_in_screen(LiveArenaDevView),
    }

    SCREEN_ORDER: List[str] = [
        "agi_terminal",
        "network",
        "hardware",
        "biometrics",
        "ai_inference",
        "training",
        "governance",
        "tooling",
        "optimization",
        "live_arena_dev",
    ]

    BINDINGS: List[Binding] = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
        Binding("r", "refresh_current", "Refresh"),
        Binding("c", "show_agi_terminal", "AGI Terminal"),
        Binding("1", "show_agi_terminal", "AGI Terminal"),
        Binding("n", "show_network", "Network"),
        Binding("2", "show_network", "Network"),
        Binding("h", "show_hardware", "Hardware"),
        Binding("3", "show_hardware", "Hardware"),
        Binding("b", "show_biometrics", "Biometrics"),
        Binding("4", "show_biometrics", "Biometrics"),
        Binding("i", "show_ai_inference", "Inference"),
        Binding("5", "show_ai_inference", "Inference"),
        Binding("t", "show_training", "Training"),
        Binding("6", "show_training", "Training"),
        Binding("g", "show_governance", "Governance"),
        Binding("7", "show_governance", "Governance"),
        Binding("s", "show_tooling", "Tooling"),
        Binding("8", "show_tooling", "Tooling"),
        Binding("o", "show_optimization", "Optimization"),
        Binding("9", "show_optimization", "Optimization"),
        Binding("v", "show_live_arena_dev", "Arena Dev"),
        Binding("0", "show_all_tabs", "All Tabs"),
        Binding("a", "show_all_tabs", "All Tabs"),
        Binding("e", "show_explorer", "Explorer"),
        Binding("x", "show_explorer", "Explorer"),
        Binding("dollar", "show_commercialization", "Capability Tiers ($)", priority=True),
        Binding("$", "show_commercialization", "Capability Tiers ($)", priority=True),
        Binding("f10", "show_commercialization", "Capability Tiers ($)", priority=True),
        Binding("less_than", "previous_view", "Prev Screen"),
        Binding("<", "previous_view", "Prev Screen"),
        Binding("left", "previous_view", "Prev Screen"),
        Binding("greater_than", "next_view", "Next Screen"),
        Binding(">", "next_view", "Next Screen"),
        Binding("right", "next_view", "Next Screen"),
        Binding("ctrl+e", "cycle_inference_engine", "Switch Engine", priority=True),
        Binding("f2", "cycle_inference_engine", "Switch Engine", priority=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scroll_debounce_sec: float = 0.20
        self.current_view_id: str = "agi_terminal"
        self._last_scroll_time: float = 0.0

    def on_mount(self) -> None:
        """Mounts default startup screen (agi_terminal)."""
        self.push_screen("agi_terminal")

    def switch_view(self, screen: str) -> None:
        """Switches active screen and updates navigation bar state."""
        self.current_view_id = screen
        if getattr(self, "_screen_stack", None):
            try:
                self.switch_screen(screen)
                active_s = self.screen
                if hasattr(active_s, "query_one"):
                    nav = active_s.query_one(PinnedTabNavBar)
                    if nav:
                        nav.set_active_view(screen)
            except Exception:
                pass

    def cycle_view(self, delta: int = 1, force: bool = False) -> Union[str, bool]:
        """Cycles through screens in canonical order with debounced mouse wheel throttling."""
        now = time.time()
        if not force and (now - self._last_scroll_time < self.scroll_debounce_sec):
            return False

        self._last_scroll_time = now
        try:
            cur_idx = self.SCREEN_ORDER.index(self.current_view_id)
        except ValueError:
            cur_idx = 0

        next_idx = (cur_idx + delta) % len(self.SCREEN_ORDER)
        self.current_view_id = self.SCREEN_ORDER[next_idx]
        self.switch_view(self.current_view_id)

        if force:
            return True
        return self.current_view_id

    def action_previous_view(self) -> None:
        self.cycle_view(-1, force=True)

    def action_next_view(self) -> None:
        self.cycle_view(1, force=True)

    def action_refresh_current(self) -> None:
        """Triggers non-blocking snapshot refresh on active screen."""
        try:
            active = self.screen
            if hasattr(active, "refresh_views"):
                active.refresh_views()
        except Exception:
            pass

    def action_show_agi_terminal(self) -> None:
        self.switch_view("agi_terminal")

    def action_show_network(self) -> None:
        self.switch_view("network")

    def action_show_hardware(self) -> None:
        self.switch_view("hardware")

    def action_show_biometrics(self) -> None:
        self.switch_view("biometrics")

    def action_show_ai_inference(self) -> None:
        self.switch_view("ai_inference")

    def action_show_training(self) -> None:
        self.switch_view("training")

    def action_show_governance(self) -> None:
        self.switch_view("governance")

    def action_show_tooling(self) -> None:
        self.switch_view("tooling")

    def action_show_all_tabs(self) -> None:
        self.switch_view("all_tabs")

    def action_show_optimization(self) -> None:
        self.switch_view("optimization")

    def action_show_explorer(self) -> None:
        self.switch_view("explorer")

    def action_show_commercialization(self) -> None:
        self.switch_view("commercialization")

    def action_show_live_arena_dev(self) -> None:
        self.switch_view("live_arena_dev")

    def action_cycle_inference_engine(self) -> None:
        """Global action to cycle active inference engine (ctrl+e / F2)."""
        try:
            active_s = self.screen
            if hasattr(active_s, "action_cycle_inference_engine"):
                active_s.action_cycle_inference_engine()
            elif hasattr(active_s, "query_one"):
                header = active_s.query_one(CanonicalHeaderBar)
                if header:
                    header.cycle_engine(1)
                else:
                    sel = active_s.query_one(EngineSelectorWidget)
                    if sel:
                        sel.cycle_engine(1)
        except Exception:
            pass

    def on_inference_engine_changed(self, event: Union[InferenceEngineChanged, CanonicalEngineChanged]) -> None:
        """Propagate engine change events across screens."""
        try:
            active_s = self.screen
            if hasattr(active_s, "on_inference_engine_changed"):
                active_s.on_inference_engine_changed(event)
            elif hasattr(active_s, "on_canonical_engine_changed"):
                active_s.on_canonical_engine_changed(event)
            elif hasattr(active_s, "refresh_views"):
                active_s.refresh_views()
        except Exception:
            pass


# Canonical alias and module-level app instance for 'textual run --dev'
CanonicalPortTUI = CanonicalPortApp
app = CanonicalPortApp()

if __name__ == "__main__":
    app.run()
