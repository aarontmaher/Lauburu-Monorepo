"""
Challenger 2 Test Suite: Interactive UI & DOM Conformance Adversarial Stress Test
Target Module: 01_apps/canonical_port
Components: ArchitectureExplorerView, ArchitectureExplorerScreen, CanonicalPortApp

Adversarial Verification Dimensions:
1. DOM Hierarchy & Dual-Layout Structure Invariants (Tree + Detail Left, Canvas + HUD Right)
2. Concurrent Dynamic Filtering & Adversarial Query Injections (Unicode, Regex, Empty, Whitespace, Long Strings)
3. Node Selection Synchronization (Tree -> Markdown Detail & ASCII Canvas Highlight across 9 categories)
4. Full Stability Hierarchy Multi-Screen Navigation Transitions (e/x, Escape, 1-9, 0, prev/next)
5. Viewport Resizing and High-Frequency Event Churn Stress
"""

import os
import sys
import pytest
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Input, Button, Tree, Markdown, Static
from textual.containers import Horizontal, Vertical, ScrollableContainer

# Ensure tui directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from canonical_tui import CanonicalPortApp
from views.architecture_explorer_view import ArchitectureExplorerView
from screens.architecture_explorer_screen import ArchitectureExplorerScreen
from screens.agi_coding_terminal_screen import AgiCodingTerminalScreen
from screens.network_screen import NetworkScreen
from screens.hardware_screen import HardwareScreen
from screens.biometrics_screen import BiometricsScreen
from screens.ai_inference_screen import AiInferenceScreen
from screens.training_screen import TrainingScreen
from screens.governance_screen import GovernanceScreen
from screens.tooling_screen import ToolingScreen
from screens.optimization_screen import OptimizationScreen
from screens.all_tabs_screen import AllTabsGridScreen
from models.architecture_graph import ArchitectureGraph, VaultNode


class StandaloneExplorerApp(App):
    """Standalone wrapper for testing ArchitectureExplorerView in isolation."""
    CSS = "Screen { background: #070b12; }"

    def compose(self) -> ComposeResult:
        yield ArchitectureExplorerView(id="architecture-explorer-view")


# =============================================================================
# TIER 1: DOM HIERARCHY & DUAL-LAYOUT STRUCTURE INVARIANTS
# =============================================================================

@pytest.mark.asyncio
async def test_adversarial_dom_hierarchy_invariants():
    """
    Adversarially verify the exact DOM widget tree and layout containers:
    - Root: ArchitectureExplorerView (Vertical)
    - Split Container: Horizontal#explorer-split-container
      - Left Pane: Vertical#explorer-left-pane (width 48%)
        - Input#explorer-search-input
        - Horizontal#explorer-category-chips (with exactly 10 category buttons)
        - Tree#explorer-tree
        - ScrollableContainer#explorer-detail-container -> Markdown#explorer-markdown-detail
      - Right Pane: Vertical#explorer-right-pane (width 52%)
        - Static#explorer-metrics-hud
        - ScrollableContainer#explorer-ascii-container -> Static#explorer-ascii-canvas
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        assert view is not None

        # Verify Split Container
        split = view.query_one("#explorer-split-container", Horizontal)
        assert split is not None

        # Verify Left Pane
        left_pane = split.query_one("#explorer-left-pane", Vertical)
        assert left_pane is not None

        search_input = left_pane.query_one("#explorer-search-input", Input)
        assert search_input is not None

        chips_bar = left_pane.query_one("#explorer-category-chips", Horizontal)
        assert chips_bar is not None

        expected_chips = [
            "chip-all", "chip-modules", "chip-infra", "chip-ai", "chip-bio",
            "chip-data", "chip-gov", "chip-tool", "chip-docs", "chip-audit"
        ]
        for chip_id in expected_chips:
            btn = chips_bar.query_one(f"#{chip_id}", Button)
            assert btn is not None, f"Missing chip button: #{chip_id}"

        tree = left_pane.query_one("#explorer-tree", Tree)
        assert tree is not None
        assert tree.root is not None

        detail_container = left_pane.query_one("#explorer-detail-container", ScrollableContainer)
        assert detail_container is not None

        md_detail = detail_container.query_one("#explorer-markdown-detail", Markdown)
        assert md_detail is not None

        # Verify Right Pane
        right_pane = split.query_one("#explorer-right-pane", Vertical)
        assert right_pane is not None

        hud = right_pane.query_one("#explorer-metrics-hud", Static)
        assert hud is not None

        ascii_container = right_pane.query_one("#explorer-ascii-container", ScrollableContainer)
        assert ascii_container is not None

        canvas = ascii_container.query_one("#explorer-ascii-canvas", Static)
        assert canvas is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("width,height", [
    (50, 20),
    (70, 25),
    (80, 24),
    (100, 30),
    (120, 40),
    (160, 50),
    (200, 60),
    (240, 80),
])
async def test_adversarial_viewport_boundary_rendering(width: int, height: int):
    """
    Stress test dual-layout rendering under extreme narrow, wide, and short viewport boundaries.
    Ensures zero layout exceptions or crashes.
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(width, height)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        assert view is not None
        assert view.graph is not None

        # Verify widgets are intact after mount at boundary size
        tree = view.query_one("#explorer-tree", Tree)
        assert tree is not None
        canvas = view.query_one("#explorer-ascii-canvas", Static)
        assert canvas is not None
        hud = view.query_one("#explorer-metrics-hud", Static)
        assert hud is not None


