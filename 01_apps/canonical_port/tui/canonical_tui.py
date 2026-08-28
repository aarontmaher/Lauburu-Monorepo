#!/usr/bin/env python3
"""
Canonical Port - Headless Python Textual TUI Command Center
Version: 4.0.0-HARMONIZED
Unified terminal user interface for the Lauburu 7-layer mesh ecosystem.
Implements the 9-Screen Stability Hierarchy with Victor Harmonization:
- Screen 1: ChatIdeScreen / AgiCodingTerminalScreen (Key 'c' or '1') — Harmonized Swarm IDE & Chat Shell
- Screen 2: NetworkScreen (Layer 0 Primary) — Key 'n' or '2'
- Screen 3: HardwareScreen (Layer 1 NOC Cockpit) — Key 'h' or '3'
- Screen 4: BiometricsScreen (Layer 2 Medical DSP) — Key 'b' or '4'
- Screen 5: AiInferenceScreen (Layer 3 Model Mesh) — Key 'i' or '5'
- Screen 6: TrainingScreen (Layer 4 LoRA & Games Arena) — Key 't' or '6'
- Screen 7: GovernanceScreen (Layer 5 Infinite Debate) — Key 'g' or '7'
- Screen 8: ToolingScreen (Layer 6 Daemons & MCP) — Key 's' or '8'
- Screen 9: OptimizationScreen (Shells) — Key 'o' or '9'
- Screen 0 / 'a': AllTabsGridScreen
- Screen 'e' / 'x': ArchitectureExplorerScreen (Obsidian Vault Graph Explorer)
"""

import sys
import os
import time
from typing import Dict, Any, Type, Union, List
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual.screen import Screen

# Ensure tui directory is on import path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from screens.chat_ide_screen import ChatIdeScreen
    from screens.agi_coding_terminal_screen import AgiCodingTerminalScreen
    from screens.network_screen import NetworkScreen
    from screens.hardware_screen import HardwareScreen
    from screens.biometrics_screen import BiometricsScreen
    from screens.ai_inference_screen import AiInferenceScreen
    from screens.training_screen import TrainingScreen
    from screens.governance_screen import GovernanceScreen
    from screens.swarm_audit_screen import SwarmAuditScreen

    from screens.tooling_screen import ToolingScreen
    from screens.optimization_screen import OptimizationScreen
    from screens.all_tabs_screen import AllTabsGridScreen
    from screens.architecture_explorer_screen import ArchitectureExplorerScreen
    from screens.commercialization_screen import CommercializationScreen
    from views.chat_ide_view import ChatIdeView
    from views.hardware_noc_view import HardwareNocView
    from views.biometrics_view import BiometricsView
    from views.architecture_explorer_view import ArchitectureExplorerView
    from widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from widgets.canonical_header_bar import CanonicalHeaderBar, CanonicalEngineChanged
    from widgets.canonical_prompt_bar import CanonicalPromptBar
    from widgets.engine_selector import EngineSelectorWidget, InferenceEngineChanged
