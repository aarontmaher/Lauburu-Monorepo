"""
Canonical Port TUI - Pinned Tab Navigation Bar Widget
Version: 3.0.0-CANONICAL
Permanently docked at the top of all 9 screens, displaying high-contrast
tab items with explicit keybindings ([1]..[9], [<] Prev, [>] Next) locked in place
during extreme vertical scrolling of panes or terminal logs.
"""

from typing import List, Tuple, Optional
from textual.widgets import Static
from textual import events
from rich.text import Text


class PinnedTabNavBar(Static):
    """
    Pinned, always-visible Tab Navigation Bar Widget (Requirements R1, R2, R3).
    Structurally placed as a fixed top bar across all 9 canonical stability hierarchy screens.
    Explicitly renders keybindings in tab titles:
    [<] Prev │ [1] AGI Term │ [2] Network │ [3] Hardware │ [4] Biometrics │ [5] Inference │ [6] Training │ [7] Governance │ [8] Tooling │ [9] Optimization │ [>] Next
    """

    DEFAULT_CSS = """
    PinnedTabNavBar {
        height: 1;
        background: #0b111c;
        color: #94a3b8;
        content-align: center middle;
    }
    """

    NAV_TABS: List[Tuple[str, str, str, str]] = [
        ("1", "AGI Term", "#00ffcc", "agi_terminal"),
        ("2", "Network", "#00ffff", "network"),
        ("3", "Hardware", "#38bdf8", "hardware"),
        ("4", "Biometrics", "#4ade80", "biometrics"),
        ("5", "Inference", "#e879f9", "ai_inference"),
        ("6", "Training", "#facc15", "training"),
        ("7", "Governance", "#f43f5e", "governance"),
        ("8", "Tooling", "#a78bfa", "tooling"),
        ("9", "Optimization", "#38bdf8", "optimization"),
    ]

    NAV_TABS_COMPACT: List[Tuple[str, str, str, str]] = [
        ("1", "AGI", "#00ffcc", "agi_terminal"),
        ("2", "Net", "#00ffff", "network"),
        ("3", "HW", "#38bdf8", "hardware"),
        ("4", "Bio", "#4ade80", "biometrics"),
        ("5", "Inf", "#e879f9", "ai_inference"),
        ("6", "Train", "#facc15", "training"),
        ("7", "Gov", "#f43f5e", "governance"),
        ("8", "Tool", "#a78bfa", "tooling"),
        ("9", "Opt", "#38bdf8", "optimization"),
    ]

    NAV_TABS_TINY: List[Tuple[str, str, str, str]] = [
        ("1", "AGI", "#00ffcc", "agi_terminal"),
        ("2", "Net", "#00ffff", "network"),
        ("3", "HW", "#38bdf8", "hardware"),
        ("4", "Bio", "#4ade80", "biometrics"),
        ("5", "Inf", "#e879f9", "ai_inference"),
        ("6", "Trn", "#facc15", "training"),
        ("7", "Gov", "#f43f5e", "governance"),
        ("8", "Tol", "#a78bfa", "tooling"),
        ("9", "Opt", "#38bdf8", "optimization"),
    ]

    NAV_TABS_MICRO: List[Tuple[str, str, str, str]] = [
        ("1", "A", "#00ffcc", "agi_terminal"),
        ("2", "N", "#00ffff", "network"),
        ("3", "H", "#38bdf8", "hardware"),
        ("4", "B", "#4ade80", "biometrics"),
        ("5", "I", "#e879f9", "ai_inference"),
        ("6", "T", "#facc15", "training"),
        ("7", "G", "#f43f5e", "governance"),
        ("8", "S", "#a78bfa", "tooling"),
        ("9", "O", "#38bdf8", "optimization"),
    ]

    def __init__(self, active_screen: str = "agi_terminal", id: str = "pinned-tab-nav-bar", classes: str = "") -> None:
        super().__init__(id=id, classes=classes)
        self.active_screen = active_screen
        self._click_regions: List[Tuple[int, int, str]] = []
        self._last_text_len: int = 0

    def on_mount(self) -> None:
        self.update_nav(self.active_screen)

    def on_resize(self, event: events.Resize) -> None:
        """Dynamically re-render responsive tab bar on viewport dimension changes."""
        self.update_nav(self.active_screen)

    def set_active_screen(self, screen_name: str) -> None:
        """Update active tab and re-render visual state instantaneously."""
        self.active_screen = screen_name
        self.update_nav(screen_name)

    def build_nav_text(self, active_screen: str = "", width: Optional[int] = None) -> Text:
        """
        Build Rich Text representation of pinned navigation tabs with visible keybindings.
        Supports responsive width formatting:
        - width >= 165 or unspecified (None): Full canonical labels (161 cols)
        - 115 <= width < 165: Standard compact labels (111 cols)
        - 70 <= width < 115: High-density compact labels (69 cols)
        - 67 <= width < 70: Ultra-compact labels (67 cols)
        - 50 <= width < 67: Micro labels (50 cols)
        - width < 50: Nano labels (33 cols)
        Active tab is highlighted with bold reverse background matching layer color.
        """
        target = active_screen or self.active_screen or "agi_terminal"
        text = Text()
        self._click_regions = []
        pos = 0

        # Determine effective width
        eff_width = width
        if eff_width is None:
            eff_width = 180  # Default to full canonical mode when width is not specified

        if eff_width < 50:
            # Nano mode (<50 cols, 33 chars)
            prev_str = "[<]"
            text.append(prev_str, style="bold #94a3b8")
            self._click_regions.append((pos, pos + len(prev_str), "prev"))
            pos += len(prev_str)

            for key, _, col, sid in self.NAV_TABS_MICRO:
                is_active = (target == sid)
                tab_str = f"[{key}]"
                tab_len = len(tab_str)
                if is_active:
                    text.append(tab_str, style=f"bold {col} reverse")
                else:
                    text.append(tab_str, style=f"bold {col}")
                self._click_regions.append((pos, pos + tab_len, sid))
                pos += tab_len

            next_str = "[>]"
            text.append(next_str, style="bold #94a3b8")
            self._click_regions.append((pos, pos + len(next_str), "next"))
            pos += len(next_str)

        elif eff_width < 67:
            # Micro mode (50-66 cols, 50 chars)
            prev_str = "[<]"
            text.append(prev_str, style="bold #94a3b8")
            self._click_regions.append((pos, pos + len(prev_str), "prev"))
            pos += len(prev_str)

            for i, (key, label, col, sid) in enumerate(self.NAV_TABS_MICRO):
                is_active = (target == sid)
                tab_str = f"[{key}]{label}"
                tab_len = len(tab_str)

                if is_active:
                    text.append(f"[{key}]", style=f"bold {col} reverse")
                    text.append(f"{label}", style="bold white reverse")
                else:
                    text.append(f"[{key}]", style=f"bold {col}")
                    text.append(f"{label}", style="white")

                self._click_regions.append((pos, pos + tab_len, sid))
                pos += tab_len

                if i < len(self.NAV_TABS_MICRO) - 1:
                    text.append(" ", style="dim #334155")
                    pos += 1

            next_str = "[>]"
            text.append(next_str, style="bold #94a3b8")
            self._click_regions.append((pos, pos + len(next_str), "next"))
            pos += len(next_str)

        elif eff_width < 70:
            # Ultra-compact mode (67-69 cols, 67 chars)
            prev_str = "[<]"
            text.append("[<]", style="bold #94a3b8")
            self._click_regions.append((pos, pos + len(prev_str), "prev"))
            pos += len(prev_str)

            for i, (key, label, col, sid) in enumerate(self.NAV_TABS_TINY):
                is_active = (target == sid)
                tab_str = f"[{key}]{label}"
                tab_len = len(tab_str)

                if is_active:
                    text.append(f"[{key}]", style=f"bold {col} reverse")
                    text.append(f"{label}", style="bold white reverse")
                else:
                    text.append(f"[{key}]", style=f"bold {col}")
                    text.append(f"{label}", style="white")

                self._click_regions.append((pos, pos + tab_len, sid))
                pos += tab_len

                if i < len(self.NAV_TABS_TINY) - 1:
                    text.append(" ", style="dim #334155")
                    pos += 1

            next_str = "[>]"
            text.append("[>]", style="bold #94a3b8")
            self._click_regions.append((pos, pos + len(next_str), "next"))
            pos += len(next_str)

        elif eff_width < 115:
            # High-density compact mode (70-114 cols, e.g. standard 80-col terminal, 69 chars)
            prev_str = "[<]"
            text.append("[<]", style="bold #94a3b8")
            self._click_regions.append((pos, pos + len(prev_str), "prev"))
            pos += len(prev_str)

            text.append(" ", style="dim #334155")
            pos += 1

            for i, (key, label, col, sid) in enumerate(self.NAV_TABS_TINY):
                is_active = (target == sid)
                tab_str = f"[{key}]{label}"
                tab_len = len(tab_str)

                if is_active:
                    text.append(f"[{key}]", style=f"bold {col} reverse")
                    text.append(f"{label}", style="bold white reverse")
                else:
                    text.append(f"[{key}]", style=f"bold {col}")
                    text.append(f"{label}", style="white")

                self._click_regions.append((pos, pos + tab_len, sid))
                pos += tab_len

                if i < len(self.NAV_TABS_TINY) - 1:
                    text.append(" ", style="dim #334155")
                    pos += 1

            text.append(" ", style="dim #334155")
            pos += 1

            next_str = "[>]"
            text.append("[>]", style="bold #94a3b8")
            self._click_regions.append((pos, pos + len(next_str), "next"))
            pos += len(next_str)

        elif eff_width < 165:
            # Standard compact mode (115-164 cols, 111 chars)
            prev_str = "[<] Prev"
            text.append("[<]", style="bold #94a3b8")
            text.append(" Prev", style="#94a3b8")
            self._click_regions.append((pos, pos + len(prev_str), "prev"))
            pos += len(prev_str)

            text.append(" │ ", style="dim #334155")
            pos += 3

            for i, (key, label, col, sid) in enumerate(self.NAV_TABS_COMPACT):
                is_active = (target == sid)
                tab_str = f"[{key}] {label}"
                tab_len = len(tab_str)

                if is_active:
                    text.append(f"[{key}]", style=f"bold {col} reverse")
                    text.append(f" {label}", style="bold white reverse")
                else:
                    text.append(f"[{key}]", style=f"bold {col}")
                    text.append(f" {label}", style="white")

                self._click_regions.append((pos, pos + tab_len, sid))
                pos += tab_len

                if i < len(self.NAV_TABS_COMPACT) - 1:
                    text.append(" │ ", style="dim #334155")
                    pos += 3

            text.append(" │ ", style="dim #334155")
            pos += 3

            next_str = "[>] Next"
            text.append("[>]", style="bold #94a3b8")
            text.append(" Next", style="#94a3b8")
            self._click_regions.append((pos, pos + len(next_str), "next"))
            pos += len(next_str)

        else:
            # Full canonical mode (>=165 cols, 161 chars)
            prev_str = "[<] Prev"
            text.append("[<]", style="bold #94a3b8")
            text.append(" Prev", style="#94a3b8")
            self._click_regions.append((pos, pos + len(prev_str), "prev"))
            pos += len(prev_str)

            text.append(" │ ", style="dim #334155")
            pos += 3

            for i, (key, label, col, sid) in enumerate(self.NAV_TABS):
                is_active = (target == sid)
                tab_str = f"[{key}] {label}"
                tab_len = len(tab_str)

                if is_active:
                    text.append(f"[{key}]", style=f"bold {col} reverse")
                    text.append(f" {label}", style="bold white reverse")
                else:
                    text.append(f"[{key}]", style=f"bold {col}")
                    text.append(f" {label}", style="white")

                self._click_regions.append((pos, pos + tab_len, sid))
                pos += tab_len

                if i < len(self.NAV_TABS) - 1:
                    text.append(" │ ", style="dim #334155")
                    pos += 3

            text.append(" │ ", style="dim #334155")
            pos += 3

            next_str = "[>] Next"
            text.append("[>]", style="bold #94a3b8")
            text.append(" Next", style="#94a3b8")
            self._click_regions.append((pos, pos + len(next_str), "next"))
            pos += len(next_str)

        self._last_text_len = len(text.plain)
        return text

    def update_nav(self, active_screen: str = "") -> None:
        """Refresh rendered tab bar text taking current widget width into account."""
        target = active_screen or self.active_screen
        w = getattr(self, "_mock_size", None) or getattr(self, "size", None)
        width_val = w.width if (w and w.width > 0) else None
        rich_text = self.build_nav_text(target, width=width_val)
        try:
            self.update(rich_text)
        except Exception:
            pass

    def _dispatch_action(self, action_or_screen: str) -> None:
        """Dispatch screen switch or prev/next cycling action to app."""
        try:
            app_inst = getattr(self, "_mock_app", None) or self.app
        except Exception:
            return

        if action_or_screen == "prev":
            if hasattr(app_inst, "action_prev_screen"):
                app_inst.action_prev_screen()
            elif hasattr(app_inst, "cycle_screen"):
                app_inst.cycle_screen(-1, force=True)
        elif action_or_screen == "next":
            if hasattr(app_inst, "action_next_screen"):
                app_inst.action_next_screen()
            elif hasattr(app_inst, "cycle_screen"):
                app_inst.cycle_screen(1, force=True)
        else:
            if hasattr(app_inst, "switch_screen"):
                app_inst.switch_screen(action_or_screen)

    def on_click(self, event: events.Click) -> None:
        """
        Handle mouse click on tabs or prev/next controls with centered offset compensation.
        Uses exact half-open interval hit testing [start_x, end_x) to prevent boundary collision.
        """
        click_x = event.x
        w = getattr(self, "_mock_size", None) or getattr(self, "size", None)
        widget_w = w.width if (w and w.width > 0) else 0
        text_len = getattr(self, "_last_text_len", 0)
        start_offset = max(0, (widget_w - text_len) // 2) if (widget_w > text_len and text_len > 0) else 0
        relative_x = click_x - start_offset

        # Check adjusted relative coordinate (visual click position) with half-open interval [start_x, end_x)
        for start_x, end_x, action_or_screen in self._click_regions:
            if start_x <= relative_x < end_x:
                self._dispatch_action(action_or_screen)
                break

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        """Mouse scroll down directly on the navbar cycles forward to the next screen/tab."""
        self._dispatch_action("next")

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        """Mouse scroll up directly on the navbar cycles backward to the previous screen/tab."""
        self._dispatch_action("prev")
