"""
Unit Tests for Dynamic RAM Governor & Memory Sentinel (Feature F4).

Tests:
- Dynamic Cap calculation (<= 90.0%)
- Minimum Headroom validation (>= 2.50 GB)
- Memory tier categorization (TIER_1_OPTIMAL, TIER_2_BALANCED, TIER_3_RESTRICTED, TIER_4_CRITICAL)
- Headroom equation correctness
- Memory reclamation (gc.collect + torch.mps.empty_cache)
- Safety limit enforcement and error handling
"""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.trainer.dynamic_ram_governor import (
    DynamicRAMGovernor,
    MemoryGovernorError,
    MemoryMetrics,
    MemoryStatusTier,
)


class TestDynamicRAMGovernor(unittest.TestCase):
    """Test suite for DynamicRAMGovernor."""

    def setUp(self):
        # 24 GB total RAM baseline (24 * 1024^3 bytes)
        self.total_24gb = 24 * (1024 ** 3)
        self.bytes_in_gb = 1024 ** 3

    def test_default_initialization(self):
        """Verify default parameters match architecture specification."""
        gov = DynamicRAMGovernor()
        self.assertEqual(gov.max_ram_ratio, 0.90)
        self.assertEqual(gov.min_headroom_gb, 2.50)

    def test_invalid_parameters_raise_value_error(self):
        """Verify constructor validates parameter bounds."""
        with self.assertRaises(ValueError):
            DynamicRAMGovernor(max_ram_ratio=0.0)
        with self.assertRaises(ValueError):
            DynamicRAMGovernor(max_ram_ratio=1.5)
        with self.assertRaises(ValueError):
            DynamicRAMGovernor(min_headroom_gb=-1.0)

    def test_live_host_metrics(self):
        """Verify live host sampling produces genuine unmocked metrics."""
        gov = DynamicRAMGovernor()
        metrics = gov.get_metrics()
        
        self.assertIsInstance(metrics, MemoryMetrics)
        self.assertGreater(metrics.total_ram_gb, 0.0)
        self.assertGreater(metrics.used_ram_gb, 0.0)
        self.assertGreaterEqual(metrics.free_headroom_gb, 0.0)
        self.assertIn(metrics.status_tier, list(MemoryStatusTier))
        
        # Verify dictionary serialization
        d = metrics.to_dict()
        self.assertIn("total_ram_gb", d)
        self.assertIn("dynamic_cap_gb", d)
        self.assertIn("free_headroom_gb", d)
        self.assertIn("status_tier", d)

    def test_tier1_optimal_scenario(self):
        """Verify TIER_1_OPTIMAL classification when usage is < 70%."""
        # 24GB total, 10GB used (41.67%), available 14GB
        mock_vmem = SimpleNamespace(
            total=self.total_24gb,
            used=10 * self.bytes_in_gb,
            available=14 * self.bytes_in_gb,
            percent=41.67,
        )
        gov = DynamicRAMGovernor(vmem_provider=lambda: mock_vmem)
        metrics = gov.get_metrics()
        
        # Dynamic cap for 24GB @ 90% is 21.60 GB
        # Free headroom = 21.60 - 10.0 = 11.60 GB >= 2.50 GB
        self.assertEqual(metrics.status_tier, MemoryStatusTier.TIER_1_OPTIMAL)
        self.assertTrue(metrics.is_safe)
        self.assertAlmostEqual(metrics.dynamic_cap_gb, 21.60, places=2)
        self.assertAlmostEqual(metrics.free_headroom_gb, 11.60, places=2)
        self.assertTrue(gov.check_headroom())

    def test_tier2_balanced_scenario(self):
        """Verify TIER_2_BALANCED classification when usage is 70% <= usage < 85%."""
        # 24GB total, 18GB used (75%), available 6GB
        mock_vmem = SimpleNamespace(
            total=self.total_24gb,
            used=18 * self.bytes_in_gb,
            available=6 * self.bytes_in_gb,
            percent=75.0,
        )
        gov = DynamicRAMGovernor(vmem_provider=lambda: mock_vmem)
        metrics = gov.get_metrics()
        
        # Free headroom = 21.60 - 18.0 = 3.60 GB >= 2.50 GB
        self.assertEqual(metrics.status_tier, MemoryStatusTier.TIER_2_BALANCED)
        self.assertTrue(metrics.is_safe)
        self.assertAlmostEqual(metrics.free_headroom_gb, 3.60, places=2)
        self.assertTrue(gov.check_headroom())

    def test_tier3_restricted_scenario(self):
        """Verify TIER_3_RESTRICTED classification when usage is 85% <= usage <= 90%."""
        # 24GB total, 20.8GB used (86.67%), available 3.2GB
        mock_vmem = SimpleNamespace(
            total=self.total_24gb,
            used=int(20.8 * self.bytes_in_gb),
            available=int(3.2 * self.bytes_in_gb),
            percent=86.67,
        )
        # Using min_headroom_gb = 0.5 to keep it safe under restricted tier
        gov = DynamicRAMGovernor(min_headroom_gb=0.5, vmem_provider=lambda: mock_vmem)
        metrics = gov.get_metrics()
        
        # Dynamic cap = 21.60 GB, used = 20.80 GB, headroom = 0.80 GB >= 0.50 GB
        self.assertEqual(metrics.status_tier, MemoryStatusTier.TIER_3_RESTRICTED)
        self.assertTrue(metrics.is_safe)
        self.assertTrue(gov.check_headroom())

    def test_tier4_critical_exceeds_dynamic_cap(self):
        """Verify TIER_4_CRITICAL and unsafe status when usage exceeds 90% cap."""
        # 24GB total, 22.5GB used (93.75%), available 1.5GB
        mock_vmem = SimpleNamespace(
            total=self.total_24gb,
            used=int(22.5 * self.bytes_in_gb),
            available=int(1.5 * self.bytes_in_gb),
            percent=93.75,
        )
        gov = DynamicRAMGovernor(vmem_provider=lambda: mock_vmem)
        metrics = gov.get_metrics()
        
        self.assertEqual(metrics.status_tier, MemoryStatusTier.TIER_4_CRITICAL)
        self.assertFalse(metrics.is_safe)
        self.assertFalse(gov.check_headroom())

    def test_tier4_critical_headroom_violation(self):
        """Verify TIER_4_CRITICAL when usage < 90% but headroom < min_headroom_gb."""
        # 24GB total, 19.5GB used (81.25%), available 4.5GB
        # dynamic_cap = 21.60 GB, used = 19.50 GB -> headroom = 2.10 GB (< 2.50 GB floor)
        mock_vmem = SimpleNamespace(
            total=self.total_24gb,
            used=int(19.5 * self.bytes_in_gb),
            available=int(4.5 * self.bytes_in_gb),
            percent=81.25,
        )
        gov = DynamicRAMGovernor(min_headroom_gb=2.50, vmem_provider=lambda: mock_vmem)
        metrics = gov.get_metrics()
        
        self.assertEqual(metrics.status_tier, MemoryStatusTier.TIER_4_CRITICAL)
        self.assertFalse(metrics.is_safe)
        self.assertFalse(gov.check_headroom())

    def test_reclaim_memory_execution(self):
        """Verify reclaim_memory invokes garbage collection and returns stats."""
        gov = DynamicRAMGovernor()
        res = gov.reclaim_memory()
        
        self.assertIn("unreachable_objects_collected", res)
        self.assertIn("mps_cache_cleared", res)
        self.assertIn("cuda_cache_cleared", res)
        self.assertIn("timestamp", res)
        self.assertIsInstance(res["unreachable_objects_collected"], int)

    def test_enforce_safety_limits_success(self):
        """Verify enforce_safety_limits succeeds when headroom is healthy."""
        mock_vmem = SimpleNamespace(
            total=self.total_24gb,
            used=10 * self.bytes_in_gb,
            available=14 * self.bytes_in_gb,
            percent=41.67,
        )
        gov = DynamicRAMGovernor(vmem_provider=lambda: mock_vmem)
        metrics = gov.enforce_safety_limits(auto_reclaim=False)
        self.assertTrue(metrics.is_safe)

    def test_enforce_safety_limits_auto_reclaim_recovers(self):
        """Verify enforce_safety_limits reclaims memory and recovers when initially unsafe."""
        call_count = 0
        def dynamic_vmem():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Initially unsafe (20GB used)
                return SimpleNamespace(
                    total=self.total_24gb,
                    used=int(20.0 * self.bytes_in_gb),
                    available=int(4.0 * self.bytes_in_gb),
                    percent=83.33,
                )
            else:
                # After reclaim, recovered (15GB used)
                return SimpleNamespace(
                    total=self.total_24gb,
                    used=int(15.0 * self.bytes_in_gb),
                    available=int(9.0 * self.bytes_in_gb),
                    percent=62.5,
                )

        gov = DynamicRAMGovernor(min_headroom_gb=2.50, vmem_provider=dynamic_vmem)
        metrics = gov.enforce_safety_limits(auto_reclaim=True)
        self.assertTrue(metrics.is_safe)
        self.assertGreaterEqual(call_count, 2)

    def test_enforce_safety_limits_wait_recovers(self):
        """Verify enforce_safety_limits waits and succeeds when pressure subsides within timeout."""
        call_count = 0
        def delayed_recovery_vmem():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return SimpleNamespace(
                    total=self.total_24gb,
                    used=int(22.0 * self.bytes_in_gb),
                    available=int(2.0 * self.bytes_in_gb),
                    percent=91.67,
                )
            return SimpleNamespace(
                total=self.total_24gb,
                used=int(12.0 * self.bytes_in_gb),
                available=int(12.0 * self.bytes_in_gb),
                percent=50.0,
            )

        gov = DynamicRAMGovernor(vmem_provider=delayed_recovery_vmem)
        metrics = gov.enforce_safety_limits(auto_reclaim=True, max_wait_seconds=1.0, poll_interval=0.01)
        self.assertTrue(metrics.is_safe)

    def test_custom_governor_thresholds(self):
        """Verify custom max_ram_ratio and min_headroom_gb are strictly respected."""
        mock_vmem = SimpleNamespace(
            total=16 * self.bytes_in_gb,
            used=int(12.0 * self.bytes_in_gb),
            available=int(4.0 * self.bytes_in_gb),
            percent=75.0,
        )
        # 16GB total @ 80% cap = 12.80 GB cap. Used = 12.0 GB -> Free headroom = 0.80 GB
        # With min_headroom = 1.0 GB, headroom 0.80 < 1.0 -> UNSAFE
        gov = DynamicRAMGovernor(max_ram_ratio=0.80, min_headroom_gb=1.0, vmem_provider=lambda: mock_vmem)
        self.assertFalse(gov.check_headroom())
        metrics = gov.get_metrics()
        self.assertEqual(metrics.status_tier, MemoryStatusTier.TIER_4_CRITICAL)

        # With min_headroom = 0.5 GB, headroom 0.80 >= 0.5 -> SAFE
        gov_safe = DynamicRAMGovernor(max_ram_ratio=0.80, min_headroom_gb=0.5, vmem_provider=lambda: mock_vmem)
        self.assertTrue(gov_safe.check_headroom())
        metrics_safe = gov_safe.get_metrics()
        self.assertEqual(metrics_safe.status_tier, MemoryStatusTier.TIER_2_BALANCED)

    def test_to_dict_metric_precision(self):
        """Verify to_dict returns formatted dictionary with exact schema."""
        mock_vmem = SimpleNamespace(
            total=self.total_24gb,
            used=int(10.123456 * self.bytes_in_gb),
            available=int(13.876544 * self.bytes_in_gb),
            percent=42.18,
        )
        gov = DynamicRAMGovernor(vmem_provider=lambda: mock_vmem)
        d = gov.get_metrics().to_dict()
        self.assertEqual(d["total_ram_gb"], 24.0)
        self.assertEqual(d["used_ram_gb"], 10.1235)
        self.assertEqual(d["usage_pct"], 42.18)
        self.assertEqual(d["dynamic_cap_gb"], 21.6)
        self.assertEqual(d["status_tier"], "TIER_1_OPTIMAL")
        self.assertTrue(d["is_safe"])

    def test_enforce_safety_limits_raises_on_critical_violation(self):
        """Verify enforce_safety_limits raises MemoryGovernorError on persistent violation."""
        mock_vmem = SimpleNamespace(
            total=self.total_24gb,
            used=int(23.0 * self.bytes_in_gb),
            available=int(1.0 * self.bytes_in_gb),
            percent=95.83,
        )
        gov = DynamicRAMGovernor(vmem_provider=lambda: mock_vmem)

        with self.assertRaises(MemoryGovernorError) as ctx:
            gov.enforce_safety_limits(auto_reclaim=False, max_wait_seconds=0.0)

        self.assertIn("Memory Governor Violation", str(ctx.exception))
        self.assertIn("TIER_4_CRITICAL", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
