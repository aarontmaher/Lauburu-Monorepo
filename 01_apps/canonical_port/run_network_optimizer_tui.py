#!/usr/bin/env python3
"""
01_apps/canonical_port/run_network_optimizer_tui.py
===================================================
Standalone Launcher for the Canonical Network System Settings Optimizer TUI.
Allows instant, zero-lag launching of the full 61-parameter network tuning cockpit.
"""

import os
import sys
from pathlib import Path

# Ensure paths are configured
SCRIPT_DIR = Path(__file__).resolve().parent
TUI_DIR = SCRIPT_DIR / "tui"
if str(TUI_DIR) not in sys.path:
    sys.path.insert(0, str(TUI_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from tui.widgets.network_settings_optimizer_widget import NetworkSettingsOptimizerWidget


class StandaloneNetworkOptimizerApp(App):
    """Standalone TUI Application dedicated to Network System Settings Optimization."""

    TITLE = "LAUBURU MESH — NETWORK SYSTEM SETTINGS OPTIMIZER"
    SUB_TITLE = "61 Mapped Parameters • Live BDP Engine • Real-Time Effect Tracker • 7-Layer Mesh"

    CSS = """
    Screen {
        background: #060a12;
        color: #e2e8f0;
    }
    Header {
        dock: top;
        height: 1;
        background: #0b1120;
    }
    Footer {
        dock: bottom;
        height: 1;
        background: #060a12;
        border-top: solid #1e293b;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit Optimizer"),
        ("r", "refresh_telemetry", "Run Micro-Benchmark"),
        ("1", "apply_ai", "⚡ Preset: AI Sharding"),
        ("2", "apply_tb4", "🚀 Preset: 10G TB4"),
        ("3", "apply_mesh", "🛡️ Preset: Resilient Mesh"),
        ("0", "apply_stock", "⚖️ Reset Stock"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield NetworkSettingsOptimizerWidget(id="standalone-net-opt-widget")
        yield Footer()

    def action_refresh_telemetry(self) -> None:
        widget = self.query_one("#standalone-net-opt-widget", NetworkSettingsOptimizerWidget)
        widget.worker_run_live_benchmark()

    def action_apply_ai(self) -> None:
        widget = self.query_one("#standalone-net-opt-widget", NetworkSettingsOptimizerWidget)
        widget.on_apply_ai_profile()

    def action_apply_tb4(self) -> None:
        widget = self.query_one("#standalone-net-opt-widget", NetworkSettingsOptimizerWidget)
        widget.on_apply_tb4_profile()

    def action_apply_mesh(self) -> None:
        widget = self.query_one("#standalone-net-opt-widget", NetworkSettingsOptimizerWidget)
        widget.on_apply_mesh_profile()

    def action_apply_stock(self) -> None:
        widget = self.query_one("#standalone-net-opt-widget", NetworkSettingsOptimizerWidget)
        widget.on_apply_stock_profile()


if __name__ == "__main__":
    app = StandaloneNetworkOptimizerApp()
    app.run()
