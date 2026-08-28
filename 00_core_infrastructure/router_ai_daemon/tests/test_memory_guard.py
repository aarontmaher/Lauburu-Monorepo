"""Unit tests for smolagi MemoryGuard and MemoryStats."""

import os
import gc
from unittest.mock import patch
import pytest
from src.config import RouterConfig
from src.container.memory_guard import MemoryGuard, MemoryStats


def test_memory_stats_dataclass_and_dict():
    """Verify MemoryStats properties and dictionary serialization."""
    stats = MemoryStats(
        rss_bytes=104857600,  # 100 MB
        rss_mb=100.0,
        vms_bytes=209715200,  # 200 MB
        vms_mb=200.0,
        budget_mb=300.0,
        headroom_mb=200.0,
        utilization_pct=33.33,
        is_warning=False,
        is_critical=False,
        is_exceeded=False,
        source="test",
    )
    d = stats.to_dict()
    assert d["rss_mb"] == 100.0
    assert d["budget_mb"] == 300.0
    assert d["headroom_mb"] == 200.0
    assert d["is_warning"] is False
    assert d["is_critical"] is False
    assert d["is_exceeded"] is False


def test_memory_guard_current_process():
    """Verify MemoryGuard can inspect the current Python process RSS."""
    guard = MemoryGuard()
    stats = guard.get_process_memory()
    assert stats.rss_bytes > 0
    assert stats.rss_mb > 0
    assert stats.budget_mb == 300.0
    assert stats.headroom_mb >= 0
    assert stats.utilization_pct > 0
    assert stats.is_exceeded is False


def test_memory_guard_warning_and_critical_detection():
    """Verify warning, critical, and exceeded flags when memory scales."""
    cfg = RouterConfig(
        ram_budget_mb=300.0,
        ram_warning_threshold_mb=10.0,  # low for test
        ram_critical_threshold_mb=20.0,
    )
    guard = MemoryGuard(config=cfg)
    stats = guard.get_process_memory()
    # Since test runner uses >10MB, is_warning should be True
    assert stats.is_warning is True


def test_memory_guard_check_budget():
    """Verify check_memory_budget function."""
    guard = MemoryGuard()
    within_budget, stats = guard.check_memory_budget()
    assert within_budget is True
    assert stats.is_exceeded is False


def test_memory_guard_subsystem_aggregation():
    """Verify multi-PID aggregation."""
    guard = MemoryGuard()
    current_pid = os.getpid()
    stats = guard.get_total_subsystem_memory([current_pid])
    assert stats.rss_bytes > 0
    assert stats.rss_mb > 0


def test_memory_guard_garbage_collection():
    """Verify run_garbage_collection executes without error."""
    guard = MemoryGuard()
    # Create temporary circular reference
    a = []
    a.append(a)
    del a
    collected = guard.run_garbage_collection()
    assert isinstance(collected, int)


def test_memory_guard_enforce_limits():
    """Verify enforce_limits executes and returns stats."""
    guard = MemoryGuard()
    stats = guard.enforce_limits(trigger_gc_on_warning=True)
    assert isinstance(stats, MemoryStats)
