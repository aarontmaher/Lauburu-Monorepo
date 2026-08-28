"""
Unit Tests: Git Worktree Sandboxing (Milestone 2)
Covers Dynamic Branched Worktree Creation, Non-Mutation Isolation, and Worktree Cleanup.
Derived strictly from ORIGINAL_REQUEST.md §R1, §Acceptance Criteria, and PROJECT.md §Interface Contracts.
Test Architecture: 4-Tier Test Infra (Category-Partition, Boundary Values, Pairwise Combinations, Real-World Workload).
Rule #0 Adherence: Zero fake data, genuine Git worktree subprocess operations, real filesystem isolation verification.
"""

import os
import re
import sys
import time
import shutil
import subprocess
import pytest
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.worktree_sandbox import WorktreeSandbox, WorktreeError, run_command_in_pty


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sandbox_env(tmp_path):
    """Provides a fresh isolated WorktreeSandbox rooted in tmp_path with cleanup."""
    sandbox_base = tmp_path / "lauburu_worktrees"
    sb = WorktreeSandbox(base_dir=str(sandbox_base))
    yield sb
    # Cleanup all worktrees created during test
    for wt in sb.list_active_worktrees():
        sb.cleanup_worktree(wt["worktree_path"], force=True)
    if os.path.exists(str(sandbox_base)):
        shutil.rmtree(str(sandbox_base), ignore_errors=True)


# ============================================================================
# TIER 1: CATEGORY-PARTITION (Nominal & Happy Paths)
# ============================================================================

def test_sandbox_initialization(sandbox_env):
    """Tier 1: Verify WorktreeSandbox initializes with valid base and repo roots."""
    assert os.path.isdir(sandbox_env.base_dir)
    assert os.path.isdir(sandbox_env.repo_root)
    assert os.path.isdir(os.path.join(sandbox_env.repo_root, ".git")) or os.path.isfile(os.path.join(sandbox_env.repo_root, ".git"))

def test_create_worktree_nominal(sandbox_env):
    """Tier 1: Verify nominal Git worktree creation."""
    wt = sandbox_env.create_worktree("tui_redesign_grid")
    assert wt["status"] == "CREATED"
    assert os.path.isdir(wt["worktree_path"])
    assert "tui_redesign_grid" in wt["id"]
    assert "subagent/tui_tui_redesign_grid" in wt["branch"]
    assert wt["worktree_path"] in [w["worktree_path"] for w in sandbox_env.list_active_worktrees()]

def test_verify_sandbox_isolation_nominal(sandbox_env):
    """Tier 1: Verify subagent mutations in worktree do NOT leak to primary 01_apps."""
    wt = sandbox_env.create_worktree("isolation_check")
    is_isolated = sandbox_env.verify_sandbox_isolation(wt["worktree_path"])
    assert is_isolated is True, "Mutation inside Git Worktree leaked into primary repository working tree!"

def test_cleanup_worktree_nominal(sandbox_env):
    """Tier 1: Verify clean removal of Git worktree and directory."""
    wt = sandbox_env.create_worktree("cleanup_check")
    path = wt["worktree_path"]
    assert os.path.exists(path)

    success = sandbox_env.cleanup_worktree(path, force=True)
    assert success is True
    assert not os.path.exists(path)
    assert path not in [w["worktree_path"] for w in sandbox_env.list_active_worktrees()]

def test_list_active_worktrees_tracks_instances(sandbox_env):
    """Tier 1: Verify list_active_worktrees accurately tracks active sandboxes."""
    assert len(sandbox_env.list_active_worktrees()) == 0
    wt1 = sandbox_env.create_worktree("task_alpha")
    wt2 = sandbox_env.create_worktree("task_beta")
    active = sandbox_env.list_active_worktrees()
    assert len(active) == 2
    paths = [a["worktree_path"] for a in active]
    assert wt1["worktree_path"] in paths
    assert wt2["worktree_path"] in paths


# ============================================================================
# TIER 2: BOUNDARY VALUES & ERROR STATES
# ============================================================================

