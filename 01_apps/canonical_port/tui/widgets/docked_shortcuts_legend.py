"""
Canonical Port TUI - Persistent Docked Shortcuts Legend Widget (Feature 16)
Version: 3.0.0-CANONICAL
Permanently positioned at the bottom of all 9 screens, displaying high-contrast hotkeys
and stability layer navigation shortcuts regardless of widget focus or terminal width.
"""

from typing import List, Tuple, Optional
from textual.widgets import Static
from textual import events
from rich.text import Text


class DockedShortcutsLegend(Static):
    """
    Persistent Docked Shortcuts Legend Widget (Feature 16 & M3 Ground-Up Stability).
    High-contrast keyboard legend permanently visible at the bottom of all 9 screens.
    Supports responsive width formatting and mouse click interaction:
    - Tier 1 (>=138 cols): Full canonical labels ([1/c] AGI Term | ... | [q] Quit)
    - Tier 2 (78-137 cols, e.g. 80-col terminal): Standard compact labels ([1]AGI [2]Net ... [r]Ref [q]Quit)
    - Tier 3 (53-77 cols): Micro compact labels ([1]A [2]N ... [r] [q])
    - Tier 4 (<53 cols): Nano shortcuts ([1-9] Tabs | [r] Ref | [q] Quit)
    """

    DEFAULT_CSS = """
    DockedShortcutsLegend {
        height: 1;
        background: #0b111c;
        color: #94a3b8;
        content-align: center middle;
    }
    """

    SHORTCUT_ITEMS: List[Tuple[str, str, str, str]] = [
        ("1/c", "AGI Term", "#00ffcc", "agi_terminal"),
        ("2/n", "Net", "#00ffff", "network"),
        ("3/h", "HW", "#38bdf8", "hardware"),
        ("4/b", "Bio", "#4ade80", "biometrics"),
        ("5/i", "Inf", "#e879f9", "ai_inference"),
        ("6/t", "Train", "#facc15", "training"),
        ("7/g", "Gov", "#f43f5e", "governance"),
        ("8/s", "Tool", "#a78bfa", "tooling"),
        ("9/o", "Opt", "#38bdf8", "optimization"),
    ]

    SHORTCUT_ITEMS_COMPACT: List[Tuple[str, str, str, str]] = [
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

    SHORTCUT_ITEMS_MICRO: List[Tuple[str, str, str, str]] = [
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

    def __init__(self, active_screen: str = "", id: str = "docked-shortcuts-legend", classes: str = "") -> None:
        super().__init__(id=id, classes=classes)
        self.active_screen = active_screen
        self._click_regions: List[Tuple[int, int, str]] = []
        self._last_text_len: int = 0

    def on_mount(self) -> None:
        self.update_legend(self.active_screen)

    def on_resize(self, event: events.Resize) -> None:
        """Dynamically re-render responsive shortcut legend on viewport dimension changes."""
        self.update_legend(self.active_screen)

    def set_active_screen(self, screen_name: str) -> None:
        self.active_screen = screen_name
        self.update_legend(screen_name)

    def build_legend_text(self, active_screen: str = "", width: Optional[int] = None) -> Text:
        """
        Build Rich Text containing high-contrast hotkeys matching 9-screen stability hierarchy.
        Supports responsive width formatting across 4 viewport tiers.
        """
        target = active_screen or self.active_screen or "agi_terminal"
        eff_width = width if width is not None else 180
        text = Text()
        self._click_regions = []
        pos = 0

        if eff_width < 53:
            # Nano mode (<53 cols, 31 chars)
            t_str = "[1-9] Tabs"
            text.append("[1-9]", style="bold #00ffcc")
            text.append(" Tabs", style="white")
            self._click_regions.append((pos, pos + len(t_str), "agi_terminal"))
            pos += len(t_str)

            text.append(" | ", style="dim #475569")
            pos += 3

            r_str = "[r] Ref"
            text.append("[r]", style="bold #4ade80")
            text.append(" Ref", style="white")
            self._click_regions.append((pos, pos + len(r_str), "refresh"))
            pos += len(r_str)

            text.append(" | ", style="dim #475569")
            pos += 3

            q_str = "[q] Quit"
            text.append("[q]", style="bold #f87171")
            text.append(" Quit", style="white")
            self._click_regions.append((pos, pos + len(q_str), "quit"))
            pos += len(q_str)

        elif eff_width < 78:
            # Micro mode (53-77 cols, 52 chars)
            for i, (key, label, col, sid) in enumerate(self.SHORTCUT_ITEMS_MICRO):
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
                text.append(" ", style="dim #475569")
                pos += 1

            r_str = "[r]"
            text.append("[r]", style="bold #4ade80")
            self._click_regions.append((pos, pos + len(r_str), "refresh"))
            pos += len(r_str)

            text.append(" ", style="dim #475569")
            pos += 1

            q_str = "[q]"
            text.append("[q]", style="bold #f87171")
            self._click_regions.append((pos, pos + len(q_str), "quit"))
            pos += len(q_str)

        elif eff_width < 138:
            # Standard compact mode (78-137 cols, e.g. 80-col terminal, 76 chars)
            for i, (key, label, col, sid) in enumerate(self.SHORTCUT_ITEMS_COMPACT):
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
                text.append(" ", style="dim #475569")
                pos += 1

            r_str = "[r]Ref"
            text.append("[r]", style="bold #4ade80")
            text.append("Ref", style="white")
            self._click_regions.append((pos, pos + len(r_str), "refresh"))
            pos += len(r_str)

            text.append(" ", style="dim #475569")
            pos += 1

            q_str = "[q]Quit"
            text.append("[q]", style="bold #f87171")
            text.append("Quit", style="white")
            self._click_regions.append((pos, pos + len(q_str), "quit"))
            pos += len(q_str)

        else:
            # Full mode (>=138 cols, 137 chars)
            for i, (keys, label, col, sid) in enumerate(self.SHORTCUT_ITEMS):
                is_active = (target == sid)
                item_str = f"[{keys}] {label}"
                item_len = len(item_str)
                if is_active:
                    text.append(f"[{keys}]", style=f"bold {col} reverse")
                    text.append(f" {label}", style="bold white")
                else:
                    text.append(f"[{keys}]", style=f"bold {col}")
                    text.append(f" {label}", style="white")
                self._click_regions.append((pos, pos + item_len, sid))
                pos += item_len
                text.append(" | ", style="dim #475569")
                pos += 3

            r_str = "[r] Refresh"
            text.append("[r]", style="bold #4ade80")
            text.append(" Refresh", style="white")
            self._click_regions.append((pos, pos + len(r_str), "refresh"))
            pos += len(r_str)

            text.append(" | ", style="dim #475569")
            pos += 3

            q_str = "[q] Quit"
            text.append("[q]", style="bold #f87171")
            text.append(" Quit", style="white")
            self._click_regions.append((pos, pos + len(q_str), "quit"))
            pos += len(q_str)

        self._last_text_len = len(text.plain)
        return text

    def update_legend(self, active_screen: str = "") -> None:
        target = active_screen or self.active_screen
        w = getattr(self, "_mock_size", None) or getattr(self, "size", None)
        width_val = w.width if (w and w.width > 0) else None
        rich_text = self.build_legend_text(target, width=width_val)
        try:
            self.update(rich_text)
        except Exception:
            pass

    def _dispatch_action(self, action_or_screen: str) -> None:
        """Dispatch action to app."""
        try:
            app_inst = getattr(self, "_mock_app", None) or self.app
        except Exception:
            return

        if action_or_screen == "refresh":
            if hasattr(app_inst, "action_refresh_current"):
                app_inst.action_refresh_current()
        elif action_or_screen == "quit":
            if hasattr(app_inst, "action_quit"):
                app_inst.action_quit()
            elif hasattr(app_inst, "exit"):
                app_inst.exit()
        else:
            if hasattr(app_inst, "switch_screen"):
                app_inst.switch_screen(action_or_screen)

    def on_click(self, event: events.Click) -> None:
        """
        Handle mouse click on shortcut items with centered offset compensation.
        Uses exact half-open interval hit testing [start_x, end_x).
        """
        click_x = event.x
        w = getattr(self, "_mock_size", None) or getattr(self, "size", None)
        widget_w = w.width if (w and w.width > 0) else 0
        text_len = getattr(self, "_last_text_len", 0)
        start_offset = max(0, (widget_w - text_len) // 2) if (widget_w > text_len and text_len > 0) else 0
        relative_x = click_x - start_offset

        for start_x, end_x, action_or_screen in self._click_regions:
            if start_x <= relative_x < end_x:
                self._dispatch_action(action_or_screen)
                break