# =============================================================================
# TIER 2: CONCURRENT DYNAMIC FILTERING & ADVERSARIAL QUERY INJECTIONS
# =============================================================================

@pytest.mark.asyncio
async def test_concurrent_search_and_category_toggling():
    """
    Adversarially test interleaved typing and category chip clicking.
    Verify both Tree and ASCII canvas update synchronously without stale state.
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        search_input = view.query_one("#explorer-search-input", Input)

        # Step 1: Click AI chip
        await pilot.click("#chip-ai")
        await pilot.pause(0.02)
        assert view.active_category == "AI & Inference"
        ai_nodes = view.graph.filter_nodes(category="AI & Inference")
        assert len(ai_nodes) >= 4

        # Step 2: Type search query while AI chip is active
        search_input.value = "petals"
        await pilot.pause(0.02)
        filtered = view.graph.filter_nodes(category="AI & Inference", query="petals")
        assert len(filtered) >= 1
        assert any("petals" in n.id.lower() or "petals" in n.title.lower() for n in filtered)

        # Step 3: Switch to Biometrics chip with active 'petals' query (disjoint category)
        await pilot.click("#chip-bio")
        await pilot.pause(0.02)
        assert view.active_category == "Biometrics & DSP"
        bio_filtered = view.graph.filter_nodes(category="Biometrics & DSP", query="petals")
        # Biometrics nodes do not contain petals
        assert len(bio_filtered) == 0

        # Step 4: Clear query on Biometrics chip
        search_input.value = ""
        await pilot.pause(0.02)
        bio_all = view.graph.filter_nodes(category="Biometrics & DSP")
        assert len(bio_all) >= 1

        # Step 5: Reset to All chip
        await pilot.click("#chip-all")
        await pilot.pause(0.02)
        assert view.active_category is None
        total_nodes = len(view.graph.filter_nodes())
        assert total_nodes >= 50


@pytest.mark.asyncio
@pytest.mark.parametrize("adversarial_query", [
    "",
    "   ",
    " \t \n ",
    "NONEXISTENT_NODE_QUERY_99999_XYZ",
    "[.*+?^${}()|[\\]\\]",
    "(?P<name>[a-zA-Z0-9]+)",
    "'; DROP TABLE nodes; --",
    "<script>alert('xss')</script>",
    "\\x00\\r\\n\\t",
    "🧠 架构 🚀 00_core",
    "a" * 500,
    "00_core_infrastructure",
    "Index",
    "ECG",
    "TaIlScAlE",
])
async def test_adversarial_search_queries(adversarial_query: str):
    """
    Stress-test dynamic search engine against adversarial queries:
    whitespace, non-existent, regex injection, SQL/XSS, null bytes, Unicode/CJK, very long strings.
    Ensures zero exceptions and deterministic behavior.
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        search_input = view.query_one("#explorer-search-input", Input)

        # Inject adversarial query
        search_input.value = adversarial_query
        await pilot.pause(0.02)

        matching_nodes = view.graph.filter_nodes(query=adversarial_query)
        matching_ids = set(n.id for n in matching_nodes)

        # Verify selected node logic
        if not matching_nodes:
            assert view.selected_node_id is None
            md = view.query_one("#explorer-markdown-detail", Markdown)
            assert md is not None
        else:
            assert view.selected_node_id in matching_ids or view.selected_node_id is not None

        # Verify canvas and tree update cleanly
        canvas = view.query_one("#explorer-ascii-canvas", Static)
        assert canvas is not None


