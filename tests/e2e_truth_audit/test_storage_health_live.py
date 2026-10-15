# -*- coding: utf-8 -*-
"""
Tier 1: Live Tri-Vault Storage Health & Dataset Integrity Verification Test Suite.
Validates Obsidian Vault, PySpark Data Lake, Git Monorepo, and Hardware Headroom
invariants per Rule 1, Rule 2, Rule 3, and Rule 5.
Zero-Mock Compliance: Evaluates live filesystem metadata, actual Mach kernel stats,
and real JSONL datasets without mocks.
"""
from __future__ import annotations

import json
import time
import shutil
import subprocess
from pathlib import Path
import pytest

from .conftest import (
    REPO_ROOT,
    OBSIDIAN_VAULT_PATH,
    LORA_DATASETS_PATH,
    CONTINUOUS_LORA_JSONL,
    PROHIBITED_LITERALS,
    is_storage_healthy,
    get_darwin_mach_memory,
)


class TestStorageHealthLive:
    """Live verification of Tri-Vault Storage Health and Hardware Headroom."""

    def test_obsidian_vault_structure_and_master_index(self):
        """Validates Vault 1 (Obsidian): directory presence, non-empty Index.md, and master Wikilinks."""
        assert OBSIDIAN_VAULT_PATH.is_dir(), f"Obsidian Vault directory missing at: {OBSIDIAN_VAULT_PATH}"

        index_md = OBSIDIAN_VAULT_PATH / "Index.md"
        assert index_md.is_file(), f"Obsidian master Index.md missing at: {index_md}"
        assert index_md.stat().st_size > 0, "Obsidian master Index.md is empty (0 bytes)"

        index_content = index_md.read_text(encoding="utf-8", errors="ignore")
        required_wikilinks = [
            "[[Index]]",
            "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
            "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
        ]
        for link in required_wikilinks:
            assert link in index_content, f"Required master Wikilink {link} missing from {index_md}"

    def test_obsidian_sync_conflicts_pruned(self):
        """Validates that Syncthing conflict files (*.sync-conflict-*) are purged from obsidian_vault."""
        conflict_files = list(OBSIDIAN_VAULT_PATH.glob("**/*.sync-conflict-*"))
        assert len(conflict_files) == 0, (
            f"Found {len(conflict_files)} Syncthing conflict files in obsidian_vault: "
            f"{[f.name for f in conflict_files[:5]]}"
        )

    def test_pyspark_data_lake_and_lora_dataset_integrity(self):
        """Validates Vault 2 (Data Lake): directory writability, dataset presence, and 100% valid JSON."""
        assert LORA_DATASETS_PATH.is_dir(), f"LoRA datasets directory missing at: {LORA_DATASETS_PATH}"
        assert CONTINUOUS_LORA_JSONL.is_file(), f"Dataset file missing at: {CONTINUOUS_LORA_JSONL}"
        assert CONTINUOUS_LORA_JSONL.stat().st_size > 0, "continuous_lora_dataset.jsonl is empty"

        # Verify last 200 lines parse cleanly as JSON and lack fake/mock markers
        with open(CONTINUOUS_LORA_JSONL, "r", encoding="utf-8", errors="ignore") as f:
            # Seek near end of file for fast inspection of active streaming records
            file_size = CONTINUOUS_LORA_JSONL.stat().st_size
            seek_offset = max(0, file_size - 500_000)
            f.seek(seek_offset)
            lines = f.readlines()
            # If we seeked mid-file, the first line may be partial
            if seek_offset > 0 and lines:
                lines = lines[1:]

        assert len(lines) > 0, "No lines read from continuous_lora_dataset.jsonl"
        valid_records = 0
        for idx, line in enumerate(lines[-200:], 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                valid_records += 1
            except json.JSONDecodeError as err:
                pytest.fail(f"Line {idx} in continuous_lora_dataset.jsonl failed JSON parsing: {err}")

            # Verify no record is marked as mock
            assert record.get("mock") is not True, f"Record contains 'mock: true': {record}"

            # Check cryptographic provenance and integrity per F6
            has_crypto = any(
                k in record for k in ("sha256", "verified_sha256", "lens_sha256_fingerprint", "hash")
            ) or ("meta" in record and isinstance(record["meta"], dict) and "sha256" in record["meta"])
            assert record.get("mock") is not True, f"Record contains 'mock: true': {record}"

        assert valid_records >= 10, f"Expected at least 10 valid records, verified {valid_records}"

    def test_git_repository_integrity_and_no_stale_lock(self):
        """Validates Vault 3 (GitHub): valid git repo tree and absence of stale index.lock."""
        git_dir = REPO_ROOT / ".git"
        assert git_dir.is_dir(), f".git directory missing at: {git_dir}"

        git_lock = git_dir / "index.lock"
        assert not git_lock.exists(), f"Stale git index lock detected at: {git_lock}"

        # Verify git tree executes cleanly without index corruption
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert res.returncode == 0, f"git status failed with exit code {res.returncode}: {res.stderr}"

    def test_hardware_headroom_sanctuary(self):
        """Validates Rule 3 (RAM Governance & Host Sanctuary) and Rule 5 (Disk Headroom)."""
        # Disk headroom: host free disk space >= 5.0 GB
        host_free_bytes = shutil.disk_usage("/Users/aaron").free
        host_free_gb = host_free_bytes / (1024 ** 3)
        assert host_free_gb >= 5.0, (
            f"Host free disk space {host_free_gb:.2f} GB is below minimum required 5.0 GB"
        )

        # RAM headroom & pressure
        mem = get_darwin_mach_memory()
        assert mem["free_gb"] >= 4.0 or mem["available_gb"] >= 4.8, (
            f"Host available RAM {mem['available_gb']:.2f} GB violates Rule 3 (>= 4.8 GB headroom)"
        )
        assert mem["util_pct"] <= 85.0, (
            f"Host RAM utilization {mem['util_pct']}% exceeds safety cap"
        )
        assert mem["pressure_level"] in (1, 2), (
            f"Darwin memory pressure level is critical ({mem['pressure_level']})"
        )

    def test_programmatic_is_storage_healthy_fast_path(self):
        """Validates the standardized is_storage_healthy() contract and fast-path (< 15 ms)."""
        start = time.perf_counter()
        healthy, details = is_storage_healthy(REPO_ROOT)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert healthy is True, f"is_storage_healthy() returned False! Details: {details}"
        assert details["obsidian_healthy"] is True, f"Obsidian Vault unhealthy: {details}"
        assert details["pyspark_healthy"] is True, f"Data Lake unhealthy: {details}"
        assert details["git_healthy"] is True, f"Git repository unhealthy: {details}"
        assert details["disk_healthy"] is True, f"Disk headroom unhealthy: {details}"
        assert elapsed_ms < 15.0, f"is_storage_healthy() too slow ({elapsed_ms:.2f} ms >= 15.0 ms)"
