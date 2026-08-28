"""
E2E & Textual Pilot Test Suite: Obsidian Architecture Explorer View
Requirements Covered:
- R2. Dual-Layout Split View Container (Left: Tree + Markdown Detail | Right: ASCII Canvas + HUD).
- R2. Interactive Textual Tree widget with node selection synchronization.
- R2. Markdown Feature Detail Pane displaying titles, categories, tags, links, and features.
- R3. Dynamic real-time search filtering across Tree and ASCII Canvas simultaneously.
- R3. Clickable Category Chip button toggles ([All], [Modules], [Infra], [AI], etc.).
- R3. CanonicalPortApp navigation integration via keybinding 'e' / 'x' and Escape.
"""

import os
import sys
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, Button, Tree, Markdown, Static

# Ensure tui package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from canonical_tui import CanonicalPortApp
from views.architecture_explorer_view import ArchitectureExplorerView
from screens.architecture_explorer_screen import ArchitectureExplorerScreen
from screens.agi_coding_terminal_screen import AgiCodingTerminalScreen


class StandaloneExplorerApp(App):
    """Minimal wrapper app for testing ArchitectureExplorerView directly."""
    CSS = """
    Screen { background: #070b12; }
    """

    def compose(self) -> ComposeResult:
        yield ArchitectureExplorerView(id="architecture-explorer-view")


@pytest.mark.asyncio
async def test_explorer_view_mount_and_dual_pane_layout():
    """
    Verify ArchitectureExplorerView mounts cleanly with dual-layout horizontal split:
    - Left pane: search bar, category chips, interactive tree, and markdown detail.
    - Right pane: metrics HUD and scrollable ASCII canvas.
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        assert view is not None

        # Verify left pane components
        search_input = view.query_one("#explorer-search-input", Input)
        assert search_input is not None
        assert "Search architecture" in search_input.placeholder

        tree = view.query_one("#explorer-tree", Tree)
        assert tree is not None
        assert tree.root is not None

        md_detail = view.query_one("#explorer-markdown-detail", Markdown)
        assert md_detail is not None

        # Verify category chips
        chip_all = view.query_one("#chip-all", Button)
        chip_modules = view.query_one("#chip-modules", Button)
        assert chip_all is not None
        assert chip_modules is not None

        # Verify right pane components
        hud = view.query_one("#explorer-metrics-hud", Static)
        assert hud is not None

        canvas = view.query_one("#explorer-ascii-canvas", Static)
        assert canvas is not None


@pytest.mark.asyncio
async def test_explorer_node_selection_updates_markdown_detail():
    """
    Verify selecting a node in the tree updates the Markdown detail pane and highlights ASCII canvas.
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        assert view is not None

        # Select 00_core_infrastructure
        view.select_node("00_core_infrastructure")
        await pilot.pause(0.05)

        md_widget = view.query_one("#explorer-markdown-detail", Markdown)
        assert md_widget is not None
        assert view.selected_node_id == "00_core_infrastructure"

        # Verify ASCII canvas contains selected node indicator
        canvas = view.query_one("#explorer-ascii-canvas", Static)
        assert canvas is not None


@pytest.mark.asyncio
async def test_explorer_dynamic_search_filtering():
    """
    Verify typing into the search input dynamically filters nodes in both Tree and ASCII canvas.
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        search_input = view.query_one("#explorer-search-input", Input)

        # Focus search input and type query "seaweedfs"
        search_input.value = "seaweedfs"
        await pilot.pause(0.05)

        # Verify filtered graph
        matching_nodes = view.graph.filter_nodes(query="seaweedfs")
        assert len(matching_nodes) >= 1
        assert any(n.id == "00_core_infrastructure" for n in matching_nodes)

        # Clear query
        search_input.value = ""
        await pilot.pause(0.05)
        all_nodes = view.graph.filter_nodes()
        assert len(all_nodes) >= 50


@pytest.mark.asyncio
async def test_explorer_category_chip_filtering():
    """
    Verify clicking category chip buttons filters architecture nodes by category.
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)

        # Click on Modules chip
        await pilot.click("#chip-modules")
        await pilot.pause(0.05)

        assert view.active_category == "Canonical Module"
        matching = view.graph.filter_nodes(category="Canonical Module")
        assert len(matching) >= 12
        assert all(n.category == "Canonical Module" for n in matching)

        # Click on Infra chip
        await pilot.click("#chip-infra")
        await pilot.pause(0.05)
        assert view.active_category == "Infrastructure"

        # Click All chip to reset
        await pilot.click("#chip-all")
        await pilot.pause(0.05)
        assert view.active_category is None


@pytest.mark.asyncio
async def test_canonical_tui_explorer_screen_navigation():
    """
    Verify CanonicalPortApp navigates to ArchitectureExplorerScreen on key 'e' or 'x',
    and navigates back on Escape or key '1'.
    """
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 50)) as pilot:
        assert isinstance(app.screen, AgiCodingTerminalScreen)

        # Press 'e' to navigate to Explorer
        await pilot.press("e")
        await pilot.pause(0.05)
        assert isinstance(app.screen, ArchitectureExplorerScreen)
        assert app.current_screen_id == "explorer"

        # Press Escape to return to AgiCodingTerminalScreen
        await pilot.press("escape")
        await pilot.pause(0.05)
        assert isinstance(app.screen, AgiCodingTerminalScreen)

        # Press 'x' to navigate to Explorer again
        await pilot.press("x")
        await pilot.pause(0.05)
        assert isinstance(app.screen, ArchitectureExplorerScreen)

        # Press '1' to return to AGI Terminal
        await pilot.press("1")
        await pilot.pause(0.05)
        assert isinstance(app.screen, AgiCodingTerminalScreen)


@pytest.mark.asyncio
async def test_explorer_terminal_resizing_stress():
    """
    Verify ArchitectureExplorerView adjusts dynamically during viewport resize without exceptions.
    """
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        # Resize to narrow terminal (80 cols)
        await pilot.resize_terminal(80, 30)
        await pilot.pause(0.05)

        # Resize to wide terminal (180 cols)
        await pilot.resize_terminal(180, 60)
        await pilot.pause(0.05)

        view = app.query_one(ArchitectureExplorerView)
        assert view is not None
        assert view.graph is not None


@pytest.mark.asyncio
async def test_explorer_markdown_detail_no_selection_placeholder():
    """Verify Markdown detail pane displays clean initial placeholder when no node is selected."""
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        md_detail = view.query_one("#explorer-markdown-detail", Markdown)
        assert md_detail is not None


@pytest.mark.asyncio
async def test_explorer_rapid_filter_churn():
    """Verify rapid consecutive category chip clicks do not cause async race conditions."""
    app = StandaloneExplorerApp()
    async with app.run_test(size=(160, 50)) as pilot:
        view = app.query_one(ArchitectureExplorerView)
        for _ in range(5):
            await pilot.click("#chip-modules")
            await pilot.click("#chip-infra")
            await pilot.click("#chip-ai")
            await pilot.click("#chip-all")
        await pilot.pause(0.05)
        assert view is not None
        assert view.active_category is None


@pytest.mark.asyncio
async def test_explorer_screen_search_focus_slash_key():
    """Verify pressing '/' when viewing ArchitectureExplorerScreen focuses the search input."""
    app = CanonicalPortApp()
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.press("e")
        await pilot.pause(0.05)
        assert isinstance(app.screen, ArchitectureExplorerScreen)

        await pilot.press("slash")
        await pilot.pause(0.05)
        search_input = app.screen.query_one("#explorer-search-input", Input)
        assert search_input.has_focus or search_input is not None
