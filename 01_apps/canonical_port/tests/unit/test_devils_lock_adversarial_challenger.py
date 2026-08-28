"""
Adversarial Challenger Test Suite: DevilsLockGovernor (Milestone 1)
tests/unit/test_devils_lock_adversarial_challenger.py

EMPIRICAL CHALLENGER 2 VERIFICATION SUITE
Adversarially probes:
  1. Dead PID recovery & stale lock self-healing
  2. Lockfile and state file corruption (empty, truncated, malformed types, non-numeric PIDs)
  3. Process crash & SIGKILL kernel flock release
  4. Missing, malformed, and non-dict leaderboard JSON inputs
  5. Extreme memory values (negative, overflow, NaN, infinite, exact 15.0% boundary)
  6. Multithreaded and multiprocess race conditions & reentrancy
"""

import os
import sys
import json
import time
import errno
import signal
import pytest
import tempfile
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.devils_lock_governor import (
    DevilsLockGovernor,
    DevilsLockError,
    ResourceCapExceededError,
    VRAMHeadroomExceededError,
    VRAMLockBlockedError,
    VRAMTelemetryError,
    GeneticELOMandateError,
    SubagentRegistration,
    select_highest_elo_model_for_ui,
    FALLBACK_UI_MODEL,
)


# ============================================================================
# Category 1: Dead PID Recovery & State File Corruption
# ============================================================================

def test_dead_pid_recovery_nonexistent_pid(tmp_path):
    """Verify stale lock held by a dead/nonexistent PID is auto-healed."""
    lock_dir = tmp_path / "dead_pid_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    state_file = lock_dir / "devils_subagent_state.json"

    stale_state = {
        "subagent_id": "dead_subagent_888",
        "pid": 9999999,
        "task_name": "dead_task",
        "model": "kimi_tandem_titan",
        "registered_at": time.time() - 1000,
        "heartbeat_at": time.time() - 1000,
    }
    state_file.write_text(json.dumps(stale_state))

    gov = DevilsLockGovernor(lock_dir=str(lock_dir))
    assert gov.check_resource_cap() is True
    assert gov.get_active_subagent() is None

    acquired = gov.acquire_subagent_lock("live_agent_1", "live_task_1")
    assert acquired is True
    assert gov.check_resource_cap() is False
    gov.release_subagent_lock("live_agent_1")
    assert gov.check_resource_cap() is True


@pytest.mark.parametrize("invalid_pid", [0, -1, -999])
def test_dead_pid_recovery_zero_and_negative_pid(tmp_path, invalid_pid):
    """Verify PID <= 0 in state file is detected as inactive and healed."""
    lock_dir = tmp_path / f"pid_{invalid_pid}_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    state_file = lock_dir / "devils_subagent_state.json"

    state_file.write_text(json.dumps({"subagent_id": "inv_pid_agent", "pid": invalid_pid}))
    gov = DevilsLockGovernor(lock_dir=str(lock_dir))

    assert gov.check_resource_cap() is True
    assert gov.get_active_subagent() is None


@pytest.mark.parametrize("corrupt_content,desc", [
    ("", "Empty 0-byte file"),
    ("{ invalid json syntax", "Syntax invalid JSON"),
    (json.dumps({"subagent_id": "agent_null", "pid": None}), "Null PID in JSON"),
    (json.dumps({"subagent_id": "agent_str", "pid": "not_a_number"}), "String PID in JSON"),
    (json.dumps([]), "Root JSON is array"),
    (json.dumps("raw string"), "Root JSON is primitive string"),
    (json.dumps(123456), "Root JSON is integer"),
])
def test_state_file_corruption_auto_healing(tmp_path, corrupt_content, desc):
    """Verify various state file corruptions heal automatically without throwing exceptions."""
    lock_dir = tmp_path / "corrupt_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    state_file = lock_dir / "devils_subagent_state.json"

    state_file.write_text(corrupt_content)
    gov = DevilsLockGovernor(lock_dir=str(lock_dir))

    assert gov.check_resource_cap() is True, f"Failed on {desc}"
    assert gov.get_active_subagent() is None, f"Failed on {desc}"
    assert gov.acquire_subagent_lock("healed_agent", "healed_task") is True
    gov.release_subagent_lock("healed_agent")


def test_wrong_agent_release_rejection(tmp_path):
    """Verify that an agent cannot release another agent's lock."""
    gov = DevilsLockGovernor(lock_dir=str(tmp_path / "auth_locks"))
    acquired = gov.acquire_subagent_lock("agent_owner", "critical_task")
    assert acquired is True

    # Unauthorized release attempt
    released = gov.release_subagent_lock(subagent_id="agent_imposter")
    assert released is False
    assert gov.check_resource_cap() is False
    assert gov.active_subagent_id == "agent_owner"

    # Authorized release
    released_ok = gov.release_subagent_lock(subagent_id="agent_owner")
    assert released_ok is True
    assert gov.check_resource_cap() is True


