"""
Canonical Port TUI - Commercialization & Capability Tier Screen
Version: 1.0.0-CANONICAL

Screen wrapper mounting the CommercializationUnlockWidget with Shopify/Stripe deep links.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer

try:
    from widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from widgets.canonical_header_bar import CanonicalHeaderBar
    from widgets.commercialization_unlock_widget import CommercializationUnlockWidget
except ImportError:
    from tui.widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from tui.widgets.canonical_header_bar import CanonicalHeaderBar
    from tui.widgets.commercialization_unlock_widget import CommercializationUnlockWidget


class CommercializationScreen(Screen):
    """
    Screen dedicated to commercialization, subscription tiers, and hardware capability unlocks.
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield CanonicalHeaderBar(id="canonical_header_bar")
        yield PinnedTabNavBar(active_tab="tooling", id="pinned_tab_nav_bar")
        with VerticalScroll():
            yield CommercializationUnlockWidget()
        yield Footer()
