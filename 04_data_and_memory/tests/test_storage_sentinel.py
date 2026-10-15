#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E & Unit Test Suite: Rule 6.3 Storage Sentinel & Self-Healing Cache Purger
============================================================================
Test Target: 04_data_and_memory/telemetry_streamer.py (StorageSentinel)
Covers:
- Feature 13: Fast-Path Storage Headroom Sentinel (Tier 1 & Tier 2)
- Feature 14: Self-Healing Cache Purging (Tier 1 & Tier 2)
Test Framework: pytest
Zero-Mock Compliance: 100% genuine disk usage checks, genuine directory inodes, zero facade mocks.
"""

import os
import sys
import time
import shutil
import tempfile
from pathlib import Path

import pytest

# Ensure module path is accessible
MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from telemetry_streamer import StorageSentinel


@pytest.fixture
def temp_sentinel_workspace():
    """Provides an isolated workspace for storage sentinel testing."""
    temp_dir = tempfile.mkdtemp(prefix="lauburu_sentinel_test_")
    ws = Path(temp_dir)
    obs_dir = ws / "obsidian_vault"
    lora_dir = ws / "lora_datasets"
    data_dir = ws / "04_data_and_memory"
    obs_dir.mkdir(parents=True, exist_ok=True)
    lora_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    sentinel = StorageSentinel(monorepo_root=ws, min_free_gb=5.0)
    # Point lora_dir to temp workspace for isolation
    sentinel.lora_dir = lora_dir

    yield {
        "workspace": ws,
        "obs_dir": obs_dir,
        "lora_dir": lora_dir,
        "data_dir": data_dir,
        "sentinel": sentinel,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================================================================
# FEATURE 13: Fast-Path Storage Headroom Sentinel (Tiers 1 & 2)
# ===========================================================================

class TestFeature13FastPathStorageSentinel:
    """Tests sub-3ms Rule 6.3 Fast-Path storage check and headroom verification."""

    def test_fast_path_latency_sub_3ms(self, temp_sentinel_workspace):
        """Tier 1.1: fast_path_check executes in < 3.0 ms."""
        sentinel = temp_sentinel_workspace["sentinel"]
        is_healthy, free_gb, latency_ms = sentinel.fast_path_check()

        assert latency_ms < 3.0  # Rule 6.3 Invariant: sub-3ms
        assert isinstance(is_healthy, bool)
        assert free_gb > 0.0

    def test_fast_path_returns_healthy_with_adequate_headroom(self, temp_sentinel_workspace):
        """Tier 1.2: Returns is_healthy=True when free space >= min_free_gb."""
        sentinel = temp_sentinel_workspace["sentinel"]
        sentinel.min_free_gb = 1.0  # 1.0 GB threshold

        is_healthy, free_gb, _ = sentinel.fast_path_check()
        assert is_healthy is True
        assert free_gb >= 1.0

    def test_fast_path_returns_unhealthy_when_headroom_insufficient(self, temp_sentinel_workspace):
        """Tier 1.3: Returns is_healthy=False when requested headroom exceeds disk capacity."""
        sentinel = temp_sentinel_workspace["sentinel"]
        sentinel.min_free_gb = 50000.0  # 50 TB threshold (impossible on test machine)

        is_healthy, free_gb, _ = sentinel.fast_path_check()
        assert is_healthy is False
        assert free_gb < 50000.0

    def test_fast_path_handles_missing_obsidian_dir(self, temp_sentinel_workspace):
        """Tier 1.4: Returns is_healthy=False when obsidian_vault directory is missing."""
        sentinel = temp_sentinel_workspace["sentinel"]
        obs_dir = temp_sentinel_workspace["obs_dir"]
        shutil.rmtree(obs_dir, ignore_errors=True)

        is_healthy, _, _ = sentinel.fast_path_check()
        assert is_healthy is False

    def test_is_storage_healthy_boolean_interface(self, temp_sentinel_workspace):
        """Tier 1.5: is_storage_healthy provides clean boolean check conforming to contract."""
        sentinel = temp_sentinel_workspace["sentinel"]
        assert sentinel.is_storage_healthy(min_free_gb=1.0) is True
        assert sentinel.is_storage_healthy(min_free_gb=99999.0) is False


# ===========================================================================
# FEATURE 14: Self-Healing Cache Purging (Tiers 1 & 2)
# ===========================================================================

class TestFeature14SelfHealingCachePurging:
    """Tests directory auto-creation, stale git lock cleanup, and cache purging."""

    def test_heal_storage_creates_missing_vault_directories(self, temp_sentinel_workspace):
        """Tier 1.1: heal_storage_headroom re-creates missing obsidian and lora directories."""
        sentinel = temp_sentinel_workspace["sentinel"]
        obs_dir = temp_sentinel_workspace["obs_dir"]
        shutil.rmtree(obs_dir, ignore_errors=True)
        assert not obs_dir.exists()

        result = sentinel.heal_storage_headroom()
        assert obs_dir.exists()
        assert any(f"Created missing directory: {obs_dir}" in a for a in result["actions_taken"])

    def test_heal_storage_removes_stale_git_lock(self, temp_sentinel_workspace):
        """Tier 1.2: heal_storage_headroom removes stale .git/index.lock older than 10s."""
        sentinel = temp_sentinel_workspace["sentinel"]
        ws = temp_sentinel_workspace["workspace"]
        git_dir = ws / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)
        lock_file = git_dir / "index.lock"
        lock_file.write_text("STALE_LOCK")

        # Set modification time to 30 seconds ago
        old_time = time.time() - 30.0
        os.utime(lock_file, (old_time, old_time))

        result = sentinel.heal_storage_headroom()
        assert not lock_file.exists()
        assert any("Removed stale .git/index.lock" in a for a in result["actions_taken"])

    def test_heal_storage_purges_pycache_directories(self, temp_sentinel_workspace):
        """Tier 1.3: heal_storage_headroom purges __pycache__ directories."""
        sentinel = temp_sentinel_workspace["sentinel"]
        ws = temp_sentinel_workspace["workspace"]
        sub_mod = ws / "submodule"
        pycache_dir = sub_mod / "__pycache__"
        pycache_dir.mkdir(parents=True, exist_ok=True)
        (pycache_dir / "dummy.pyc").write_bytes(b"PYC_BYTECODE")

        assert pycache_dir.exists()
        result = sentinel.heal_storage_headroom()
        assert not pycache_dir.exists()

    def test_heal_storage_purges_pytest_cache_directories(self, temp_sentinel_workspace):
        """Tier 1.4: heal_storage_headroom purges .pytest_cache directories."""
        sentinel = temp_sentinel_workspace["sentinel"]
        ws = temp_sentinel_workspace["workspace"]
        pytest_cache = ws / ".pytest_cache"
        pytest_cache.mkdir(parents=True, exist_ok=True)
        (pytest_cache / "v").mkdir(parents=True, exist_ok=True)

        assert pytest_cache.exists()
        result = sentinel.heal_storage_headroom()
        assert not pytest_cache.exists()

    def test_heal_storage_purges_stale_log_files(self, temp_sentinel_workspace):
        """Tier 1.5: heal_storage_headroom purges log files > 3 days old while keeping fresh logs."""
        sentinel = temp_sentinel_workspace["sentinel"]
        ws = temp_sentinel_workspace["workspace"]
        log_dir = ws / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        stale_log = log_dir / "stale_run.log"
        fresh_log = log_dir / "fresh_run.log"
        stale_log.write_text("old logs")
        fresh_log.write_text("fresh logs")

        # Set stale log mtime to 5 days ago
        five_days_ago = time.time() - (5 * 86400)
        os.utime(stale_log, (five_days_ago, five_days_ago))

        result = sentinel.heal_storage_headroom()
        assert not stale_log.exists()
        assert fresh_log.exists()

    def test_check_and_heal_headroom_auto_recovers(self, temp_sentinel_workspace):
        """Tier 2.1: check_and_heal_headroom automatically executes healing if headroom needed."""
        sentinel = temp_sentinel_workspace["sentinel"]
        is_healthy, free_gb = sentinel.check_and_heal_headroom(min_free_gb=1.0)
        assert is_healthy is True
        assert free_gb >= 1.0

    def test_storage_sentinel_idempotency(self, temp_sentinel_workspace):
        """Tier 2.2: Running heal_storage_headroom consecutively causes zero errors."""
        sentinel = temp_sentinel_workspace["sentinel"]
        res1 = sentinel.heal_storage_headroom()
        res2 = sentinel.heal_storage_headroom()
        assert res1["is_healthy"] is True
        assert res2["is_healthy"] is True
