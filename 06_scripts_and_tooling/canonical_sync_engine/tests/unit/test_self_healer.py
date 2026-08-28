"""
tests/unit/test_self_healer.py
Unit and boundary tests for Rule 6.2 pre-flight self-healing engine.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
import pytest

from canonical_sync_engine.verification.invariants import REQUIRED_OBSIDIAN_WIKILINKS
from canonical_sync_engine.verification.self_healer import (
    CANONICAL_INDEX_MD_CONTENT,
    PreFlightSelfHealer,
    StorageSelfHealer,
)


def test_heal_missing_directories(tmp_path: Path):
    obs_dir = tmp_path / "obsidian_vault"
    pysp_dir = tmp_path / "lora_datasets"
    mem_dir = tmp_path / "04_data_and_memory"
    gdrive_cache = tmp_path / "data" / "gdrive_cache"

    healer = StorageSelfHealer(
        obsidian_path=obs_dir,
        pyspark_lora_path=pysp_dir,
        pyspark_memory_path=mem_dir,
        gdrive_fallback_path=gdrive_cache,
    )

    assert not obs_dir.exists()
    assert not pysp_dir.exists()

    actions = healer.heal_directories()
    assert len(actions) == 4
    assert obs_dir.is_dir()
    assert pysp_dir.is_dir()
    assert mem_dir.is_dir()
    assert gdrive_cache.is_dir()

    # Idempotence: subsequent call performs 0 actions
    actions_second = healer.heal_directories()
    assert actions_second == []


def test_heal_stale_git_lock(tmp_path: Path):
    git_dir = tmp_path / "git_repo"
    dot_git = git_dir / ".git"
    dot_git.mkdir(parents=True)
    lock_file = dot_git / "index.lock"
    lock_file.write_text("lock", encoding="utf-8")

    # Set mtime to 30 seconds in the past
    past_time = time.time() - 30.0
    os.utime(str(lock_file), (past_time, past_time))

    healer = StorageSelfHealer(
        git_repo_path=git_dir,
        stale_lock_timeout_sec=10.0,
    )

    actions = healer.heal_git_locks(force=False)
    assert len(actions) == 1
    assert "Removed stale git index lock" in actions[0]
    assert not lock_file.exists()


def test_skip_active_git_lock(tmp_path: Path):
    git_dir = tmp_path / "git_repo"
    dot_git = git_dir / ".git"
    dot_git.mkdir(parents=True)
    lock_file = dot_git / "index.lock"
    lock_file.write_text("lock", encoding="utf-8")

    # Lock is current (0 seconds old)
    healer = StorageSelfHealer(
        git_repo_path=git_dir,
        stale_lock_timeout_sec=10.0,
    )

    actions = healer.heal_git_locks(force=False)
    assert len(actions) == 1
    assert "Skipped active git index lock" in actions[0]
    assert lock_file.exists()

    # Force flag removes even active lock
    actions_force = healer.heal_git_locks(force=True)
    assert len(actions_force) == 1
    assert "Removed stale git index lock" in actions_force[0]
    assert not lock_file.exists()


def test_heal_missing_obsidian_index(tmp_path: Path):
    obs_dir = tmp_path / "obsidian_vault"
    obs_dir.mkdir(parents=True)
    index_file = obs_dir / "Index.md"

    healer = StorageSelfHealer(obsidian_path=obs_dir)

    actions = healer.heal_obsidian_index()
    assert len(actions) == 1
    assert "Recreated Obsidian master Index.md" in actions[0]
    assert index_file.exists()

    content = index_file.read_text(encoding="utf-8")
    for link in REQUIRED_OBSIDIAN_WIKILINKS:
        assert link in content


def test_heal_corrupt_obsidian_index(tmp_path: Path):
    obs_dir = tmp_path / "obsidian_vault"
    obs_dir.mkdir(parents=True)
    index_file = obs_dir / "Index.md"
    index_file.write_text("# Partial Index Without Links", encoding="utf-8")

    healer = StorageSelfHealer(obsidian_path=obs_dir)

    actions = healer.heal_obsidian_index()
    assert len(actions) == 1
    assert "Recreated Obsidian master Index.md" in actions[0]

    content = index_file.read_text(encoding="utf-8")
    for link in REQUIRED_OBSIDIAN_WIKILINKS:
        assert link in content

    # Idempotent call on healthy index
    actions_second = healer.heal_obsidian_index()
    assert actions_second == []


def test_heal_all_composite(tmp_path: Path):
    obs_dir = tmp_path / "obsidian_vault"
    pysp_dir = tmp_path / "lora_datasets"
    git_dir = tmp_path / "git_repo"
    dot_git = git_dir / ".git"
    dot_git.mkdir(parents=True)
    lock_file = dot_git / "index.lock"
    lock_file.write_text("lock", encoding="utf-8")
    past_time = time.time() - 20.0
    os.utime(str(lock_file), (past_time, past_time))

    healer = PreFlightSelfHealer(
        obsidian_path=obs_dir,
        pyspark_lora_path=pysp_dir,
        git_repo_path=git_dir,
        stale_lock_timeout_sec=5.0,
    )

    actions = healer.heal_all()
    assert len(actions) >= 3  # Directories + Lock + Index.md
    assert obs_dir.is_dir()
    assert (obs_dir / "Index.md").is_file()
    assert not lock_file.exists()


def test_heal_disk_headroom_purge(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)
    cache_dir = project_dir / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "temp.pyc").write_text("code", encoding="utf-8")

    stale_log = project_dir / "old.log"
    stale_log.write_text("log content", encoding="utf-8")
    past_time = time.time() - (8 * 86400)  # 8 days old
    os.utime(str(stale_log), (past_time, past_time))

    healer = StorageSelfHealer(
        git_repo_path=project_dir,
        cleanup_target_paths=[project_dir],
    )

    # Trigger headroom purge with high threshold
    actions = healer.heal_disk_headroom(min_free_gb=999999.0)
    assert len(actions) == 1
    assert "Purged" in actions[0]
    assert not cache_dir.exists()
    assert not stale_log.exists()

