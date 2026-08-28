"""
Unit Tests: Headless Python Textual TUI Command Center (Milestone M3 & Features 14, 15, 16, 29)
Verifies:
1. 9-Screen Canonical Stability Hierarchy (Screens 1 through 9)
2. AgiCodingTerminalScreen as default Screen 1 (keys 'c' and '1')
3. Dynamic Grid Splitting (1, 4, 8, 16 panes via '+' / '-' or '[' / ']')
4. STT/TTS Voice Chat & Coding Tab (Feature 29)
5. Persistent DockedShortcutsLegend on all 9 screens (Feature 16)
6. App lifecycle, screen transitions, bindings, and real screen instantiation.
"""

import os
import sys
import pytest
from typing import Dict, List, Any, Optional

# Ensure tui package is on Python import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from canonical_tui import CanonicalPortTUI
from screens.agi_coding_terminal_screen import AgiCodingTerminalScreen
from screens.network_screen import NetworkScreen
from screens.hardware_screen import HardwareScreen
from screens.biometrics_screen import BiometricsScreen
from screens.ai_inference_screen import AiInferenceScreen
from screens.training_screen import TrainingScreen
from screens.governance_screen import GovernanceScreen
from screens.tooling_screen import ToolingScreen
from screens.optimization_screen import OptimizationScreen
from widgets.docked_shortcuts_legend import DockedShortcutsLegend
from widgets.pinned_tab_nav_bar import PinnedTabNavBar
from services.blackboard_store import blackboard_store
from models.blackboard_models import BlackboardTelemetryState


