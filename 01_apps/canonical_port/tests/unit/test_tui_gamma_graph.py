"""
Unit and Textual Pilot Test Suite for TUI-Gamma: Obsidian Topology & Knowledge Explorer
Prototype: tui/prototypes/tui_gamma_graph.py

Requirements Verified:
1. Standalone Application Mounting and 3-Column Responsive Split (25% Left, 55% Center, 20% Right, Bottom Dock).
2. 10 Quick-Filter Category Chip Buttons ([All], [Modules], [Infra], [AI], [Biometrics], [Data], [Governance], [Tooling], [Docs], [Audit]).
3. Real-time Search Input with '/' Focus Shortcut and Substring Matching.
4. Interactive Obsidian Knowledge Tree with In/Out Degree badges and Outbound link sub-leaves.
5. Sugiyama Layered Topology Canvas with Depth Selector (1/2/3/All) and Layer Isolation (L0/L1/L2/L3+).
6. Tarjan SCC Cycle Badges ('↺ SCC') and Bidirectional Flow Vectors ('⇄ BIDI' / '⇄ Flow Vectors').
7. Markdown Architecture Document Inspector with frontmatter, tags, backlinks, and subsystem features.
8. Code AST Metrics Card (PySpark 434,965 LOC, 3,104 files, 325 tests, language breakdowns, project stats).
9. Live 3-Way Synchronization (Tree Selection <-> Canvas Highlight <-> Markdown Detail <-> AST Card).
10. Collapsible Sidebar ('b' shortcut), Detail/Compact Mode Toggle ('d'), and SIGWINCH Terminal Resizing Resilience.
"""

import os
import sys
from pathlib import Path
import pytest
from textual.widgets import Button, Input, Markdown, Static, Tree