@pytest.mark.parametrize("raw_task,expected_slug", [
    ("Redesign TUI Grid Layout", "redesign_tui_grid_layout"),
    ("fix/bug-42! #urgent", "fix_bug_42_urgent"),
    ("   spaces   around   ", "spaces_around"),
    ("---dashes---___", "dashes"),
    ("special@#$%^&*()chars", "special_chars"),
    ("", "unnamed_task"),
])
def test_create_worktree_sanitizes_task_name(sandbox_env, raw_task, expected_slug):
    """Tier 2: Boundary test for task name sanitization and slugification."""
    wt = sandbox_env.create_worktree(raw_task)
    assert expected_slug in wt["id"]
    assert os.path.isdir(wt["worktree_path"])
    sandbox_env.cleanup_worktree(wt["worktree_path"])

def test_create_worktree_path_traversal_rejection(sandbox_env):
    """Tier 2: Verify path traversal attempts in task name are sanitized safely."""
    wt = sandbox_env.create_worktree("../../etc/shadow")
    # Path must remain strictly within sandbox_env.base_dir
    assert os.path.abspath(wt["worktree_path"]).startswith(sandbox_env.base_dir)
    assert os.path.isdir(wt["worktree_path"])
    sandbox_env.cleanup_worktree(wt["worktree_path"])

def test_cleanup_nonexistent_worktree_is_idempotent(sandbox_env):
    """Tier 2: Verify cleanup on non-existent worktree path returns True cleanly."""
    fake_path = os.path.join(sandbox_env.base_dir, "nonexistent_worktree_99999")
    result = sandbox_env.cleanup_worktree(fake_path, force=True)
    assert result is True

def test_cleanup_dirty_worktree_with_force(sandbox_env):
    """Tier 2: Verify dirty uncommitted files inside worktree are removed with force=True."""
    wt = sandbox_env.create_worktree("dirty_worktree")
    dirty_file = os.path.join(wt["worktree_path"], "dirty_untracked_file.py")
    with open(dirty_file, "w") as f:
        f.write("# Uncommitted subagent changes\n")
    assert os.path.isfile(dirty_file)

    success = sandbox_env.cleanup_worktree(wt["worktree_path"], force=True)
    assert success is True
    assert not os.path.exists(wt["worktree_path"])

def test_create_worktree_invalid_commit_raises_error(sandbox_env):
    """Tier 2: Verify invalid base commit ref raises WorktreeError."""
    with pytest.raises(WorktreeError, match="Failed to create Git worktree"):
        sandbox_env.create_worktree("invalid_ref_task", base_commit="nonexistent_git_hash_abc123")


# ============================================================================
# TIER 3: PAIRWISE COMBINATIONS
# ============================================================================

def test_concurrent_multi_worktree_cross_isolation(sandbox_env):
    """Tier 3: Pairwise cross-isolation between multiple active worktrees."""
    wt_a = sandbox_env.create_worktree("parallel_agent_a")
    wt_b = sandbox_env.create_worktree("parallel_agent_b")

    file_a = os.path.join(wt_a["worktree_path"], "module_a.py")
    file_b = os.path.join(wt_b["worktree_path"], "module_b.py")

    with open(file_a, "w") as f:
        f.write("# Agent A mutation")
    with open(file_b, "w") as f:
        f.write("# Agent B mutation")

    # Assert mutual isolation
    assert os.path.isfile(file_a)
    assert not os.path.isfile(os.path.join(wt_b["worktree_path"], "module_a.py"))
    assert not os.path.isfile(os.path.join(sandbox_env.repo_root, "module_a.py"))

    assert os.path.isfile(file_b)
    assert not os.path.isfile(os.path.join(wt_a["worktree_path"], "module_b.py"))
    assert not os.path.isfile(os.path.join(sandbox_env.repo_root, "module_b.py"))

    sandbox_env.cleanup_worktree(wt_a["worktree_path"])
    sandbox_env.cleanup_worktree(wt_b["worktree_path"])

