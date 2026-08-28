"""
tests/unit/test_network_settings_optimizer.py
=============================================
Unit Tests for Network System Settings Optimization Engine & Real-Time Effect Tracker.
"""

import sys
import unittest
from pathlib import Path

# Add repository paths
REPO_ROOT = Path(__file__).resolve().parents[2]
TUI_PATH = REPO_ROOT / "01_apps" / "canonical_port" / "tui"
if str(TUI_PATH) not in sys.path:
    sys.path.insert(0, str(TUI_PATH))

from models.network_optimizer_models import (
    NetworkSettingCategory,
    SettingImpactMetric,
    SettingValueType,
    NetworkSettingDefinition,
    NetworkBenchmarkMetrics,
    OptimizationDeltaReport,
    BDPCalculation,
)
from services.network_optimizer_service import NetworkOptimizerService


class TestNetworkSettingsOptimizer(unittest.TestCase):
    """Test suite for Network System Settings Optimization Engine."""

    def setUp(self):
        self.service = NetworkOptimizerService()

    def test_registry_size_and_categories(self):
        """Verify that at least 60 settings are mapped across all 6 categories."""
        settings = self.service.get_all_settings()
        self.assertGreaterEqual(len(settings), 60, "Expected at least 60 mapped settings")

        categories = {s.category for s in settings}
        self.assertEqual(len(categories), 6, "Expected all 6 network categories to be represented")
        self.assertIn(NetworkSettingCategory.KERNEL_SYSCTL, categories)
        self.assertIn(NetworkSettingCategory.INTERFACE_MTU, categories)
        self.assertIn(NetworkSettingCategory.SOCKET_BDP, categories)
        self.assertIn(NetworkSettingCategory.DNS_ROUTING, categories)
        self.assertIn(NetworkSettingCategory.MESH_TAILSCALE, categories)
        self.assertIn(NetworkSettingCategory.REMOTE_NODES, categories)

    def test_key_kernel_sysctls_present(self):
        """Verify critical high-impact Darwin sysctls exist in registry."""
        critical_keys = [
            "net.inet.tcp.sendspace",
            "net.inet.tcp.recvspace",
            "kern.ipc.maxsockbuf",
            "kern.ipc.somaxconn",
            "net.inet.tcp.delayed_ack",
            "net.inet.tcp.sack",
            "net.inet.tcp.fastopen",
            "net.inet.tcp.keepidle",
            "net.inet.tcp.win_scale_factor",
            "ifconfig.bridge0.mtu",
            "bdp.engine.tb4_10gbe",
        ]
        for key in critical_keys:
            setting = self.service.get_setting(key)
            self.assertIsNotNone(setting, f"Critical key '{key}' missing from registry")
            self.assertTrue(len(setting.line_by_line_analysis) > 10, f"Setting '{key}' lacks deep analysis")

    def test_bdp_matrix_calculations(self):
        """Verify Bandwidth-Delay Product calculations match mathematical formulas."""
        bdp_list = self.service.calculate_bdp_matrix()
        self.assertGreaterEqual(len(bdp_list), 5)

        tb4_bdp = next((b for b in bdp_list if "Thunderbolt" in b.link_name), None)
        self.assertIsNotNone(tb4_bdp)
        self.assertEqual(tb4_bdp.bandwidth_mbps, 10000.0)
        self.assertEqual(tb4_bdp.rtt_ms, 0.28)
        # BDP = (10000 * 1e6 * 0.00028) / 8 = 350,000 bytes
        self.assertEqual(tb4_bdp.bdp_bytes, 350000)
        self.assertGreater(tb4_bdp.recommended_sendspace, 350000)
        self.assertGreater(tb4_bdp.recommended_recvspace, 350000)

    def test_profile_presets_application(self):
        """Verify optimization profile presets update registry values and generate safe commands."""
        profiles = ["ai_tensor_sharding", "high_throughput_tb4", "resilient_mesh", "stock_balanced"]
        for p in profiles:
            ok, msg, cmds = self.service.apply_profile(p)
            self.assertTrue(ok, f"Failed to apply profile {p}: {msg}")
            self.assertEqual(self.service._active_profile, p)

    def test_setting_bounds_validation(self):
        """Verify out-of-bounds parameter modifications are cleanly rejected."""
        # Test lower bound rejection
        ok, cmd, err = self.service.set_setting_value("net.inet.tcp.sendspace", 1024)
        self.assertFalse(ok)
        self.assertIn("below minimum", err)

        # Test upper bound rejection
        ok, cmd, err = self.service.set_setting_value("net.inet.tcp.sendspace", 99999999)
        self.assertFalse(ok)
        self.assertIn("exceeds maximum", err)

    def test_micro_benchmark_and_delta_report(self):
        """Verify live empirical benchmark execution and delta metric computation."""
        metrics = self.service.run_benchmark(is_baseline=False)
        self.assertIsNotNone(metrics.avg_rtt_ms)
        self.assertGreater(metrics.loopback_throughput_mbps, 0.0)

        report = self.service._compute_delta_report()
        self.assertIsNotNone(report.overall_score)
        self.assertGreaterEqual(report.overall_score, 0.0)
        self.assertLessEqual(report.overall_score, 100.0)


if __name__ == "__main__":
    unittest.main()
