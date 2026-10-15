"""
tests/unit/test_git_worktree_manager.py
Unit and integration tests for GitWorktreeManager (.worktrees/<task_id> isolation, CI gating, and cleanup).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
import pytest

from canonical_sync_engine.sync.git_worktree_manager import (
    GitWorktreeManager,
    create_worktree,
    cleanup_worktree,
)


@pytest.fixture
def test_git_repo(tmp_path: Path) -> Path:
    """Initializes a real git repository for testing worktree lifecycle."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git_bin = shutil.which("git") or "/usr/bin/git"

    # Initialize git repo
    subprocess.run([git_bin, "init", "-b", "main"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run([git_bin, "config", "user.name", "Test Runner"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run([git_bin, "config", "user.email", "test@lauburu.local"], cwd=str(repo), check=True, capture_output=True)

    # Initial commit
    readme = repo / "README.md"
    readme.write_text("# Main Branch Content\n", encoding="utf-8")
    subprocess.run([git_bin, "add", "README.md"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run([git_bin, "commit", "-m", "Initial commit on main"], cwd=str(repo), check=True, capture_output=True)

    return repo


def test_create_worktree_basic(test_git_repo: Path):
    manager = GitWorktreeManager(repo_path=test_git_repo)
    task_id = "task_001_feature_test"

    wt_path_str = manager.create_worktree(task_id)
    wt_path = Path(wt_path_str)

    assert wt_path.exists()
    assert wt_path.is_dir()
    assert (wt_path / "README.md").exists()
    assert manager.is_worktree_active(task_id)

    # Path should be under .worktrees/<task_id>
    expected_path = test_git_repo / ".worktrees" / task_id
    assert wt_path.resolve() == expected_path.resolve()


def test_worktree_isolation(test_git_repo: Path):
    """Verifies that mutations in worktree do not affect main working tree."""
    manager = GitWorktreeManager(repo_path=test_git_repo)
    task_id = "task_002_isolation"

    wt_path = Path(manager.create_worktree(task_id))

    # Add a new file in the worktree
    new_file = wt_path / "worktree_only_file.txt"
    new_file.write_text("Isolated content in worktree", encoding="utf-8")

    # Main repository should NOT have this file
    main_file = test_git_repo / "worktree_only_file.txt"
    assert not main_file.exists()

    # Commit in worktree
    git_bin = shutil.which("git") or "/usr/bin/git"
    subprocess.run([git_bin, "add", "worktree_only_file.txt"], cwd=str(wt_path), check=True, capture_output=True)
    subprocess.run([git_bin, "commit", "-m", "Commit in worktree"], cwd=str(wt_path), check=True, capture_output=True)

    # Main repository still unaffected
    assert not main_file.exists()


def test_run_in_worktree(test_git_repo: Path):
    manager = GitWorktreeManager(repo_path=test_git_repo)
    task_id = "task_003_exec"

    manager.create_worktree(task_id)
    res = manager.run_in_worktree(task_id, ["python3", "-c", "import sys; print('HELLO_WORKTREE')"])

    assert res.returncode == 0
    assert "HELLO_WORKTREE" in res.stdout


def test_ci_verification_pass(test_git_repo: Path):
    manager = GitWorktreeManager(repo_path=test_git_repo)
    task_id = "task_004_ci_pass"

    manager.create_worktree(task_id)
    assert not manager.is_ci_passed(task_id)

    passed, summary, details = manager.run_ci_verification(
        task_id,
        test_command=["python3", "-c", "print('CI TEST SUCCESS'); exit(0)"],
    )

    assert passed is True
    assert "CI TEST SUCCESS" in summary
    assert details["passed"] is True
    assert manager.is_ci_passed(task_id)


def test_ci_verification_fail(test_git_repo: Path):
    manager = GitWorktreeManager(repo_path=test_git_repo)
    task_id = "task_005_ci_fail"

    manager.create_worktree(task_id)
    passed, summary, details = manager.run_ci_verification(
        task_id,
        test_command=["python3", "-c", "import sys; sys.stderr.write('CI FAILURE DETECTED'); sys.exit(1)"],
    )

    assert passed is False
    assert "CI FAILURE DETECTED" in summary
    assert details["passed"] is False
    assert not manager.is_ci_passed(task_id)


def test_gated_merge_rejected_without_ci(test_git_repo: Path):
    """Enforces zero direct mutations to production branches without automated CI passage."""
    manager = GitWorktreeManager(repo_path=test_git_repo)
    task_id = "task_006_unverified_merge"

    wt_path = Path(manager.create_worktree(task_id))
    (wt_path / "patch.txt").write_text("Unverified patch", encoding="utf-8")

    git_bin = shutil.which("git") or "/usr/bin/git"
    subprocess.run([git_bin, "add", "patch.txt"], cwd=str(wt_path), check=True, capture_output=True)
    subprocess.run([git_bin, "commit", "-m", "Unverified patch commit"], cwd=str(wt_path), check=True, capture_output=True)

    # Attempt merge without CI
    success, msg = manager.merge_to_production(task_id, target_branch="main", require_ci=True)
    assert success is False
    assert "Merge rejected" in msg
    assert "CI verification" in msg

    # Verify main branch was NOT mutated
    assert not (test_git_repo / "patch.txt").exists()


def test_gated_merge_success_with_ci(test_git_repo: Path):
    """Verifies that merge succeeds after passing CI verification."""
    manager = GitWorktreeManager(repo_path=test_git_repo)
    task_id = "task_007_verified_merge"

    wt_path = Path(manager.create_worktree(task_id))
    (wt_path / "verified_feature.txt").write_text("Verified code change", encoding="utf-8")

    git_bin = shutil.which("git") or "/usr/bin/git"
    subprocess.run([git_bin, "add", "verified_feature.txt"], cwd=str(wt_path), check=True, capture_output=True)
    subprocess.run([git_bin, "commit", "-m", "Verified feature commit"], cwd=str(wt_path), check=True, capture_output=True)

    # Run CI verification (passing)
    passed, _, _ = manager.run_ci_verification(
        task_id,
        test_command=["python3", "-c", "print('All unit tests passed'); exit(0)"],
    )
    assert passed is True

    # Now merge should succeed
    success, msg = manager.merge_to_production(task_id, target_branch="main", require_ci=True)
    assert success is True
    assert "Successfully merged" in msg

    # Verify main branch now contains the merged file
    assert (test_git_repo / "verified_feature.txt").exists()
    assert (test_git_repo / "verified_feature.txt").read_text() == "Verified code change"


def test_list_worktrees(test_git_repo: Path):
    manager = GitWorktreeManager(repo_path=test_git_repo)
    manager.create_worktree("task_alpha")
    manager.create_worktree("task_beta")

    worktrees = manager.list_worktrees()
    assert len(worktrees) >= 3  # main + task_alpha + task_beta

    managed_tasks = [w.get("task_id") for w in worktrees if w.get("is_managed")]
    assert "task_alpha" in managed_tasks
    assert "task_beta" in managed_tasks


def test_cleanup_worktree(test_git_repo: Path):
    manager = GitWorktreeManager(repo_path=test_git_repo)
    task_id = "task_to_cleanup"

    wt_path = Path(manager.create_worktree(task_id))
    assert wt_path.exists()
    assert manager.is_worktree_active(task_id)

    cleaned = manager.cleanup_worktree(task_id, force=True, delete_branch=True)
    assert cleaned is True
    assert not wt_path.exists()
    assert not manager.is_worktree_active(task_id)


def test_cleanup_all_worktrees(test_git_repo: Path):
    manager = GitWorktreeManager(repo_path=test_git_repo)
    manager.create_worktree("bulk_task_1")
    manager.create_worktree("bulk_task_2")
    manager.create_worktree("bulk_task_3")

    cleaned_count = manager.cleanup_all_worktrees(force=True, delete_branches=True)
    assert cleaned_count >= 3
    assert len([w for w in manager.list_worktrees() if w.get("is_managed")]) == 0


def test_stale_lock_healing_during_worktree_ops(test_git_repo: Path):
    """Verifies that stale locks (>10s) are automatically purged during worktree operations."""
    manager = GitWorktreeManager(repo_path=test_git_repo, stale_lock_timeout_sec=5.0)

    # Place stale lock in .git
    lock_file = test_git_repo / ".git" / "index.lock"
    lock_file.write_text("stale_lock", encoding="utf-8")
    past_time = time.time() - 20.0
    os.utime(str(lock_file), (past_time, past_time))

    # create_worktree should heal stale lock and succeed
    wt_path = manager.create_worktree("lock_heal_task")
    assert Path(wt_path).exists()
    assert not lock_file.exists()