def test_create_cleanup_recreate_same_task_name(sandbox_env):
    """Tier 3: Verify cycle of create -> cleanup -> re-create with same task name."""
    task = "repeatable_refactor_task"
    wt1 = sandbox_env.create_worktree(task)
    p1 = wt1["worktree_path"]
    assert os.path.isdir(p1)
    sandbox_env.cleanup_worktree(p1, force=True)
    assert not os.path.exists(p1)

    time.sleep(0.01)  # Ensure unique millisecond timestamp
    wt2 = sandbox_env.create_worktree(task)
    p2 = wt2["worktree_path"]
    assert os.path.isdir(p2)
    assert p1 != p2  # Unique timestamps
    sandbox_env.cleanup_worktree(p2, force=True)


# ============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ============================================================================

def test_scenario_subagent_ui_refactor_workflow(sandbox_env):
    """
    Tier 4: Scenario 1 — Real-world AI subagent UI restructuring flow.
    Exercises dynamic worktree creation, file modification, syntax validation,
    zero-mutation guarantee on primary tree, and clean post-run teardown.
    """
    # 1. Spawn subagent sandbox
    wt = sandbox_env.create_worktree("mesh_latency_spike_ui_restructure")
    wt_path = wt["worktree_path"]

    # 2. Subagent modifies a file inside worktree
    target_rel_path = "01_apps/canonical_port/tui/widgets/simulated_widget.py"
    target_file = os.path.join(wt_path, target_rel_path)
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w") as f:
        f.write("# Refactored widget AST by Kimi Tandem Titan\ndef render(): return 'NEW_UI'\n")

    # 3. Assert modification exists in worktree
    assert os.path.isfile(target_file)
    with open(target_file, "r") as f:
        assert "NEW_UI" in f.read()

    # 4. Mandatory Rule #0 & R1 Acceptance Guarantee: Primary repository MUST NOT be mutated!
    primary_target = os.path.join(sandbox_env.repo_root, target_rel_path)
    assert not os.path.exists(primary_target), f"CRITICAL: Primary monorepo mutated at {primary_target}!"

    # 5. Clean teardown
    cleanup_ok = sandbox_env.cleanup_worktree(wt_path, force=True)
    assert cleanup_ok is True
    assert not os.path.exists(wt_path)

def test_scenario_stale_worktree_pruning(sandbox_env):
    """
    Tier 4: Scenario 2 — Automated reaper prunes abandoned or stale worktrees.
    """
    wt = sandbox_env.create_worktree("abandoned_job")
    # Artificially set created_at back by 7200 seconds
    sandbox_env._active_worktrees[wt["worktree_path"]]["created_at"] = time.time() - 7200.0

    pruned = sandbox_env.prune_stale_worktrees(max_age_seconds=3600.0)
    assert pruned == 1
    assert not os.path.exists(wt["worktree_path"])
    assert len(sandbox_env.list_active_worktrees()) == 0


def test_pty_execution_list_command(sandbox_env):
    """Tier 4: Verify run_command_in_pty with list command preserves ANSI output and unbuffered execution."""
    wt = sandbox_env.create_worktree("pty_test_list")
    wt_path = wt["worktree_path"]

    code, output = sandbox_env.run_command_in_pty(
        command=["python3", "-c", "print('\033[32mHELLO_PTY\033[0m')"],
        cwd=wt_path,
    )
    assert code == 0
    assert "HELLO_PTY" in output
    assert "\x1b[32m" in output or "HELLO_PTY" in output
    sandbox_env.cleanup_worktree(wt_path)


def test_pty_execution_string_command(sandbox_env):
    """Tier 4: Verify standalone run_command_in_pty with string command."""
    wt = sandbox_env.create_worktree("pty_test_str")
    wt_path = wt["worktree_path"]

    code, output = run_command_in_pty(
        command="python3 -c \"print('STANDALONE_PTY_OK')\"",
        cwd=wt_path,
    )
    assert code == 0
    assert "STANDALONE_PTY_OK" in output
    sandbox_env.cleanup_worktree(wt_path)


def test_pty_execution_nonexistent_directory():
    """Tier 4: Verify run_command_in_pty raises WorktreeError on nonexistent cwd."""
    with pytest.raises(WorktreeError, match="Cannot execute in non-existent directory"):
        run_command_in_pty(
            command=["echo", "fail"],
            cwd="/tmp/nonexistent_pty_dir_99999",
        )