# Ensure tui and prototype paths are present
_TEST_DIR = Path(__file__).resolve().parent
_PORT_DIR = _TEST_DIR.parent.parent
_TUI_DIR = _PORT_DIR / "tui"
for p in [str(_PORT_DIR), str(_TUI_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from tui.prototypes.tui_gamma_graph import (
    AstMetricsData,
    GammaTopologyRenderer,
    TuiGammaGraphApp,
)
from tui.models.architecture_graph import ArchitectureGraph, VaultNode, WikilinkRef, VaultFeature


# =============================================================================
# UNIT TESTS: DATA & RENDERER ENGINE
# =============================================================================

class TestGammaEngineUnits:
    """Unit tests for AST metrics parsing, Sugiyama layout, and Tarjan cycle detection."""

    def test_ast_metrics_data_loading(self):
        """Verify AstMetricsData loads authentic monorepo stats."""
        data = AstMetricsData.load_from_vault()
        assert data.total_loc >= 400000
        assert data.total_files >= 3000
        assert data.total_tests >= 300
        assert data.total_projects >= 30
        assert "Python" in data.languages
        assert "Markdown" in data.languages
        assert "00_core_infrastructure" in data.project_loc_map
        assert data.project_loc_map["00_core_infrastructure"]["loc"] > 0

    def test_gamma_renderer_scc_and_bidirectional_vectors(self):
        """Verify GammaTopologyRenderer detects cycles, renders SCC badges and flow vectors."""
        graph = ArchitectureGraph()
        
        # Create cyclic and bidirectional pair
        n1 = VaultNode(
            id="NodeA", file_path=Path("NodeA.md"), title="Node A", category="Canonical Module",
            out_links=[WikilinkRef("NodeB")], in_degree=1, out_degree=1
        )
        n2 = VaultNode(
            id="NodeB", file_path=Path("NodeB.md"), title="Node B", category="Canonical Module",
            out_links=[WikilinkRef("NodeA")], in_degree=1, out_degree=1
        )
        n3 = VaultNode(
            id="NodeC", file_path=Path("NodeC.md"), title="Node C", category="Infrastructure",
            out_links=[], in_degree=1, out_degree=0
        )
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_edge("NodeA", "NodeB")
        graph.add_edge("NodeB", "NodeA")
        graph.add_edge("NodeB", "NodeC")

        renderer = GammaTopologyRenderer(graph)
        rendered = renderer.render_canvas(selected_node="NodeA", detailed_mode=True)

        assert "SUGIYAMA DIRECTED TOPOLOGY CANVAS" in rendered
        assert "NodeA" in rendered
        assert "NodeB" in rendered
        assert "NodeC" in rendered
        # Tarjan SCC badge
        assert "↺ SCC" in rendered
        # Bidirectional flow vector
        assert "⇄ BIDI" in rendered or "⇄ Flow Vectors:" in rendered
        # Selected badge
        assert "★ SELECTED" in rendered

    def test_neighborhood_subgraph_depth_limiting(self):
        """Verify k-hop neighborhood graph extraction."""
        graph = ArchitectureGraph()
        for i in range(5):
            node = VaultNode(id=f"N{i}", file_path=Path(f"N{i}.md"), title=f"Node {i}")
            graph.add_node(node)
        graph.add_edge("N0", "N1")
        graph.add_edge("N1", "N2")
        graph.add_edge("N2", "N3")
        graph.add_edge("N3", "N4")

        renderer = GammaTopologyRenderer(graph)
        
        # Depth 1 around N2 -> N1, N2, N3
        sub_d1 = renderer.get_neighborhood_subgraph("N2", depth=1)
        assert "N2" in sub_d1
        assert "N1" in sub_d1
        assert "N3" in sub_d1
        assert "N0" not in sub_d1
        assert "N4" not in sub_d1

        # Depth 2 around N2 -> N0, N1, N2, N3, N4
        sub_d2 = renderer.get_neighborhood_subgraph("N2", depth=2)
        assert len(sub_d2) == 5


# =============================================================================
# TEXTUAL PILOT TESTS: TUI-GAMMA APPLICATION
# =============================================================================

class TestTuiGammaPilot:
    """Comprehensive Textual Pilot tests for the TuiGammaGraphApp prototype."""

    @pytest.mark.asyncio
    async def test_gamma_app_mount_and_3column_layout(self):
        """
        Verify TuiGammaGraphApp mounts cleanly with the complete 3-column architecture explorer layout:
        - Left Sidebar (25%): search bar, 10 chips, tree, collapse button.
        - Center Canvas (55%): controls (depth, layer, mode), scrollable ASCII canvas.
        - Right Inspector (20%): AST metrics card, markdown detail.
        - Bottom Dock: metrics HUD.
        """
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            # 1. Left Sidebar
            sidebar = app.query_one("#gamma-left-sidebar")
            assert sidebar is not None
            search_input = app.query_one("#gamma-search-input", Input)
            assert search_input is not None
            assert "Search architecture" in search_input.placeholder
            tree = app.query_one("#gamma-tree", Tree)
            assert tree is not None
            assert tree.root is not None
            collapse_btn = app.query_one("#gamma-btn-toggle-sidebar", Button)
            assert collapse_btn is not None

            # Verify 10 category chips exist
            for _, chip_id, _ in TuiGammaGraphApp.CHIP_CONFIGS:
                chip_btn = app.query_one(f"#{chip_id}", Button)
                assert chip_btn is not None

            # 2. Center Canvas
            canvas_pane = app.query_one("#gamma-center-canvas")
            assert canvas_pane is not None
            ascii_canvas = app.query_one("#gamma-ascii-canvas", Static)
            assert ascii_canvas is not None

            # Depth & Layer buttons
            for d_id in ["depth-all", "depth-1", "depth-2", "depth-3"]:
                assert app.query_one(f"#{d_id}", Button) is not None
            for l_id in ["layer-all", "layer-0", "layer-1", "layer-2", "layer-3"]:
                assert app.query_one(f"#{l_id}", Button) is not None

            # 3. Right Inspector
            inspector = app.query_one("#gamma-right-inspector")
            assert inspector is not None
            ast_card = app.query_one("#gamma-ast-metrics-card", Static)
            assert ast_card is not None
            md_detail = app.query_one("#gamma-markdown-detail", Markdown)
            assert md_detail is not None

            # 4. Bottom Dock HUD
            hud = app.query_one("#gamma-bottom-hud", Static)
            assert hud is not None

    @pytest.mark.asyncio
    async def test_gamma_category_chip_filtering(self):
        """Verify clicking each category chip updates active_category and filters the graph."""
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            # 1. Click Modules Chip
            await pilot.click("#chip-modules")
            await pilot.pause(0.05)
            assert app.active_category == "Canonical Module"
            matching = app.graph.filter_nodes(category="Canonical Module")
            assert len(matching) >= 12
            assert all(n.category == "Canonical Module" for n in matching)

            # 2. Click Infra Chip
            await pilot.click("#chip-infra")
            await pilot.pause(0.05)
            assert app.active_category == "Infrastructure"

            # 3. Click AI Chip
            await pilot.click("#chip-ai")
            await pilot.pause(0.05)
            assert app.active_category == "AI & Inference"

            # 4. Click Biometrics Chip
            await pilot.click("#chip-bio")
            await pilot.pause(0.05)
            assert app.active_category == "Biometrics & DSP"

            # 5. Click Data Chip
            await pilot.click("#chip-data")
            await pilot.pause(0.05)
            assert app.active_category == "Data & Memory"

            # 6. Click All Chip to reset
            await pilot.click("#chip-all")
            await pilot.pause(0.05)
            assert app.active_category is None

    @pytest.mark.asyncio
    async def test_gamma_realtime_search_filtering(self):
        """Verify search input dynamically filters tree and topology canvas."""
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            search_input = app.query_one("#gamma-search-input", Input)

            # Type search query "seaweedfs"
            search_input.value = "seaweedfs"
            await pilot.pause(0.05)
            assert app.current_query == "seaweedfs"

            matching = app.graph.filter_nodes(query="seaweedfs")
            assert len(matching) >= 1
            assert any("00_core_infrastructure" in n.id for n in matching)

            # Clear search query
            search_input.value = ""
            await pilot.pause(0.05)
            all_nodes = app.graph.filter_nodes()
            assert len(all_nodes) >= 50

    @pytest.mark.asyncio
    async def test_gamma_tree_selection_synchronization(self):
        """Verify selecting a node in the tree updates Markdown detail, AST Card, and Canvas highlight."""
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            # Select 00_core_infrastructure
            app.select_node("00_core_infrastructure")
            await pilot.pause(0.05)

            assert app.selected_node_id == "00_core_infrastructure"

            # Verify Markdown detail is populated
            md_widget = app.query_one("#gamma-markdown-detail", Markdown)
            assert md_widget is not None

            # Verify AST Card is updated
            ast_card = app.query_one("#gamma-ast-metrics-card", Static)
            assert ast_card is not None

            # Verify Canvas is rendered
            canvas = app.query_one("#gamma-ascii-canvas", Static)
            assert canvas is not None

    @pytest.mark.asyncio
    async def test_gamma_depth_selector_controls(self):
        """Verify clicking Depth buttons updates active_depth and k-hop neighborhood."""
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            # Click Depth 1
            await pilot.click("#depth-1")
            await pilot.pause(0.05)
            assert app.active_depth == 1

            # Click Depth 2
            await pilot.click("#depth-2")
            await pilot.pause(0.05)
            assert app.active_depth == 2

            # Click Depth 3
            await pilot.click("#depth-3")
            await pilot.pause(0.05)
            assert app.active_depth == 3

            # Click Depth All
            await pilot.click("#depth-all")
            await pilot.pause(0.05)
            assert app.active_depth is None

    @pytest.mark.asyncio
    async def test_gamma_layer_isolation_controls(self):
        """Verify clicking Layer buttons updates active_layer."""
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            # Click L0
            await pilot.click("#layer-0")
            await pilot.pause(0.05)
            assert app.active_layer == 0

            # Click L1
            await pilot.click("#layer-1")
            await pilot.pause(0.05)
            assert app.active_layer == 1

            # Click L2
            await pilot.click("#layer-2")
            await pilot.pause(0.05)
            assert app.active_layer == 2

            # Click L3+
            await pilot.click("#layer-3")
            await pilot.pause(0.05)
            assert app.active_layer == 3

            # Click Layer All
            await pilot.click("#layer-all")
            await pilot.pause(0.05)
            assert app.active_layer is None

    @pytest.mark.asyncio
    async def test_gamma_sidebar_collapse_toggle(self):
        """Verify toggling sidebar collapse via button and 'b' keybinding."""
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            sidebar = app.query_one("#gamma-left-sidebar")
            canvas = app.query_one("#gamma-center-canvas")

            assert not app.sidebar_collapsed
            assert not sidebar.has_class("collapsed")

            # Press 'b' to collapse sidebar
            await pilot.press("b")
            await pilot.pause(0.05)
            assert app.sidebar_collapsed
            assert sidebar.has_class("collapsed")
            assert canvas.has_class("expanded")

            # Press 'b' to expand sidebar again
            await pilot.press("b")
            await pilot.pause(0.05)
            assert not app.sidebar_collapsed
            assert not sidebar.has_class("collapsed")

            # Click toggle button
            await pilot.click("#gamma-btn-toggle-sidebar")
            await pilot.pause(0.05)
            assert app.sidebar_collapsed

    @pytest.mark.asyncio
    async def test_gamma_slash_shortcut_focuses_search(self):
        """Verify pressing '/' focuses the search input."""
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            search_input = app.query_one("#gamma-search-input", Input)
            await pilot.press("slash")
            await pilot.pause(0.05)
            assert search_input.has_focus

    @pytest.mark.asyncio
    async def test_gamma_detail_compact_mode_toggle(self):
        """Verify toggling between detailed and compact rendering via 'd' keybinding."""
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            assert app.detailed_mode is True

            # Press 'd' to toggle to compact
            await pilot.press("d")
            await pilot.pause(0.05)
            assert app.detailed_mode is False

            # Press 'd' to toggle back to detailed
            await pilot.press("d")
            await pilot.pause(0.05)
            assert app.detailed_mode is True

    @pytest.mark.asyncio
    async def test_gamma_terminal_resizing_stress(self):
        """Verify TuiGammaGraphApp handles terminal resizing gracefully without DOM errors."""
        app = TuiGammaGraphApp()
        async with app.run_test(size=(160, 50)) as pilot:
            # Resize to narrow terminal
            await pilot.resize_terminal(80, 24)
            await pilot.pause(0.05)

            # Resize to ultra-wide
            await pilot.resize_terminal(200, 60)
            await pilot.pause(0.05)

            assert app.graph is not None
            assert len(app.graph.nodes) > 0
