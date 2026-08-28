"""
Unit Tests: 4-Way Debate Devil's Lock Governance (Milestone 1)
backend/devils_lock_governor.py

Covers:
  - Resource Cap Gate (Max 1 active subagent, thread-safety, kernel flock, dead PID recovery, context manager)
  - VRAM Headroom Check (Strict < 15% lock, boundary values, Rule #0 authentic hardware inspection)
  - Genetic ELO Model Selection (canonical_ai_leaderboard.json scoring, UI domain specialist skills, tie-breaking)
  - Preflight Validator (Sequence execution, error raising, success payload verification)

Derived strictly from: ORIGINAL_REQUEST.md §R2, PROJECT.md §Interface Contracts
Test Architecture: 4-Tier Multi-Tier Testing Infrastructure (Category-Partition, Boundary Values, Pairwise Combinations, Real-World Scenarios)
"""

import os
import sys
import json
import time
import errno
import pytest
import threading
from typing import Dict, Any, Optional, Tuple, List

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.devils_lock_governor import (
    DevilsLockGovernor,
    DevilsLockError,
    ResourceCapExceededError,
    VRAMHeadroomExceededError,
    VRAMLockBlockedError,
    VRAMTelemetryError,
    GeneticELOMandateError,
    GeneticLeaderboardError,
    LeaderboardSelectionError,
    SubagentRegistration,
    select_highest_elo_model_for_ui,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def governor(tmp_path) -> DevilsLockGovernor:
    """Creates a fresh DevilsLockGovernor instance with isolated lock directory."""
    lock_dir = tmp_path / "lauburu_locks"
    gov = DevilsLockGovernor(lock_dir=str(lock_dir))
    yield gov
    gov.release_subagent_lock()


@pytest.fixture
def temp_leaderboard(tmp_path) -> str:
    """Creates an authentic temporary leaderboard JSON for isolated boundary tests."""
    leaderboard_file = tmp_path / "test_canonical_ai_leaderboard.json"
    content = {
        "schema_version": "2.5.0",
        "last_updated_utc": "2026-08-29T00:00:00Z",
        "canonical_summary": {
            "total_models": 3,
            "top_sovereign_model_id": "kimi_tandem_titan",
        },
        "leaderboard": [
            {
                "id": "kimi_tandem_titan",
                "name": "Kimi Tandem Titan (VL-Encoder + 72B Backbone)",
                "short_name": "Kimi Tandem 88B",
                "tier": "LOCAL_SOVEREIGN_GIANT",
                "elo": 3089.0,
                "base_elo": 3089.0,
                "canonical_score": 99.8,
                "overall_benchmark_score": 99.6,
                "specialist_skills": {
                    "3d_ai_training_game": 99.8,
                    "flutter_dart_mobile_architecture": 95.6,
                    "vision_vlm_truth_auditing": 99.7,
                },
            },
            {
                "id": "antigravity_preview",
                "name": "Antigravity Preview AGY",
                "short_name": "AGY Preview",
                "tier": "CLOUD_FRONTIER_REASONER",
                "elo": 2390.0,
                "base_elo": 2390.0,
                "canonical_score": 98.4,
                "overall_benchmark_score": 98.0,
                "specialist_skills": {
                    "3d_ai_training_game": 99.6,
                    "flutter_dart_mobile_architecture": 99.0,
                    "vision_vlm_truth_auditing": 98.5,
                },
            },
            {
                "id": "hermes_3_8b",
                "name": "Hermes 3 8B Edge",
                "short_name": "Hermes 8B",
                "tier": "EDGE_COMPACT",
                "elo": 2240.0,
                "base_elo": 2240.0,
                "canonical_score": 92.0,
                "overall_benchmark_score": 91.5,
                "specialist_skills": {
                    "3d_ai_training_game": 97.4,
                    "flutter_dart_mobile_architecture": 92.0,
                    "vision_vlm_truth_auditing": 90.0,
                },
            },
        ],
    }
    leaderboard_file.write_text(json.dumps(content, indent=2))
    return str(leaderboard_file)


# ============================================================================
# TIER 1: CATEGORY-PARTITION (Nominal & Happy Paths)
# ============================================================================

def test_governor_initialization(governor):
    """Tier 1: Verify DevilsLockGovernor initializes with correct defaults and properties."""
    assert governor.max_active_subagents == 1
    assert governor.VRAM_MIN_HEADROOM_PCT == 15.0
    assert governor.min_vram_pct == 15.0
    assert governor.check_resource_cap() is True
    assert governor.active_subagent_id is None
    assert governor.active_subagent_task is None
    assert governor.get_active_subagent() is None


def test_resource_cap_allows_single_subagent(governor):
    """Tier 1: Verify single subagent lock acquisition succeeds and updates state."""
    assert governor.check_resource_cap() is True
    success = governor.acquire_subagent_lock("subagent_001", "tui_redesign_grid")
    assert success is True
    assert governor.check_resource_cap() is False
    assert governor.active_subagent_id == "subagent_001"
    assert governor.active_subagent_task == "tui_redesign_grid"

    active = governor.get_active_subagent()
    assert active is not None
    assert active.subagent_id == "subagent_001"
    assert active.task_name == "tui_redesign_grid"


def test_resource_cap_release_restores_capacity(governor):
    """Tier 1: Verify releasing subagent lock restores capacity cleanly."""
    governor.acquire_subagent_lock("subagent_001", "tui_redesign_grid")
    assert governor.check_resource_cap() is False
    released = governor.release_subagent_lock("subagent_001")
    assert released is True
    assert governor.check_resource_cap() is True
    assert governor.active_subagent_id is None
    assert governor.get_active_subagent() is None


def test_vram_lock_allows_execution_when_headroom_adequate(governor):
    """Tier 1: Verify VRAM check allows execution when headroom >= 15%."""
    allowed, free_gb, free_pct = governor.check_vram_and_lock(override_free_pct=25.0)
    assert allowed is True
    assert free_pct == 25.0
    assert free_gb > 0.0


def test_genetic_elo_selects_top_model(temp_leaderboard):
    """Tier 1: Verify Genetic ELO selector picks the highest domain UI model."""
    gov = DevilsLockGovernor(leaderboard_path=temp_leaderboard)
    top = gov.select_highest_elo_model_for_ui()
    assert top["id"] == "kimi_tandem_titan"
    assert top["elo"] == 3089.0
    assert top["ui_composite_score"] > 95.0
    assert "specialist_skills" in top
    assert top["tier"] == "LOCAL_SOVEREIGN_GIANT"


def test_preflight_locks_pass_all_gates(temp_leaderboard, tmp_path):
    """Tier 1: Verify complete preflight lock passes when all conditions met."""
    gov = DevilsLockGovernor(leaderboard_path=temp_leaderboard, lock_dir=str(tmp_path / "locks"))
    result = gov.validate_preflight_locks(override_free_pct=30.0)
    assert result["status"] == "PASS"
    assert result["resource_cap_ok"] is True
    assert result["resource_cap_passed"] is True
    assert result["vram_passed"] is True
    assert result["vram_free_pct"] == 30.0
    assert result["selected_model"]["id"] == "kimi_tandem_titan"


def test_subagent_context_manager_lifecycle(governor):
    """Tier 1: Verify context manager automatically acquires and releases lock."""
    with governor.subagent_lock_context("ctx_agent_1", task_name="ctx_task") as reg:
        assert reg.subagent_id == "ctx_agent_1"
        assert governor.check_resource_cap() is False
        assert governor.active_subagent_id == "ctx_agent_1"

    # After exiting context block, lock must be released
    assert governor.check_resource_cap() is True
    assert governor.active_subagent_id is None


def test_subagent_context_manager_exception_safety(governor):
    """Tier 1: Verify context manager releases lock even when exception is raised."""
    try:
        with governor.subagent_lock_context("ctx_agent_err", task_name="crash_task"):
            assert governor.check_resource_cap() is False
            raise RuntimeError("Simulated subagent crash")
    except RuntimeError:
        pass

    assert governor.check_resource_cap() is True
    assert governor.active_subagent_id is None


def test_subagent_heartbeat(governor):
    """Tier 1: Verify heartbeat updates timestamp for active agent."""
    governor.acquire_subagent_lock("hb_agent", "hb_task")
    old_heartbeat = governor.get_active_subagent().heartbeat_at
    time.sleep(0.01)
    updated = governor.heartbeat("hb_agent")
    assert updated is True
    new_heartbeat = governor.get_active_subagent().heartbeat_at
    assert new_heartbeat >= old_heartbeat
    governor.release_subagent_lock("hb_agent")


# ============================================================================
# TIER 2: BOUNDARY VALUES & ERROR STATES
# ============================================================================

@pytest.mark.parametrize("vram_pct,expected_allowed", [
    (0.0, False),
    (5.0, False),
    (14.0, False),
    (14.9, False),
    (14.99, False),
    (15.0, True),       # Exact 15.0% boundary condition per R2 §2
    (15.01, True),
    (15.1, True),
    (20.0, True),
    (50.0, True),
    (99.9, True),
    (100.0, True),
])
def test_vram_lock_exact_boundary_thresholds(governor, vram_pct, expected_allowed):
    """Tier 2: Boundary Value Analysis on VRAM < 15.0% lock."""
    allowed, free_gb, free_pct = governor.check_vram_and_lock(override_free_pct=vram_pct)
    assert allowed == expected_allowed, f"VRAM {vram_pct}% failed expected allowed={expected_allowed}"
    assert free_pct == vram_pct


def test_vram_lock_invalid_negative_or_overflow_pct(governor):
    """Tier 2: Verify invalid percentage values raise ValueError."""
    with pytest.raises(ValueError, match="Invalid VRAM percentage"):
        governor.check_vram_and_lock(override_free_pct=-5.0)

    with pytest.raises(ValueError, match="Invalid VRAM percentage"):
        governor.check_vram_and_lock(override_free_pct=105.0)


def test_resource_cap_blocks_second_subagent(governor):
    """Tier 2: Verify second subagent is blocked when 1 is already running."""
    success_1 = governor.acquire_subagent_lock("subagent_A", "task_A")
    assert success_1 is True

    # Second acquisition must fail
    success_2 = governor.acquire_subagent_lock("subagent_B", "task_B")
    assert success_2 is False
    assert governor.active_subagent_id == "subagent_A"

    # acquire_resource_lock raises ResourceCapExceededError
    with pytest.raises(ResourceCapExceededError, match="Resource Cap Exceeded"):
        governor.acquire_resource_lock("subagent_B", task_name="task_B")

    governor.release_subagent_lock("subagent_A")


def test_preflight_locks_raise_on_resource_cap_violation(governor):
    """Tier 2: Verify validate_preflight_locks raises DevilsLockError when cap violated."""
    governor.acquire_subagent_lock("active_agent_1", "task_running")
    with pytest.raises(DevilsLockError, match="Resource Cap Violated"):
        governor.validate_preflight_locks(override_free_pct=50.0)
    governor.release_subagent_lock("active_agent_1")


def test_preflight_locks_raise_on_vram_exhaustion(governor):
    """Tier 2: Verify validate_preflight_locks raises DevilsLockError when VRAM < 15%."""
    with pytest.raises(DevilsLockError, match="VRAM Headroom Lock Engaged"):
        governor.validate_preflight_locks(override_free_pct=12.5)


def test_genetic_elo_missing_file_error():
    """Tier 2: Verify missing leaderboard file raises descriptive DevilsLockError."""
    gov = DevilsLockGovernor(leaderboard_path="/tmp/nonexistent_leaderboard_12345.json")
    with pytest.raises(DevilsLockError, match="Canonical AI Leaderboard not found"):
        gov.select_highest_elo_model_for_ui()


def test_genetic_elo_malformed_json_error(tmp_path):
    """Tier 2: Verify malformed JSON file raises DevilsLockError."""
    corrupted_file = tmp_path / "corrupted_leaderboard.json"
    corrupted_file.write_text("{ this is not valid json")
    gov = DevilsLockGovernor(leaderboard_path=str(corrupted_file))
    with pytest.raises(DevilsLockError, match="Failed to parse leaderboard JSON"):
        gov.select_highest_elo_model_for_ui()


def test_release_lock_by_wrong_agent_fails(governor):
    """Tier 2: Verify a different subagent cannot release another's lock."""
    governor.acquire_subagent_lock("subagent_A", "task_A")
    released = governor.release_subagent_lock(subagent_id="subagent_B")
    assert released is False
    assert governor.active_subagent_id == "subagent_A"
    # Clean up lock at end of test
    governor.release_subagent_lock(subagent_id="subagent_A")


def test_stale_pid_self_healing_recovery(tmp_path):
    """Tier 2: Verify dead PID in persisted state is auto-healed without error."""
    lock_dir = tmp_path / "stale_locks"
    os.makedirs(lock_dir, exist_ok=True)
    state_file = lock_dir / "devils_subagent_state.json"

    # Write stale state with non-existent PID (9999999)
    stale_state = {
        "subagent_id": "dead_agent_999",
        "pid": 9999999,
        "task_name": "abandoned_task",
        "model": "kimi_tandem_titan",
        "registered_at": time.time() - 3600,
        "heartbeat_at": time.time() - 3600,
    }
    state_file.write_text(json.dumps(stale_state))

    gov = DevilsLockGovernor(lock_dir=str(lock_dir))
    # Must detect dead PID and report slot as available
    assert gov.check_resource_cap() is True
    assert gov.get_active_subagent() is None

    # New acquisition must succeed
    acquired = gov.acquire_subagent_lock("new_live_agent", "new_task")
    assert acquired is True
    gov.release_subagent_lock("new_live_agent")


# ============================================================================
# TIER 3: PAIRWISE COMBINATIONS & RACE CONCURRENCY
# ============================================================================

@pytest.mark.parametrize("subagent_active,vram_pct,expect_pass,expected_error_substr", [
    (False, 25.0, True, None),                                  # Nominal pass
    (True, 25.0, False, "Resource Cap Violated"),               # Cap violated, VRAM ok
    (False, 10.0, False, "VRAM Headroom Lock Engaged"),         # Cap ok, VRAM violated
    (True, 10.0, False, "Resource Cap Violated"),               # Both violated (Cap fails first)
    (False, 14.99, False, "VRAM Headroom Lock Engaged"),        # Edge boundary below 15%
    (False, 15.00, True, None),                                 # Edge boundary at 15%
])
def test_preflight_pairwise_matrix(temp_leaderboard, tmp_path, subagent_active, vram_pct, expect_pass, expected_error_substr):
    """Tier 3: Pairwise combination of Resource Cap × VRAM Headroom states."""
    gov = DevilsLockGovernor(leaderboard_path=temp_leaderboard, lock_dir=str(tmp_path / f"locks_{subagent_active}_{vram_pct}"))
    if subagent_active:
        gov.acquire_subagent_lock("existing_agent", "existing_task")

    if expect_pass:
        res = gov.validate_preflight_locks(override_free_pct=vram_pct)
        assert res["status"] == "PASS"
    else:
        with pytest.raises(DevilsLockError, match=expected_error_substr):
            gov.validate_preflight_locks(override_free_pct=vram_pct)

    if subagent_active:
        gov.release_subagent_lock("existing_agent")


def test_concurrent_lock_acquisition_race(tmp_path):
    """Tier 3: Verify strict single-subagent concurrency under race conditions."""
    gov = DevilsLockGovernor(lock_dir=str(tmp_path / "race_locks"))
    results = []
    threads = []

    def try_acquire(agent_id: str):
        ok = gov.acquire_subagent_lock(agent_id, f"task_{agent_id}")
        results.append((agent_id, ok))

    for i in range(10):
        t = threading.Thread(target=try_acquire, args=(f"agent_{i}",))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly 1 thread must have succeeded
    successful_acquisitions = [r for r in results if r[1] is True]
    assert len(successful_acquisitions) == 1
    assert gov.check_resource_cap() is False

    winner_id = successful_acquisitions[0][0]
    gov.release_subagent_lock(winner_id)
    assert gov.check_resource_cap() is True


def test_genetic_elo_custom_weights(temp_leaderboard):
    """Tier 3: Verify custom skill weights correctly influence model ranking."""
    # Weight 3D skill 100%
    model_3d = select_highest_elo_model_for_ui(
        leaderboard_path=temp_leaderboard,
        weights={"3d_ai_training_game": 1.0, "vision_vlm_truth_auditing": 0.0, "flutter_dart_mobile_architecture": 0.0, "elo": 0.0}
    )
    assert model_3d["id"] == "kimi_tandem_titan"
    assert model_3d["capabilities"]["3d_ai_training_game"] >= 99.0

    # Weight Flutter skill 100%
    model_flutter = select_highest_elo_model_for_ui(
        leaderboard_path=temp_leaderboard,
        weights={"3d_ai_training_game": 0.0, "vision_vlm_truth_auditing": 0.0, "flutter_dart_mobile_architecture": 1.0, "elo": 0.0}
    )
    assert model_flutter["id"] == "antigravity_preview"
    assert model_flutter["capabilities"]["flutter_dart_mobile_architecture"] == 99.0


# ============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ============================================================================

def test_scenario_full_subagent_lifecycle(temp_leaderboard, tmp_path):
    """Tier 4: Scenario 1 — Complete subagent lifecycle with Devil's Lock gates."""
    gov = DevilsLockGovernor(leaderboard_path=temp_leaderboard, lock_dir=str(tmp_path / "lifecycle_locks"))

    # 1. Preflight validation
    preflight = gov.validate_preflight_locks(override_free_pct=40.0)
    assert preflight["status"] == "PASS"
    selected_model = preflight["selected_model"]["id"]
    assert selected_model == "kimi_tandem_titan"

    # 2. Acquire subagent slot
    acquired = gov.acquire_subagent_lock(selected_model, "refactor_tui_grid")
    assert acquired is True

    # 3. Intermediate spawn attempt is rejected
    with pytest.raises(DevilsLockError, match="Resource Cap Violated"):
        gov.validate_preflight_locks(override_free_pct=40.0)

    # 4. Release lock after task completion
    released = gov.release_subagent_lock(selected_model)
    assert released is True
    assert gov.check_resource_cap() is True

    # 5. Next cycle passes preflight
    next_preflight = gov.validate_preflight_locks(override_free_pct=35.0)
    assert next_preflight["status"] == "PASS"


def test_scenario_live_monorepo_leaderboard_resolution(governor):
    """Tier 4: Scenario 2 — Verify live monorepo leaderboard parses authentic models."""
    if os.path.isfile(governor.leaderboard_path):
        top_model = governor.select_highest_elo_model_for_ui()
        assert top_model["id"] in ["kimi_tandem_titan", "gemini_3_1_pro", "antigravity_preview"]
        assert top_model["elo"] >= 2000.0
        assert "ui_composite_score" in top_model


def test_scenario_live_vram_metrics_read_safely(governor):
    """Tier 4: Scenario 3 — Verify real system VRAM queries without fake data."""
    total, free, pct = governor.get_system_vram_metrics()
    assert total > 0.0
    assert free >= 0.0
    assert 0.0 <= pct <= 100.0
    allowed, free_gb, free_pct = governor.check_vram_and_lock()
    assert isinstance(allowed, bool)
    assert allowed == (free_pct >= 15.0)

    # Telemetry format check
    telemetry = governor.get_vram_telemetry()
    assert "is_allowed" in telemetry
    assert "free_vram_gb" in telemetry
    assert "free_pct" in telemetry
    assert "min_required_pct" in telemetry
    assert telemetry["min_required_pct"] == 15.0