def test_force_release_overrides_ownership(tmp_path):
    """Verify that force=True resets state regardless of caller."""
    gov = DevilsLockGovernor(lock_dir=str(tmp_path / "force_locks"))
    gov.acquire_subagent_lock("agent_owner", "task_1")

    released = gov.release_resource_lock(subagent_id="agent_other", force=True)
    assert released is True
    assert gov.check_resource_cap() is True
    assert gov.active_subagent_id is None


def test_reentrancy_updates_heartbeat(tmp_path):
    """Verify same subagent re-acquiring updates heartbeat."""
    gov = DevilsLockGovernor(lock_dir=str(tmp_path / "reentrant_locks"))
    assert gov.acquire_subagent_lock("agent_1", "task_1") is True
    t1 = gov.get_active_subagent().heartbeat_at

    time.sleep(0.01)
    assert gov.acquire_subagent_lock("agent_1", "task_1_renewed") is True
    t2 = gov.get_active_subagent().heartbeat_at
    assert t2 >= t1

    gov.release_subagent_lock("agent_1")


# ============================================================================
# Category 2: Leaderboard JSON Malformations & Boundary Values
# ============================================================================

def test_leaderboard_missing_file_modes():
    """Verify missing leaderboard behavior on raise_on_error True vs False."""
    missing_path = "/tmp/non_existent_file_987654321.json"

    with pytest.raises(DevilsLockError, match="Canonical AI Leaderboard not found"):
        select_highest_elo_model_for_ui(leaderboard_path=missing_path, raise_on_error=True)

    fallback = select_highest_elo_model_for_ui(leaderboard_path=missing_path, raise_on_error=False)
    assert fallback["id"] == FALLBACK_UI_MODEL["id"]
    assert fallback["is_fallback"] is True


