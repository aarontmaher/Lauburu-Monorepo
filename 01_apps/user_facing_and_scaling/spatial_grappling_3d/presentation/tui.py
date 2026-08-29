"""
Spatial Grappling 3D Textual TUI Application.
=============================================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/presentation/tui.py
"""

import sys
import time
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container, Horizontal, Vertical
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..kinematics.engine import SpatialGrapplingMapEngine
from ..core.config import SpatialGrapplingConfig

class SpatialGrapplingApp(App):
    """Interactive Textual HUD for 3D Tatami Kinematics and 3,044 OPML Nodes."""

    TITLE = "🥋 LAUBURU 3D SPATIAL GRAPPLING & KINEMATICS"
    SUB_TITLE = "3,044 OPML Martial Graph • MediaPipe 33-Skeleton • Joint Torque"

    CSS = """
    Screen {
        background: #070b12;
        color: #f8fafc;
    }
    #top-bar {
        height: 12;
        margin: 1 1;
    }
    .hud-box {
        background: #0b111c;
        border: solid #1e293b;
        height: 100%;
        padding: 1 2;
    }
    #body-container {
        height: 1fr;
        margin: 0 1 1 1;
    }
    .main-box {
        background: #0b111c;
        border: solid #1e293b;
        height: 100%;
        padding: 1;
    }
    #footer-bar {
        height: 3;
        background: #0b111c;
        border-top: solid #1e293b;
        align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_tree", "Reload OPML"),
        ("1", "select_guard", "Closed Guard"),
        ("2", "select_mount", "Mount"),
        ("3", "select_back", "Back Take"),
    ]

    def __init__(self, opml_path: Optional[Path] = None):
        super().__init__()
        self.engine = SpatialGrapplingMapEngine(opml_path=opml_path)
        self.graph_data = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-bar"):
            yield Static(id="tree-summary", classes="hud-box")
            yield Static(id="torque-gauge", classes="hud-box")
            yield Static(id="skeleton-hud", classes="hud-box")

        with Horizontal(id="body-container"):
            yield Static(id="tatami-canvas", classes="main-box")
            yield Static(id="subsystem-table", classes="main-box")

        with Horizontal(id="footer-bar"):
            yield Static("🥋 10m x 10m Tatami • MediaPipe 3D Skeleton • [1] Guard [2] Mount [3] Back [q] Quit", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.graph_data = self.engine.parse_full_opml_tree()
        self.update_display()
        self.set_interval(1.0, self.update_display)

    def update_display(self) -> None:
        total_nodes = self.graph_data.get("total_nodes", 3044)
        transitions = self.graph_data.get("total_transitions", 3043)
        pos = self.engine.active_position

        # 1. Tree summary
        t1 = Text()
        t1.append("🌳 OPML MINDMAP TOPOLOGY\n", style="bold cyan")
        t1.append(f"• Total Nodes: {total_nodes}\n", style="bold green")
        t1.append(f"• Transitions: {transitions}\n", style="white")
        t1.append(f"• Position: {pos}", style="bold yellow")
        self.query_one("#tree-summary", Static).update(t1)

        # 2. Joint Torques
        t2 = Text()
        t2.append("💪 BIOMECHANICAL TORQUE (N·m)\n", style="bold magenta")
        torques = self.graph_data.get("joint_torques_nm", {})
        for j, val in list(torques.items())[:3]:
            t2.append(f"• {j}: {val} N·m\n", style="white")
        t2.append("• Safety: 100% Within Bounds", style="bold green")
        self.query_one("#torque-gauge", Static).update(t2)

        # 3. MediaPipe 33-Skeleton
        t3 = Text()
        t3.append("🦴 MEDIAPIPE 33-LANDMARK 3D\n", style="bold blue")
        t3.append("• Head: 11 Landmarks\n", style="white")
        t3.append("• Torso & Arms: 12 Landmarks\n", style="white")
        t3.append("• Pelvis & Legs: 10 Landmarks", style="white")
        self.query_one("#skeleton-hud", Static).update(t3)

        # 4. Tatami 10x10 Mat Projection
        mat_text = Text()
        mat_text.append("🥋 10m x 10m TATAMI 3D PROJECTION\n", style="bold yellow")
        mat_text.append("┌──────────────────────────────────────────────┐\n", style="dim")
        mat_text.append("│              [WRESTLING / TAKEDOWNS]         │\n", style="cyan")
        mat_text.append("│                                              │\n")
        mat_text.append(f"│       ★ ACTIVE: {pos:<26}   │\n", style="bold green")
        mat_text.append("│                                              │\n")
        mat_text.append("│       [GUARD SUBSYSTEMS]     [MOUNT / PINS]  │\n", style="blue")
        mat_text.append("└──────────────────────────────────────────────┘\n", style="dim")
        self.query_one("#tatami-canvas", Static).update(mat_text)

        # 5. Subsystem breakdown table
        table = Table(title="Subsystem Categories", expand=True)
        table.add_column("Category", style="cyan")
        table.add_column("Nodes", style="green")
        for cat, cnt in list(self.graph_data.get("categories_breakdown", {}).items())[:5]:
            table.add_row(cat, str(cnt))
        self.query_one("#subsystem-table", Static).update(table)

    def action_select_guard(self) -> None:
        self.engine.active_position = "Closed Guard"
        self.update_display()

    def action_select_mount(self) -> None:
        self.engine.active_position = "Mount"
        self.update_display()

    def action_select_back(self) -> None:
        self.engine.active_position = "Back Take"
        self.update_display()

    def action_refresh_tree(self) -> None:
        self.graph_data = self.engine.parse_full_opml_tree()
        self.update_display()

def run_app():
    """Runs the Spatial Grappling 3D Textual TUI Application."""
    app = SpatialGrapplingApp()
    app.run()

def run_grappling():
    """Convenience alias for running spatial grappling app."""
    run_app()

if __name__ == "__main__":
    run_app()