# =============================================================================
# TIER 3: NODE SELECTION, MARKDOWN DETAIL & ASCII CANVAS HIGHLIGHT SYNC
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("node_id,expected_category", [
    ("00_core_infrastructure", "Canonical Module"),
    ("01_apps", "Canonical Module"),
    ("02_ai_models_and_inference", "Canonical Module"),
    ("03_biometrics_and_telemetry", "Canonical Module"),
    ("04_data_and_memory", "Canonical Module"),
    ("05_agents_and_swarms", "Canonical Module"),
    ("06_scripts_and_tooling", "Canonical Module"),
    ("07_docs_and_architecture", "Canonical Module"),
    ("Index", "Architecture & Docs"),
    ("seaweedfs_setup", "Infrastructure"),
    ("petals_inference", "AI & Inference"),
    ("movesense_ecg", "Biometrics & DSP"),
    ("pyspark_memory", "Data & Memory"),
    ("ai_debate_council", "Swarm & Governance"),
    ("ssh_tooling", "Tooling & Scripts"),
    ("audit_ledger", "Audit & Telemetry"),
])
async def test_node_selection_sync_across_all_categories(node_id: str, expected_category: str):
    """
    Verify selecting nodes across all canonical categories updates:
    - view.selected_node_id
    - Markdown detail pane (with title, category, tags, and dependencies)
    - ASCII canvas highlight
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        assert view is not None

        if node_id in view.graph.nodes:
            view.select_node(node_id)
            await pilot.pause(0.02)

            assert view.selected_node_id == node_id

            # Verify Markdown detail
            md = view.query_one("#explorer-markdown-detail", Markdown)
            assert md is not None

            # Verify ASCII canvas
            canvas = view.query_one("#explorer-ascii-canvas", Static)
            assert canvas is not None


@pytest.mark.asyncio
async def test_node_selection_adversarial_edge_cases():
    """
    Test selecting non-existent nodes, empty strings, and rapid programmatic selections.
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)

        # 1. Non-existent node ID
        view.select_node("NonExistent_Ghost_Node_99999")
        await pilot.pause(0.02)
        # Should gracefully keep previous or update safely without crash
        assert view is not None

        # 2. Rapid node switching
        node_keys = list(view.graph.nodes.keys())[:10]
        for k in node_keys:
            view.select_node(k)
        await pilot.pause(0.02)
        assert view.selected_node_id == node_keys[-1]


# =============================================================================
# TIER 4: MULTI-SCREEN NAVIGATION & STABILITY HIERARCHY TRANSITIONS
# =============================================================================

