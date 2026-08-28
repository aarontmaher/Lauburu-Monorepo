"""
Canonical Port TUI - Architecture Explorer Screen
Version: 1.0.0-CANONICAL
Screen wrapper mounting ArchitectureExplorerView with Pinned Navigation Bar,
Docked Shortcuts Legend, and keyboard bindings (Escape to back, '/' to search, 'r' to reload).
"""

import os
import sys
from pathlib import Path
from typing import Optional
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input
from textual.binding import Binding

# Ensure tui package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from views.architecture_explorer_view import ArchitectureExplorerView
    from widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from widgets.docked_shortcuts_legend import DockedShortcutsLegend
except ImportError:
    from tui.views.architecture_explorer_view import ArchitectureExplorerView
    from tui.widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from tui.widgets.docked_shortcuts_legend import DockedShortcutsLegend


class ArchitectureExplorerScreen(Screen):
    """
    Dedicated Architecture Explorer Screen.
    Surfaces the Obsidian Knowledge Vault dual-layout explorer.
    """

    BINDINGS = [
        Binding("escape", "back_to_terminal", "Back"),
        Binding("slash", "focus_filter", "Search"),
        Binding("r", "refresh_vault", "Refresh"),
        Binding("c", "show_agi_terminal", "AGI Terminal"),
        Binding("1", "show_agi_terminal", "AGI Terminal"),
    ]

    def __init__(self, vault_path: Optional[Path] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vault_path = vault_path

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield PinnedTabNavBar(active_screen="explorer")
        yield ArchitectureExplorerView(vault_path=self.vault_path, id="architecture-explorer-view")
        yield DockedShortcutsLegend(active_screen="explorer")
        yield Footer()

    def on_mount(self) -> None:
        self._focus_default()

    def on_screen_resume(self) -> None:
        self._focus_default()

    def _focus_default(self) -> None:
        try:
            view = self.query_one(ArchitectureExplorerView)
            if view:
                tree = view.query_one("#explorer-tree")
                if tree:
                    tree.focus()
        except Exception:
            pass

    def action_focus_filter(self) -> None:
        """Focus search input field."""
        try:
            inp = self.query_one("#explorer-search-input", Input)
            if inp:
                inp.focus()
        except Exception:
            pass

    def action_refresh_vault(self) -> None:
        """Reload and refresh the Obsidian vault graph."""
        try:
            view = self.query_one(ArchitectureExplorerView)
            if view:
                view.reload_vault()
                self.notify("Reloaded Obsidian Architecture Vault", title="VAULT REFRESH")
        except Exception:
            pass

    def action_back_to_terminal(self) -> None:
        """Navigate back to home AGI coding terminal screen."""
        if hasattr(self.app, "switch_screen"):
            self.app.switch_screen("agi_terminal")
        elif hasattr(self.app, "pop_screen"):
            self.app.pop_screen()

    def action_show_agi_terminal(self) -> None:
        if hasattr(self.app, "switch_screen"):
            self.app.switch_screen("agi_terminal")

    def refresh_views(self) -> None:
        """Called by app-level refresh actions."""
        self.action_refresh_vault()
