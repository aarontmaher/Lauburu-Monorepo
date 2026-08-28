"""
Canonical Port TUI - Harmonized Screen 1: Swarm IDE & Chat Shell Screen
Version: 4.0.0-HARMONIZED
Wraps ChatIdeView with PinnedTabNavBar, DockedShortcutsLegend, and global bindings.
"""

import os
import sys
from typing import Optional
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer
from textual.binding import Binding

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from views.chat_ide_view import ChatIdeView
    from widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from widgets.docked_shortcuts_legend import DockedShortcutsLegend
    from widgets.canonical_header_bar import CanonicalHeaderBar, CanonicalEngineChanged
except ImportError:
    from tui.views.chat_ide_view import ChatIdeView
    from tui.widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from tui.widgets.docked_shortcuts_legend import DockedShortcutsLegend
    from tui.widgets.canonical_header_bar import CanonicalHeaderBar, CanonicalEngineChanged


class ChatIdeScreen(Screen):
    """
    Dedicated Harmonized Swarm IDE & Multi-Agent Chat Shell Screen (Screen 1 / 'c' / '1').
    """

    BINDINGS = [
        Binding("ctrl+e", "cycle_inference_engine", "Switch Engine", priority=True),
        Binding("f2", "cycle_inference_engine", "Switch Engine", priority=True),
        Binding("f5", "execute_code", "Run Code", priority=True),
        Binding("r", "refresh_views", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield PinnedTabNavBar(active_screen="agi_terminal")
        yield ChatIdeView(id="canonical-chat-ide-view")
        yield DockedShortcutsLegend(active_screen="agi_terminal")
        yield Footer()

    def action_cycle_inference_engine(self) -> None:
        """Cycle active engine."""
        try:
            view = self.query_one(ChatIdeView)
            if view:
                header = view.query_one(CanonicalHeaderBar)
                if header:
                    header.cycle_engine(1)
        except Exception:
            pass

    def action_execute_code(self) -> None:
        """Execute active code buffer."""
        try:
            view = self.query_one(ChatIdeView)
            if view:
                view._on_execute_code()
        except Exception:
            pass

    def refresh_views(self, force_refresh: bool = False) -> None:
        """Refresh screen views."""
        try:
            view = self.query_one(ChatIdeView)
            if view:
                view._tick_refresh()
        except Exception:
            pass