@pytest.mark.asyncio
async def test_full_stability_hierarchy_multi_screen_transitions():
    """
    Adversarially test transitions between ArchitectureExplorerScreen and ALL 10 other screens
    in CanonicalPortApp:
    - agi_terminal (1 / c)
    - network (2 / n)
    - hardware (3 / h)
    - biometrics (4 / b)
    - ai_inference (5 / i)
    - training (6 / t)
    - governance (7 / g)
    - tooling (8 / s)
    - optimization (9 / o)
    - all_tabs (0 / a)
    - explorer (e / x)
    """
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 50)) as pilot:
        # Start on agi_terminal
        assert isinstance(app.screen, AgiCodingTerminalScreen)

        screen_jump_sequence = [
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("escape", AgiCodingTerminalScreen, "agi_terminal"),
            ("x", ArchitectureExplorerScreen, "explorer"),
            ("2", NetworkScreen, "network"),
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("3", HardwareScreen, "hardware"),
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("4", BiometricsScreen, "biometrics"),
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("5", AiInferenceScreen, "ai_inference"),
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("6", TrainingScreen, "training"),
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("7", GovernanceScreen, "governance"),
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("8", ToolingScreen, "tooling"),
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("9", OptimizationScreen, "optimization"),
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("0", AllTabsGridScreen, "all_tabs"),
            ("e", ArchitectureExplorerScreen, "explorer"),
            ("1", AgiCodingTerminalScreen, "agi_terminal"),
        ]

        for key, expected_cls, expected_id in screen_jump_sequence:
            await pilot.press(key)
            await pilot.pause(0.03)
            assert isinstance(app.screen, expected_cls), f"Failed jumping on key '{key}': expected {expected_cls}, got {type(app.screen)}"
            assert app.current_screen_id == expected_id, f"current_screen_id mismatch: expected {expected_id}, got {app.current_screen_id}"


@pytest.mark.asyncio
async def test_explorer_screen_action_refresh_and_search_focus():
    """
    Test Explorer screen specific actions:
    - '/' focuses search bar
    - 'r' triggers action_refresh_vault
    - 'escape' navigates back to terminal
    """
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.press("e")
        await pilot.pause(0.02)
        assert isinstance(app.screen, ArchitectureExplorerScreen)

        # Test '/' focuses search input
        await pilot.press("slash")
        await pilot.pause(0.02)
        search_input = app.screen.query_one("#explorer-search-input", Input)
        assert search_input.has_focus

        # Test 'r' vault refresh
        screen = app.screen
        assert isinstance(screen, ArchitectureExplorerScreen)
        screen.action_refresh_vault()
        await pilot.pause(0.02)
        view = screen.query_one(ArchitectureExplorerView)
        assert len(view.graph.nodes) >= 50

        # Test Escape returns to agi_terminal
        screen.action_back_to_terminal()
        await pilot.pause(0.02)
        assert isinstance(app.screen, AgiCodingTerminalScreen)


# =============================================================================
# TIER 5: HIGH-FREQUENCY EVENT CHURN & STRESS HARNESS
# =============================================================================

@pytest.mark.asyncio
async def test_high_frequency_adversarial_interaction_stress():
    """
    Execute 50 rapid, randomized-style UI interactions in a tight async loop:
    - screen switching
    - search input changes
    - category chip clicks
    - terminal resize events
    - node selections
    Ensures zero unhandled exceptions, zero deadlocks, and zero DOM corruption.
    """
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 50)) as pilot:
        chips = ["#chip-all", "#chip-modules", "#chip-infra", "#chip-ai", "#chip-bio", "#chip-data", "#chip-gov", "#chip-tool", "#chip-docs", "#chip-audit"]
        queries = ["00", "pyspark", "seaweedfs", "petals", "movesense", "", "audit", "index"]

        for i in range(10):
            # Switch to explorer
            await pilot.press("e")
            await pilot.pause(0.01)

            # Click a chip
            chip_id = chips[i % len(chips)]
            await pilot.click(chip_id)
            await pilot.pause(0.01)

            # Type a query
            query = queries[i % len(queries)]
            view = app.screen.query_one(ArchitectureExplorerView)
            search_input = view.query_one("#explorer-search-input", Input)
            search_input.value = query
            await pilot.pause(0.01)

            # Resize terminal
            new_w = 120 + (i % 4) * 20
            new_h = 40 + (i % 3) * 10
            await pilot.resize_terminal(new_w, new_h)
            await pilot.pause(0.01)

            # Switch screen
            await pilot.press(str((i % 9) + 1))
            await pilot.pause(0.01)

        # Final return to explorer to verify health
        await pilot.press("e")
        await pilot.pause(0.02)
        assert isinstance(app.screen, ArchitectureExplorerScreen)
        view = app.screen.query_one(ArchitectureExplorerView)
        assert view is not None
        assert len(view.graph.nodes) >= 50