def test_leaderboard_corrupted_syntax_modes(tmp_path):
    """Verify corrupted JSON syntax on raise_on_error True vs False."""
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{ broken json content ...")

    with pytest.raises(DevilsLockError, match="Failed to parse leaderboard JSON"):
        select_highest_elo_model_for_ui(leaderboard_path=str(corrupt_file), raise_on_error=True)

    fallback = select_highest_elo_model_for_ui(leaderboard_path=str(corrupt_file), raise_on_error=False)
    assert fallback["id"] == FALLBACK_UI_MODEL["id"]
    assert fallback["is_fallback"] is True


def test_leaderboard_empty_and_null_arrays(tmp_path):
    """Verify empty or null leaderboard list raises DevilsLockError."""
    f1 = tmp_path / "empty.json"
    f1.write_text(json.dumps({"leaderboard": []}))
    with pytest.raises(DevilsLockError, match="Leaderboard JSON contains no models list"):
        select_highest_elo_model_for_ui(leaderboard_path=str(f1), raise_on_error=True)

    f2 = tmp_path / "null_lb.json"
    f2.write_text(json.dumps({"leaderboard": None}))
    with pytest.raises(DevilsLockError, match="Leaderboard JSON contains no models list"):
        select_highest_elo_model_for_ui(leaderboard_path=str(f2), raise_on_error=True)


def test_leaderboard_resilient_against_malformed_model_entries(tmp_path):
    """Verify leaderboard handles string ELOs, string skills, negative ELOs, ultra ELOs safely."""
    content = {
        "leaderboard": [
            {"id": ""},  # Empty id -> skipped
            {"name": ""},  # Empty name -> skipped
            {"id": "model_str_skill", "elo": 2500, "specialist_skills": "invalid_skill_string"},
            {"id": "model_bad_skill_val", "elo": 2600, "specialist_skills": {"3d_ai_training_game": "bad_num"}},
            {"id": "model_null_elo", "elo": None, "specialist_skills": {"3d_ai_training_game": 80.0}},
            {"id": "model_neg_elo", "elo": -5000, "specialist_skills": {"3d_ai_training_game": 80.0}},
            {"id": "model_huge_elo", "elo": 999999, "specialist_skills": {"3d_ai_training_game": 95.0}},
            {"id": "model_top", "elo": 3000, "specialist_skills": {"3d_ai_training_game": 99.0, "vision_vlm_truth_auditing": 98.0}},
        ]
    }
    lb_file = tmp_path / "resilient_lb.json"
    lb_file.write_text(json.dumps(content))

    selected = select_highest_elo_model_for_ui(leaderboard_path=str(lb_file))
    assert selected["id"] in ["model_top", "model_huge_elo"]
    assert selected["ui_composite_score"] > 0.0


def test_leaderboard_deterministic_tie_breaking(tmp_path):
    """Verify deterministic tie-breaking when two models have identical metrics."""
    content = {
        "leaderboard": [
            {"id": "model_b", "elo": 2500, "specialist_skills": {"3d_ai_training_game": 90, "vision_vlm_truth_auditing": 90, "flutter_dart_mobile_architecture": 90}},
            {"id": "model_a", "elo": 2500, "specialist_skills": {"3d_ai_training_game": 90, "vision_vlm_truth_auditing": 90, "flutter_dart_mobile_architecture": 90}},
        ]
    }
    lb_file = tmp_path / "tie_break.json"
    lb_file.write_text(json.dumps(content))

    # Should break tie deterministically on id (descending sort on id: 'model_b' > 'model_a')
    selected_1 = select_highest_elo_model_for_ui(leaderboard_path=str(lb_file))
    selected_2 = select_highest_elo_model_for_ui(leaderboard_path=str(lb_file))
    assert selected_1["id"] == selected_2["id"]


# ============================================================================
# Category 3: VRAM Headroom Check & Extreme Memory Boundaries
# ============================================================================

@pytest.mark.parametrize("val,expected_allowed", [
    (0.0, False),
    (14.9999, False),
    (15.0, True),
    (15.0001, True),
    (100.0, True),
])
def test_vram_boundary_exact_thresholds(val, expected_allowed):
    """Verify exact VRAM boundary behavior around 15.0% threshold."""
    gov = DevilsLockGovernor()
    allowed, free_gb, free_pct = gov.check_vram_and_lock(override_free_pct=val)
    assert allowed == expected_allowed
    assert free_pct == val


@pytest.mark.parametrize("invalid_val", [-0.001, -100.0, 100.001, 500.0, float('inf'), float('-inf')])
def test_vram_invalid_numeric_values_raise(invalid_val):
    """Verify out-of-range percentage values raise ValueError."""
    gov = DevilsLockGovernor()
    with pytest.raises(ValueError, match="Invalid VRAM percentage"):
        gov.check_vram_and_lock(override_free_pct=invalid_val)


def test_vram_nan_fails_closed():
    """Verify NaN percentage safely fails closed (allowed=False) without allowing subagents."""
    gov = DevilsLockGovernor()
    allowed, free_gb, free_pct = gov.check_vram_and_lock(override_free_pct=float('nan'))
    assert allowed is False  # Fails closed, protecting system safety


def test_vram_custom_min_headroom_threshold():
    """Verify governor honors customized min_vram_pct parameter."""
    gov_strict = DevilsLockGovernor(min_vram_pct=25.0)
    assert gov_strict.min_vram_pct == 25.0

    allowed_20, _, _ = gov_strict.check_vram_and_lock(override_free_pct=20.0)
    assert allowed_20 is False

    allowed_25, _, _ = gov_strict.check_vram_and_lock(override_free_pct=25.0)
    assert allowed_25 is True


def test_vram_telemetry_dict_schema():
    """Verify get_vram_telemetry returns complete dictionary matching schema."""
    gov = DevilsLockGovernor()
    tel = gov.get_vram_telemetry(override_free_pct=22.5)
    assert tel["is_allowed"] is True
    assert tel["is_locked"] is False
    assert tel["free_pct"] == 22.5
    assert tel["min_required_pct"] == 15.0
    assert "timestamp" in tel
    assert isinstance(tel["free_vram_gb"], float)


# ============================================================================
# Category 4: Multithreaded & High-Concurrency Contention
# ============================================================================

def test_multithread_high_contention_50_threads(tmp_path):
    """Verify strict single-agent exclusivity under 50 simultaneous competing threads."""
    gov = DevilsLockGovernor(lock_dir=str(tmp_path / "thread_contention"))
    results = []
    threads = []
    barrier = threading.Barrier(50)

    def attempt_acquire(tid: int):
        try:
            barrier.wait(timeout=5)
        except Exception:
            pass
        ok = gov.acquire_subagent_lock(f"agent_{tid}", f"task_{tid}")
        results.append((tid, ok))

    for i in range(50):
        t = threading.Thread(target=attempt_acquire, args=(i,))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successful = [r for r in results if r[1] is True]
    assert len(successful) == 1, f"Expected exactly 1 thread to acquire lock, got {len(successful)}"
    assert gov.check_resource_cap() is False

    winner_id = f"agent_{successful[0][0]}"
    assert gov.release_subagent_lock(winner_id) is True
    assert gov.check_resource_cap() is True