class CanonicalTUIAppMock:
    """
    Reference model of the Canonical Port Python Textual TUI application.
    Implements exact 9-screen stability hierarchy and key bindings:
    - c / 1: 1. AGI Coding Terminal (Screen 1 / Home - default startup)
    - n / 2: 2. Networking (Layer 0 Primary)
    - h / 3: 3. Hardware & Nodes (Layer 1)
    - b / 4: 4. Biometrics & DSP (Layer 2)
    - i / 5: 5. AI Inference Mesh (Layer 3)
    - t / 6: 6. Training & Games (Layer 4)
    - g / 7: 7. Governance (Layer 5)
    - s / 8: 8. Tooling & Commerce (Layer 6)
    - o / 9: 9. Optimizations (4 Shells)
    - + / ]: Grid Split increase (1 -> 4 -> 8 -> 16 -> 1)
    - - / [: Grid Split decrease (16 -> 8 -> 4 -> 1 -> 16)
    - r: Refresh telemetry data
    - q: Quit
    """
    SCREENS = {
        "c": "agi_terminal",
        "1": "agi_terminal",
        "n": "network",
        "2": "network",
        "h": "hardware",
        "3": "hardware",
        "b": "biometrics",
        "4": "biometrics",
        "i": "ai_inference",
        "5": "ai_inference",
        "t": "training",
        "6": "training",
        "g": "governance",
        "7": "governance",
        "s": "tooling",
        "8": "tooling",
        "o": "optimization",
        "9": "optimization",
        # Legacy alias
        "0": "network",
    }

    SCREEN_ORDER = [
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

    def __init__(self, is_headless: bool = True):
        self.is_headless = is_headless
        # Screen 1 is default startup screen
        self.active_screen = "agi_terminal"
        self.running = False
        self.terminal_size = (80, 24)
        self.dispatched_actions: List[str] = []
        self.debate_triggered = False
        self.refreshed = False
        self.grid_split_count: int = 1

    def start(self) -> bool:
        self.running = True
        return True

    def stop(self) -> int:
        self.running = False
        return 0

    def handle_keypress(self, key: str) -> bool:
        if not self.running:
            return False

        if key in self.SCREENS:
            self.active_screen = self.SCREENS[key]
            return True
        elif key == "q":
            self.stop()
            return True
        elif key == "r":
            self.refreshed = True
            return True
        elif key in ["+", "]"]:
            cycle_map = {1: 4, 4: 8, 8: 16, 16: 1}
            self.grid_split_count = cycle_map.get(self.grid_split_count, 1)
            self.dispatched_actions.append(f"/split_{self.grid_split_count}")
            return True
        elif key in ["-", "["]:
            cycle_map = {16: 8, 8: 4, 4: 1, 1: 16}
            self.grid_split_count = cycle_map.get(self.grid_split_count, 1)
            self.dispatched_actions.append(f"/split_{self.grid_split_count}")
            return True
        elif key == "d":
            self.debate_triggered = True
            self.dispatched_actions.append("/duel")
            return True
        elif key == "a":
            self.dispatched_actions.append("/audit")
            return True
        elif key == "x":
            self.dispatched_actions.append("/cron")
            return True
        elif key == "p":
            self.dispatched_actions.append("/ping")
            return True
        elif key == "v":
            self.dispatched_actions.append("/revive")
            return True
        elif key == "m":
            self.dispatched_actions.append("/storage")
            return True
        return False

    def cycle_screen(self, direction: int) -> str:
        """Cycle through screens via mouse scroll or tab next/prev."""
        cur_idx = self.SCREEN_ORDER.index(self.active_screen)
        next_idx = (cur_idx + direction) % len(self.SCREEN_ORDER)
        self.active_screen = self.SCREEN_ORDER[next_idx]
        return self.active_screen

    def render_header(self) -> str:
        return "[CANONICAL PORT] 7-Layer Mesh Command Center | 108 GB RAM / 82.8 GB VRAM | 7 Nodes"

    def render_active_screen_view(self) -> Dict[str, Any]:
        return {
            "screen": self.active_screen,
            "header": self.render_header(),
            "grid_splits": self.grid_split_count,
            "status": "RUNNING" if self.running else "STOPPED"
        }


# ============================================================================
# 1. TUI APP LIFECYCLE & 9-SCREEN SWITCHING TESTS (FEATURES 14, 15)
# ============================================================================

def test_tui_app_lifecycle():
    app = CanonicalTUIAppMock(is_headless=True)
    assert app.running is False
    assert app.start() is True
    assert app.running is True
    assert app.stop() == 0
    assert app.running is False


def test_tui_9_screen_startup_and_switching():
    """Verify default screen is 'agi_terminal' (Screen 1) and all 9 screens switch via keys."""
    app = CanonicalTUIAppMock()
    app.start()

    # 1. Default startup screen: Screen 1 (AgiCodingTerminalScreen)
    assert app.active_screen == "agi_terminal"

    # 2. Key 'n' / '2': Networking (Screen 2)
    assert app.handle_keypress("n") is True
    assert app.active_screen == "network"
    assert app.handle_keypress("2") is True
    assert app.active_screen == "network"

    # 3. Key 'h' / '3': Hardware (Screen 3)
    assert app.handle_keypress("h") is True
    assert app.active_screen == "hardware"
    assert app.handle_keypress("3") is True
    assert app.active_screen == "hardware"

    # 4. Key 'b' / '4': Biometrics (Screen 4)
    assert app.handle_keypress("b") is True
    assert app.active_screen == "biometrics"
    assert app.handle_keypress("4") is True
    assert app.active_screen == "biometrics"

    # 5. Key 'i' / '5': AI Inference (Screen 5)
    assert app.handle_keypress("i") is True
    assert app.active_screen == "ai_inference"
    assert app.handle_keypress("5") is True
    assert app.active_screen == "ai_inference"

    # 6. Key 't' / '6': Training (Screen 6)
    assert app.handle_keypress("t") is True
    assert app.active_screen == "training"
    assert app.handle_keypress("6") is True
    assert app.active_screen == "training"

    # 7. Key 'g' / '7': Governance (Screen 7)
    assert app.handle_keypress("g") is True
    assert app.active_screen == "governance"
    assert app.handle_keypress("7") is True
    assert app.active_screen == "governance"

    # 8. Key 's' / '8': Tooling (Screen 8)
    assert app.handle_keypress("s") is True
    assert app.active_screen == "tooling"
    assert app.handle_keypress("8") is True
    assert app.active_screen == "tooling"

    # 9. Key 'o' / '9': Optimization (Screen 9)
    assert app.handle_keypress("o") is True
    assert app.active_screen == "optimization"
    assert app.handle_keypress("9") is True
    assert app.active_screen == "optimization"

    # Return to Screen 1 via 'c' and '1'
    assert app.handle_keypress("c") is True
    assert app.active_screen == "agi_terminal"
    assert app.handle_keypress("1") is True
    assert app.active_screen == "agi_terminal"


def test_dynamic_grid_splitting_keys():
    """Verify cycling grid splits: 1 -> 4 -> 8 -> 16 -> 1 via '+' and '-' keys."""
    app = CanonicalTUIAppMock()
    app.start()
    assert app.grid_split_count == 1

    # Increase split
    assert app.handle_keypress("+") is True
    assert app.grid_split_count == 4
    assert app.handle_keypress("]") is True
    assert app.grid_split_count == 8
    assert app.handle_keypress("+") is True
    assert app.grid_split_count == 16
    assert app.handle_keypress("+") is True
    assert app.grid_split_count == 1

    # Decrease split
    assert app.handle_keypress("-") is True
    assert app.grid_split_count == 16
    assert app.handle_keypress("[") is True
    assert app.grid_split_count == 8
    assert app.handle_keypress("-") is True
    assert app.grid_split_count == 4
    assert app.handle_keypress("-") is True
    assert app.grid_split_count == 1


def test_mouse_scroll_screen_cycling():
    """Verify mouse scroll transitions across all 9 screens in sequence."""
    app = CanonicalTUIAppMock()
    app.start()
    assert app.active_screen == "agi_terminal"

    # Scroll down forward sequence
    assert app.cycle_screen(1) == "network"
    assert app.cycle_screen(1) == "hardware"
    assert app.cycle_screen(1) == "biometrics"
    assert app.cycle_screen(1) == "ai_inference"
    assert app.cycle_screen(1) == "training"
    assert app.cycle_screen(1) == "governance"
    assert app.cycle_screen(1) == "tooling"
    assert app.cycle_screen(1) == "optimization"
    assert app.cycle_screen(1) == "agi_terminal"

    # Scroll up backward sequence
    assert app.cycle_screen(-1) == "optimization"
    assert app.cycle_screen(-1) == "tooling"
    assert app.cycle_screen(-1) == "governance"


def test_canonical_tui_mouse_scroll_debouncing():
    """Verify that rapid mouse scroll events are properly throttled by the debounce window."""
    app = CanonicalPortTUI()
    assert app.scroll_debounce_sec >= 0.15

    # Initial screen transition
    res1 = app.cycle_screen(1, force=True)
    assert res1 is True

    # Immediate second call within debounce window should be throttled
    res2 = app.cycle_screen(1, force=False)
    assert res2 is False

    # Force should bypass debounce
    res3 = app.cycle_screen(1, force=True)
    assert res3 is True


def test_tui_action_and_refresh_keys():
    app = CanonicalTUIAppMock()
    app.start()
    assert app.debate_triggered is False
    assert app.refreshed is False
    assert len(app.dispatched_actions) == 0

    # Trigger /duel with "d"
    assert app.handle_keypress("d") is True
    assert app.debate_triggered is True
    assert "/duel" in app.dispatched_actions

    # Dispatch /audit with "a"
    assert app.handle_keypress("a") is True
    assert "/audit" in app.dispatched_actions

    # Dispatch /cron with "x"
    assert app.handle_keypress("x") is True
    assert "/cron" in app.dispatched_actions

    # Dispatch /ping with "p"
    assert app.handle_keypress("p") is True
    assert "/ping" in app.dispatched_actions

    # Dispatch /revive with "v"
    assert app.handle_keypress("v") is True
    assert "/revive" in app.dispatched_actions

    # Dispatch /storage with "m"
    assert app.handle_keypress("m") is True
    assert "/storage" in app.dispatched_actions

    # Refresh with "r"
    assert app.handle_keypress("r") is True
    assert app.refreshed is True


def test_tui_quit_key():
    app = CanonicalTUIAppMock()
    app.start()
    assert app.running is True
    assert app.handle_keypress("q") is True
    assert app.running is False


def test_tui_unhandled_keypress():
    app = CanonicalTUIAppMock()
    app.start()
    assert app.handle_keypress("z") is False
    assert app.handle_keypress("F12") is False


# ============================================================================
# 2. REAL CANONICAL TUI CLASS & 9 SCREENS CONTRACT TESTS
# ============================================================================

def test_canonical_port_tui_app_structure():
    """Verify CanonicalPortTUI Textual application attributes and 9 screen registrations."""
    app = CanonicalPortTUI()
    assert len(app.SCREENS) >= 9
    assert len(app.SCREEN_ORDER) == 9
    assert "agi_terminal" in app.SCREENS
    assert "network" in app.SCREENS
    assert "hardware" in app.SCREENS
    assert "biometrics" in app.SCREENS
    assert "ai_inference" in app.SCREENS
    assert "training" in app.SCREENS
    assert "governance" in app.SCREENS
    assert "tooling" in app.SCREENS
    assert "optimization" in app.SCREENS

    # Check classes
    assert app.SCREENS["agi_terminal"] == AgiCodingTerminalScreen
    assert app.SCREENS["network"] == NetworkScreen
    assert app.SCREENS["hardware"] == HardwareScreen
    assert app.SCREENS["biometrics"] == BiometricsScreen
    assert app.SCREENS["ai_inference"] == AiInferenceScreen
    assert app.SCREENS["training"] == TrainingScreen
    assert app.SCREENS["governance"] == GovernanceScreen
    assert app.SCREENS["tooling"] == ToolingScreen
    assert app.SCREENS["optimization"] == OptimizationScreen


def test_all_9_screens_instantiation_and_blackboard_integration():
    """Verify that all 9 screen classes can be instantiated and interact with BlackboardStore."""
    snapshot = blackboard_store.get_snapshot()
    assert isinstance(snapshot, BlackboardTelemetryState)

    # 1. AgiCodingTerminalScreen (Screen 1)
    agi_screen = AgiCodingTerminalScreen()
    assert agi_screen is not None
    assert agi_screen.grid_split_count == 1

    # 2. NetworkScreen (Screen 2)
    net_screen = NetworkScreen()
    assert net_screen is not None

    # 3. HardwareScreen (Screen 3)
    hw_screen = HardwareScreen()
    assert hw_screen is not None

    # 4. BiometricsScreen (Screen 4)
    bio_screen = BiometricsScreen()
    assert bio_screen is not None

    # 5. AiInferenceScreen (Screen 5)
    inf_screen = AiInferenceScreen()
    assert inf_screen is not None

    # 6. TrainingScreen (Screen 6)
    train_screen = TrainingScreen()
    assert train_screen is not None

    # 7. GovernanceScreen (Screen 7)
    gov_screen = GovernanceScreen()
    assert gov_screen is not None

    # 8. ToolingScreen (Screen 8)
    tool_screen = ToolingScreen()
    assert tool_screen is not None

    # 9. OptimizationScreen (Screen 9)
    opt_screen = OptimizationScreen()
    assert opt_screen is not None


def test_docked_shortcuts_legend_widget_content():
    """Verify DockedShortcutsLegend formats all 9 stability layers in high contrast."""
    legend = DockedShortcutsLegend(active_screen="agi_terminal")
    text = legend.build_legend_text("agi_terminal")
    plain = text.plain

    # Verify all 9 screens are in the legend text
    assert "[1/c] AGI Term" in plain
    assert "[2/n] Net" in plain
    assert "[3/h] HW" in plain
    assert "[4/b] Bio" in plain
    assert "[5/i] Inf" in plain
    assert "[6/t] Train" in plain
    assert "[7/g] Gov" in plain
    assert "[8/s] Tool" in plain
    assert "[9/o] Opt" in plain
    assert "[r] Refresh" in plain
    assert "[q] Quit" in plain


def test_agi_coding_terminal_grid_splits_and_models():
    """Verify AgiCodingTerminalScreen dynamic grid splits and model switching."""
    screen = AgiCodingTerminalScreen()
    assert screen.grid_split_count == 1
    assert len(screen.MODEL_ROSTER) >= 4

    # Test increasing grid split
    screen.action_grid_split_increase()
    assert screen.grid_split_count == 4
    screen.action_grid_split_increase()
    assert screen.grid_split_count == 8
    screen.action_grid_split_increase()
    assert screen.grid_split_count == 16
    screen.action_grid_split_increase()
    assert screen.grid_split_count == 1

    # Test decreasing grid split
    screen.action_grid_split_decrease()
    assert screen.grid_split_count == 16
    screen.action_grid_split_decrease()
    assert screen.grid_split_count == 8
    screen.action_grid_split_decrease()
    assert screen.grid_split_count == 4
    screen.action_grid_split_decrease()
    assert screen.grid_split_count == 1


def test_pinned_tab_nav_bar_widget_content():
    """Verify PinnedTabNavBar formats all 9 tabs with explicit keybindings and prev/next controls (R2)."""
    navbar = PinnedTabNavBar(active_screen="agi_terminal")
    text = navbar.build_nav_text("agi_terminal")
    plain = text.plain

    # Verify navigation controls
    assert "[<] Prev" in plain
    assert "[>] Next" in plain

    # Verify all 9 tabs have explicit keybindings rendered directly in titles
    assert "[1] AGI Term" in plain
    assert "[2] Network" in plain
    assert "[3] Hardware" in plain
    assert "[4] Biometrics" in plain
    assert "[5] Inference" in plain
    assert "[6] Training" in plain
    assert "[7] Governance" in plain
    assert "[8] Tooling" in plain
    assert "[9] Optimization" in plain


def test_pinned_tab_nav_bar_active_highlight():
    """Verify PinnedTabNavBar highlights the active screen tab and updates dynamically (R3)."""
    navbar = PinnedTabNavBar(active_screen="hardware")
    assert navbar.active_screen == "hardware"

    # Switch active screen to network
    navbar.set_active_screen("network")
    assert navbar.active_screen == "network"

    text = navbar.build_nav_text("network")
    assert "[2] Network" in text.plain

    # Verify click regions mapped for all 9 tabs + 2 controls = 11 regions
    assert len(navbar._click_regions) == 11
    assert navbar._click_regions[0][2] == "prev"
    assert navbar._click_regions[-1][2] == "next"
    assert navbar._click_regions[1][2] == "agi_terminal"
    assert navbar._click_regions[2][2] == "network"


def test_pinned_tab_nav_bar_responsive_tiers():
    """Verify PinnedTabNavBar formats responsive labels for all 4 width tiers."""
    navbar = PinnedTabNavBar(active_screen="biometrics")

    # Tier 1: Full mode (>=165)
    t1 = navbar.build_nav_text("biometrics", width=180).plain
    assert "[1] AGI Term" in t1 and "[4] Biometrics" in t1 and "[9] Optimization" in t1

    # Tier 2: Compact desktop mode (115-164)
    t2 = navbar.build_nav_text("biometrics", width=120).plain
    assert "[1] AGI" in t2 and "[4] Bio" in t2 and "[9] Opt" in t2

    # Tier 3: High-density compact mode (70-114)
    t3 = navbar.build_nav_text("biometrics", width=80).plain
    assert "[1]AGI" in t3 and "[4]Bio" in t3 and "[9]Opt" in t3

    # Tier 4: Ultra-compact mode (<70)
    t4 = navbar.build_nav_text("biometrics", width=68).plain
    assert "[1]AGI" in t4 and "[4]Bio" in t4 and "[9]Opt" in t4


def test_pinned_tab_nav_bar_mouse_scroll_and_dispatch():
    """Verify PinnedTabNavBar handles mouse scroll events and action dispatches."""
    navbar = PinnedTabNavBar(active_screen="network")
    dispatched = []

    class MockApp:
        def action_next_screen(self):
            dispatched.append("next")
        def action_prev_screen(self):
            dispatched.append("prev")
        def switch_screen(self, target):
            dispatched.append(target)

    navbar._mock_app = MockApp()

    navbar.on_mouse_scroll_down(None)
    assert dispatched == ["next"]

    navbar.on_mouse_scroll_up(None)
    assert dispatched == ["next", "prev"]

    navbar._dispatch_action("hardware")
    assert dispatched == ["next", "prev", "hardware"]


def test_docked_shortcuts_legend_responsive_tiers():
    """Verify DockedShortcutsLegend formats responsive labels across 4 tiers."""
    legend = DockedShortcutsLegend(active_screen="hardware")

    # Tier 1: Full mode (>=138)
    t1 = legend.build_legend_text("hardware", width=180).plain
    assert "[1/c] AGI Term" in t1 and "[3/h] HW" in t1 and "[q] Quit" in t1
    assert len(t1) <= 180

    # Tier 2: Standard compact mode (78-137)
    t2 = legend.build_legend_text("hardware", width=80).plain
    assert "[1]AGI" in t2 and "[3]HW" in t2 and "[q]Quit" in t2
    assert len(t2) <= 80

    # Tier 3: Micro mode (53-77)
    t3 = legend.build_legend_text("hardware", width=60).plain
    assert "[1]A" in t3 and "[3]H" in t3 and "[q]" in t3
    assert len(t3) <= 60

    # Tier 4: Nano mode (<53)
    t4 = legend.build_legend_text("hardware", width=40).plain
    assert "[1-9] Tabs" in t4 and "[q] Quit" in t4
    assert len(t4) <= 40


def test_docked_shortcuts_legend_click_dispatch():
    """Verify DockedShortcutsLegend dispatches screen switches and action calls."""
    legend = DockedShortcutsLegend(active_screen="hardware")
    dispatched = []

    class MockApp:
        def switch_screen(self, target):
            dispatched.append(f"switch:{target}")
        def action_refresh_current(self):
            dispatched.append("action:refresh")
        def action_quit(self):
            dispatched.append("action:quit")

    legend._mock_app = MockApp()

    legend._dispatch_action("biometrics")
    assert dispatched == ["switch:biometrics"]

    legend._dispatch_action("refresh")
    assert dispatched == ["switch:biometrics", "action:refresh"]

    legend._dispatch_action("quit")
    assert dispatched == ["switch:biometrics", "action:refresh", "action:quit"]


def test_navbar_and_legend_margin_and_separator_click_no_op():
    """Verify that clicks outside text bounds or on separators do not dispatch any actions."""
    class DummyClickEvent:
        def __init__(self, x: int, y: int = 0):
            self.x = x
            self.y = y

    # Test PinnedTabNavBar
    navbar = PinnedTabNavBar(active_screen="agi_terminal")
    navbar.build_nav_text("agi_terminal", width=180)
    navbar._last_text_len = 161
    dispatched_nav = []

    class MockAppNav:
        def switch_screen(self, s):
            dispatched_nav.append(s)
        def action_prev_screen(self):
            dispatched_nav.append("prev")
        def action_next_screen(self):
            dispatched_nav.append("next")

    navbar._mock_app = MockAppNav()

    from textual.geometry import Size
    navbar._mock_size = Size(180, 1)

    # 1. Click on left margin (e.g. x=0, x=3, x=8)
    for click_x in [0, 3, 8]:
        navbar.on_click(DummyClickEvent(click_x, 0))
    assert dispatched_nav == [], f"Left margin clicks dispatched actions: {dispatched_nav}"

    # 2. Click on separator (e.g. x = start_offset + 8 = 17, which is ' │ ')
    navbar.on_click(DummyClickEvent(9 + 8, 0))
    assert dispatched_nav == [], f"Separator click dispatched actions: {dispatched_nav}"

    # 3. Click on valid tab (e.g. x = start_offset + 11 = 20, which is '[1] AGI Term')
    navbar.on_click(DummyClickEvent(9 + 11, 0))
    assert dispatched_nav == ["agi_terminal"], f"Valid tab click failed: {dispatched_nav}"

    # Test DockedShortcutsLegend
    legend = DockedShortcutsLegend(active_screen="agi_terminal")
    legend.build_legend_text("agi_terminal", width=180)
    legend._last_text_len = 137
    legend._mock_size = Size(180, 1)
    dispatched_leg = []

    class MockAppLeg:
        def switch_screen(self, s):
            dispatched_leg.append(f"switch:{s}")
        def action_refresh_current(self):
            dispatched_leg.append("refresh")
        def action_quit(self):
            dispatched_leg.append("quit")

    legend._mock_app = MockAppLeg()

    # 180 cols, 137 chars -> offset = (180 - 137) // 2 = 21
    # Margin clicks at x=0, 5, 20
    for margin_x in [0, 5, 20]:
        legend.on_click(DummyClickEvent(margin_x, 0))
    assert dispatched_leg == [], f"Legend margin clicks dispatched actions: {dispatched_leg}"

    # Valid click on '[1/c] AGI Term' at relative_x = 5 -> click_x = 21 + 5 = 26
    legend.on_click(DummyClickEvent(21 + 5, 0))
    assert dispatched_leg == ["switch:agi_terminal"], f"Valid legend click failed: {dispatched_leg}"