except ImportError:
    from tui.screens.chat_ide_screen import ChatIdeScreen
    from tui.screens.agi_coding_terminal_screen import AgiCodingTerminalScreen
    from tui.screens.network_screen import NetworkScreen
    from tui.screens.hardware_screen import HardwareScreen
    from tui.screens.biometrics_screen import BiometricsScreen
    from tui.screens.ai_inference_screen import AiInferenceScreen
    from tui.screens.training_screen import TrainingScreen
    from tui.screens.governance_screen import GovernanceScreen
    from tui.screens.tooling_screen import ToolingScreen
    from tui.screens.optimization_screen import OptimizationScreen
    from tui.screens.all_tabs_screen import AllTabsGridScreen
    from tui.screens.architecture_explorer_screen import ArchitectureExplorerScreen
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

    SCREENS: Dict[str, Type[Screen]] = {
        "chat_ide": ChatIdeScreen,
        "agi_terminal": AgiCodingTerminalScreen,
        "network": NetworkScreen,
        "hardware": HardwareScreen,
        "biometrics": BiometricsScreen,
        "ai_inference": AiInferenceScreen,
        "training": TrainingScreen,
        "governance": GovernanceScreen,
        "tooling": ToolingScreen,
        "optimization": OptimizationScreen,
        "all_tabs": AllTabsGridScreen,
        "explorer": ArchitectureExplorerScreen,
        "commercialization": CommercializationScreen,
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
        Binding("0", "show_all_tabs", "All Tabs"),
        Binding("a", "show_all_tabs", "All Tabs"),
        Binding("e", "show_explorer", "Explorer"),
        Binding("x", "show_explorer", "Explorer"),
        Binding("dollar", "show_commercialization", "Capability Tiers ($)", priority=True),
        Binding("$", "show_commercialization", "Capability Tiers ($)", priority=True),
        Binding("f10", "show_commercialization", "Capability Tiers ($)", priority=True),
        Binding("less_than", "previous_screen", "Prev Screen"),
        Binding("<", "previous_screen", "Prev Screen"),
        Binding("left", "previous_screen", "Prev Screen"),
        Binding("greater_than", "next_screen", "Next Screen"),
        Binding(">", "next_screen", "Next Screen"),
        Binding("right", "next_screen", "Next Screen"),
        Binding("ctrl+e", "cycle_inference_engine", "Switch Engine", priority=True),
        Binding("f2", "cycle_inference_engine", "Switch Engine", priority=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scroll_debounce_sec: float = 0.20
        self.current_screen_id: str = "agi_terminal"
        self._last_scroll_time: float = 0.0

    def on_mount(self) -> None:
        """Mounts default startup screen (agi_terminal)."""
        self.push_screen("agi_terminal")

    def switch_screen(self, screen: str) -> None:
        """Switches active screen and updates navigation bar state."""
        self.current_screen_id = screen
        if getattr(self, "_screen_stack", None):
            try:
                super().switch_screen(screen)
                active_s = self.screen
                if hasattr(active_s, "query_one"):
                    nav = active_s.query_one(PinnedTabNavBar)
                    if nav:
                        nav.set_active_screen(screen)
            except Exception:
                pass

    def cycle_screen(self, delta: int = 1, force: bool = False) -> Union[str, bool]:
        """Cycles through screens in canonical order with debounced mouse wheel throttling."""
        now = time.time()
        if not force and (now - self._last_scroll_time < self.scroll_debounce_sec):
            return False

        self._last_scroll_time = now
        try:
            cur_idx = self.SCREEN_ORDER.index(self.current_screen_id)
        except ValueError:
            cur_idx = 0

        next_idx = (cur_idx + delta) % len(self.SCREEN_ORDER)
        self.current_screen_id = self.SCREEN_ORDER[next_idx]
        self.switch_screen(self.current_screen_id)

        if force:
            return True
        return self.current_screen_id

    def action_previous_screen(self) -> None:
        self.cycle_screen(-1, force=True)

    def action_next_screen(self) -> None:
        self.cycle_screen(1, force=True)

    def action_refresh_current(self) -> None:
        """Triggers non-blocking snapshot refresh on active screen."""
        try:
            active = self.screen
            if hasattr(active, "refresh_views"):
                active.refresh_views()
        except Exception:
            pass

    def action_show_agi_terminal(self) -> None:
        self.switch_screen("agi_terminal")

    def action_show_network(self) -> None:
        self.switch_screen("network")

    def action_show_hardware(self) -> None:
        self.switch_screen("hardware")

    def action_show_biometrics(self) -> None:
        self.switch_screen("biometrics")

    def action_show_ai_inference(self) -> None:
        self.switch_screen("ai_inference")

    def action_show_training(self) -> None:
        self.switch_screen("training")

    def action_show_governance(self) -> None:
        self.switch_screen("governance")

    def action_show_tooling(self) -> None:
        self.switch_screen("tooling")

    def action_show_all_tabs(self) -> None:
        self.switch_screen("all_tabs")

    def action_show_optimization(self) -> None:
        self.switch_screen("optimization")

    def action_show_explorer(self) -> None:
        self.switch_screen("explorer")

    def action_show_commercialization(self) -> None:
        self.switch_screen("commercialization")

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


# Canonical alias
CanonicalPortTUI = CanonicalPortApp

if __name__ == "__main__":
    app = CanonicalPortApp()
    app.run()
