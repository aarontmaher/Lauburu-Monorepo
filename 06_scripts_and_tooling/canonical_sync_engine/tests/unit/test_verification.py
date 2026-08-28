"""
tests/unit/test_verification.py
Unit and boundary tests for fast-path checker, headroom validator, storage invariants, and StorageVerifier.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from canonical_sync_engine.verification.fast_path import (
    FastPathChecker,
    FastPathResult,
    fast_path_check,
    is_storage_healthy,
)
from canonical_sync_engine.verification.headroom import (
    HeadroomStatus,
    HeadroomValidator,
    check_disk_headroom,
    check_multi_mount_headroom,
)
from canonical_sync_engine.verification.invariants import (
    REQUIRED_OBSIDIAN_WIKILINKS,
    StorageInvariantValidator,
    VaultInvariantResult,
)
from canonical_sync_engine.verification import StorageVerifier


# ---------------------------------------------------------------------------
# 1. Fast-Path Health Checker Tests (< 3ms)
# ---------------------------------------------------------------------------

def test_fast_path_healthy_sandbox(mock_vault_sandbox):
    obs = mock_vault_sandbox["obsidian"]
    pysp = mock_vault_sandbox["pyspark"]
    git_dir = mock_vault_sandbox["git"]

    res = fast_path_check(
        obsidian_path=obs,
        pyspark_path=pysp,
        disk_check_path=git_dir,
        min_free_gb=0.1,
    )
    assert res.is_healthy is True
    assert res.obsidian_ok is True
    assert res.pyspark_ok is True
    assert res.disk_free_gb > 0.0
    assert res.duration_ms < 3.0  # Must execute strictly in sub-3ms per Rule 6.3


def test_fast_path_missing_obsidian(tmp_path):
    pysp = tmp_path / "lora_datasets"
    pysp.mkdir()

    res = fast_path_check(
        obsidian_path=tmp_path / "non_existent_obsidian",
        pyspark_path=pysp,
        min_free_gb=0.1,
    )
    assert res.is_healthy is False
    assert res.obsidian_ok is False
    assert res.pyspark_ok is True
    assert not is_storage_healthy(
        obsidian_path=tmp_path / "non_existent_obsidian",
        pyspark_path=pysp,
        min_free_gb=0.1,
    )


def test_fast_path_missing_pyspark(tmp_path):
    obs = tmp_path / "obsidian_vault"
    obs.mkdir()

    res = fast_path_check(
        obsidian_path=obs,
        pyspark_path=tmp_path / "non_existent_pyspark",
        min_free_gb=0.1,
    )
    assert res.is_healthy is False
    assert res.obsidian_ok is True
    assert res.pyspark_ok is False


def test_fast_path_low_disk_headroom(mock_vault_sandbox):
    obs = mock_vault_sandbox["obsidian"]
    pysp = mock_vault_sandbox["pyspark"]
    git_dir = mock_vault_sandbox["git"]

    # Require an impossibly high disk headroom to trigger failure
    res = fast_path_check(
        obsidian_path=obs,
        pyspark_path=pysp,
        disk_check_path=git_dir,
        min_free_gb=999999.0,
    )
    assert res.is_healthy is False
    assert res.obsidian_ok is True
    assert res.pyspark_ok is True
    assert res.disk_free_gb < 999999.0


def test_fast_path_checker_class(mock_vault_sandbox):
    obs = mock_vault_sandbox["obsidian"]
    pysp = mock_vault_sandbox["pyspark"]
    git_dir = mock_vault_sandbox["git"]

    checker = FastPathChecker(
        obsidian_path=obs,
        pyspark_path=pysp,
        git_path=git_dir,
        min_free_gb=0.1,
    )
    assert checker.is_healthy() is True
    res = checker.check()
    assert isinstance(res, FastPathResult)
    assert res.is_healthy is True


# ---------------------------------------------------------------------------
# 2. Disk Headroom & Inode Capacity Validator Tests
# ---------------------------------------------------------------------------

def test_check_disk_headroom_healthy(tmp_path):
    status = check_disk_headroom(tmp_path, min_headroom_gb=0.1)
    assert status.is_sufficient is True
    assert status.free_gb > 0.1
    assert status.total_gb > 0.0
    assert status.percent_free > 0.0
    assert status.violation_message is None
    d = status.to_dict()
    assert d["is_sufficient"] is True


def test_check_disk_headroom_violation(tmp_path):
    status = check_disk_headroom(tmp_path, min_headroom_gb=999999.0)
    assert status.is_sufficient is False
    assert status.violation_message is not None
    assert "below required headroom threshold" in status.violation_message


def test_check_multi_mount_headroom(tmp_path):
    dir_a = tmp_path / "mount_a"
    dir_b = tmp_path / "mount_b"
    dir_a.mkdir()
    dir_b.mkdir()

    statuses = check_multi_mount_headroom([dir_a, dir_b], min_headroom_gb=0.1)
    assert len(statuses) == 2
    assert str(dir_a) in statuses
    assert str(dir_b) in statuses


def test_headroom_validator_class(tmp_path):
    validator = HeadroomValidator(min_headroom_gb=0.1, paths=[tmp_path])
    all_ok, lowest_free, violations = validator.check()
    assert all_ok is True
    assert lowest_free > 0.1
    assert violations == []


# ---------------------------------------------------------------------------
# 3. Storage Invariants Validator Tests (Rule 6.1)
# ---------------------------------------------------------------------------

def test_storage_invariant_validator_all_healthy(mock_vault_sandbox):
    validator = StorageInvariantValidator(
        obsidian_path=mock_vault_sandbox["obsidian"],
        pyspark_path=mock_vault_sandbox["pyspark"],
        pyspark_memory_path=mock_vault_sandbox["memory"],
        git_path=mock_vault_sandbox["git"],
        gdrive_path=mock_vault_sandbox["gdrive_mount"],
        gdrive_cache_path=mock_vault_sandbox["gdrive_cache"],
        min_headroom_gb=0.1,
    )
    report = validator.validate_all()
    assert report.is_healthy is True
    assert report.obsidian_healthy is True
    assert report.pyspark_healthy is True
    assert report.git_healthy is True
    assert report.gdrive_healthy is True
    assert report.violations == []


def test_storage_invariant_obsidian_missing_index(mock_vault_sandbox):
    index_file = mock_vault_sandbox["obsidian"] / "Index.md"
    index_file.unlink()

    validator = StorageInvariantValidator(
        obsidian_path=mock_vault_sandbox["obsidian"],
        pyspark_path=mock_vault_sandbox["pyspark"],
        git_path=mock_vault_sandbox["git"],
        gdrive_path=mock_vault_sandbox["gdrive_mount"],
        min_headroom_gb=0.1,
    )
    res = validator.validate_obsidian()
    assert res.is_healthy is False
    assert any("Index.md missing" in v for v in res.violations)


def test_storage_invariant_obsidian_empty_index(mock_vault_sandbox):
    index_file = mock_vault_sandbox["obsidian"] / "Index.md"
    index_file.write_text("", encoding="utf-8")

    validator = StorageInvariantValidator(
        obsidian_path=mock_vault_sandbox["obsidian"],
        pyspark_path=mock_vault_sandbox["pyspark"],
        git_path=mock_vault_sandbox["git"],
        gdrive_path=mock_vault_sandbox["gdrive_mount"],
        min_headroom_gb=0.1,
    )
    res = validator.validate_obsidian()
    assert res.is_healthy is False
    assert any("empty (0 bytes)" in v for v in res.violations)


def test_storage_invariant_obsidian_missing_wikilinks(mock_vault_sandbox):
    index_file = mock_vault_sandbox["obsidian"] / "Index.md"
    index_file.write_text("# Obsidian Index\n- [[Index]]\n", encoding="utf-8")

    validator = StorageInvariantValidator(
        obsidian_path=mock_vault_sandbox["obsidian"],
        pyspark_path=mock_vault_sandbox["pyspark"],
        git_path=mock_vault_sandbox["git"],
        gdrive_path=mock_vault_sandbox["gdrive_mount"],
        min_headroom_gb=0.1,
    )
    res = validator.validate_obsidian()
    assert res.is_healthy is False
    assert any("missing mandatory Wikilink" in v for v in res.violations)


def test_storage_invariant_git_stale_lock(mock_vault_sandbox):
    lock_file = mock_vault_sandbox["git"] / ".git" / "index.lock"
    lock_file.write_text("lock", encoding="utf-8")

    validator = StorageInvariantValidator(
        obsidian_path=mock_vault_sandbox["obsidian"],
        pyspark_path=mock_vault_sandbox["pyspark"],
        git_path=mock_vault_sandbox["git"],
        gdrive_path=mock_vault_sandbox["gdrive_mount"],
        min_headroom_gb=0.1,
    )
    res = validator.validate_git()
    assert res.is_healthy is False
    assert any("Git index lock present" in v for v in res.violations)


def test_storage_invariant_gdrive_unavailable(tmp_path):
    validator = StorageInvariantValidator(
        obsidian_path=tmp_path / "obs",
        pyspark_path=tmp_path / "pysp",
        git_path=tmp_path / "git",
        gdrive_path=tmp_path / "non_existent_mount",
        gdrive_cache_path=tmp_path / "non_existent_cache",
        min_headroom_gb=0.1,
    )
    res = validator.validate_gdrive()
    assert res.is_healthy is False
    assert any("Google Drive unavailable" in v for v in res.violations)


# ---------------------------------------------------------------------------
# 4. StorageVerifier Composite Orchestrator Tests
# ---------------------------------------------------------------------------

def test_storage_verifier_composite_workflow(mock_vault_sandbox):
    verifier = StorageVerifier(
        obsidian_vault_path=mock_vault_sandbox["obsidian"],
        pyspark_dataset_path=mock_vault_sandbox["pyspark"],
        pyspark_memory_path=mock_vault_sandbox["memory"],
        git_working_tree_path=mock_vault_sandbox["git"],
        gdrive_mount_path=mock_vault_sandbox["gdrive_mount"],
        gdrive_fallback_cache_path=mock_vault_sandbox["gdrive_cache"],
        min_headroom_gb=0.1,
    )
    assert verifier.fast_path_check() is True
    assert verifier.fast_path() is True

    headroom_ok, free_gb, h_violations = verifier.validate_headroom()
    assert headroom_ok is True
    assert h_violations == []

    inv_ok, inv_violations, vault_statuses = verifier.validate_invariants()
    assert inv_ok is True
    assert inv_violations == []

    report = verifier.full_verification(scan_remote_nodes=False, auto_heal=True)
    assert report.is_healthy is True
    assert report.obsidian_healthy is True
    assert report.pyspark_healthy is True
    assert report.git_healthy is True
    assert report.gdrive_healthy is True
    assert "L1" in report.node_reports


def test_fast_path_100_iterations_benchmark(mock_vault_sandbox):
    """Benchmarks fast-path check across 100 runs to guarantee <3.0ms constraint."""
    obs = mock_vault_sandbox["obsidian"]
    pysp = mock_vault_sandbox["pyspark"]
    git_dir = mock_vault_sandbox["git"]

    durations = []
    for _ in range(100):
        res = fast_path_check(
            obsidian_path=obs,
            pyspark_path=pysp,
            disk_check_path=git_dir,
            min_free_gb=0.1,
        )
        assert res.is_healthy is True
        durations.append(res.duration_ms)

    avg_duration = sum(durations) / len(durations)
    max_duration = max(durations)
    assert avg_duration < 1.0  # Average is sub-millisecond
    assert max_duration < 3.0  # Strict Rule 6.3 bound


def test_storage_invariant_pyspark_corrupt_jsonl(mock_vault_sandbox):
    """Tests detection of malformed JSON lines in dataset directory."""
    corrupt_file = mock_vault_sandbox["pyspark"] / "corrupt.jsonl"
    corrupt_file.write_text("NOT_VALID_JSON\n", encoding="utf-8")

    validator = StorageInvariantValidator(
        obsidian_path=mock_vault_sandbox["obsidian"],
        pyspark_path=mock_vault_sandbox["pyspark"],
        git_path=mock_vault_sandbox["git"],
        gdrive_path=mock_vault_sandbox["gdrive_mount"],
        min_headroom_gb=0.1,
    )
    res = validator.validate_pyspark()
    assert res.is_healthy is False
    assert any("Corrupt JSONL" in v for v in res.violations)

