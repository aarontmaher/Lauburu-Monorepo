"""
tests/e2e/test_network_optimizer_tui_e2e.py
===========================================
Headless Textual E2E Pilot Test for Network System Settings Optimizer TUI.
"""

import sys
import asyncio
import unittest
from pathlib import Path

# Add paths
REPO_ROOT = Path(__file__).resolve().parents[2]
TUI_PATH = REPO_ROOT / "01_apps" / "canonical_port" / "tui"
APP_PATH = REPO_ROOT / "01_apps" / "canonical_port"
if str(TUI_PATH) not in sys.path:
    sys.path.insert(0, str(TUI_PATH))
if str(APP_PATH) not in sys.path:
    sys.path.insert(0, str(APP_PATH))

from run_network_optimizer_tui import StandaloneNetworkOptimizerApp
from widgets.network_settings_optimizer_widget import NetworkSettingsOptimizerWidget
from textual.widgets import DataTable


class TestNetworkOptimizerTUIE2E(unittest.IsolatedAsyncioTestCase):
    """Headless Pilot E2E Test for Network Settings Optimizer TUI."""

    async def test_tui_app_lifecycle_and_interactions(self):
        """Verify TUI mounts, populates DataTable, handles profile clicks, and quits cleanly."""
        app = StandaloneNetworkOptimizerApp()
        async with app.run_test(size=(140, 45)) as pilot:
            # 1. Verify app and widget mounted
            widget = app.query_one(NetworkSettingsOptimizerWidget)
            self.assertIsNotNone(widget)

            # 2. Verify DataTable contains rows
            table = widget.query_one("#opt-settings-table", DataTable)
            self.assertGreater(table.row_count, 50, "Expected >50 rows in settings table")

            # 3. Simulate Profile Button Press (AI Tensor Sharding)
            await pilot.click("#btn-profile-ai")
            await pilot.pause(0.2)
            self.assertEqual(widget._current_report.active_profile, "ai_tensor_sharding")

            # 4. Simulate Category Filter Button Press (Kernel Sysctl)
            await pilot.click("#btn-cat-sysctl")
            await pilot.pause(0.2)
            self.assertEqual(table.row_count, 35)

            # 5. Simulate Category Filter Button Press (All)
            await pilot.click("#btn-cat-all")
            await pilot.pause(0.2)
            self.assertEqual(table.row_count, 61)

            # 6. Simulate Benchmarking
            await pilot.click("#btn-run-benchmark")
            await pilot.pause(0.5)
            self.assertIsNotNone(widget._current_report)

            # 7. Press 'q' to quit cleanly
            await pilot.press("q")


if __name__ == "__main__":
    unittest.main()
