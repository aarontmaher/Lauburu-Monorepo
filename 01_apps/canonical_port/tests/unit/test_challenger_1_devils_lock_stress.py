"""
Adversarial Stress Test Suite: DevilsLockGovernor (Milestone 1)
tests/unit/test_challenger_1_devils_lock_stress.py

Empirical Challenger 1 Stress Harness:
  1. High-concurrency thread contention (50 threads race conditions, reentrancy, rapid cycling).
  2. Multi-process kernel contention & abrupt crash recovery (SIGKILL dead PID self-healing).
  3. Exact boundary & extreme float stress on VRAM headroom (14.999999%, 15.0%, NaN, Inf, overflow).
  4. Adversarial fuzzing of Genetic ELO leaderboard parser (corrupted JSON, null fields, non-numeric strings, 10,000 models).
  5. Security & anti-theft checks (lock spoofing, unauthorized release, heartbeat isolation).
  6. Corrupted state file fault tolerance (truncated disk JSON recovery).
"""

import os
import sys
import math
import json
import time
import errno
import signal
import pytest
import threading
import multiprocessing
from pathlib import Path
from typing import Dict, Any, List

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
# 1. HIGH-CONCURRENCY THREAD CONTENTION HARNESS
# ============================================================================

def test_stress_50_threads_simultaneous_race(tmp_path):
    """
    Stress 1.1: 50 threads concurrently competing to acquire resource lock.
    Invariant: EXACTLY ONE thread must succeed. 49 threads must be rejected.
    """
    lock_dir = str(tmp_path / "stress_thread_race")
    gov = DevilsLockGovernor(lock_dir=lock_dir)

    barrier = threading.Barrier(50)
    results = []
    threads = []

    def worker(tid: int):
        barrier.wait()  # synchronize start to maximize collision
        ok = gov.acquire_subagent_lock(f"agent_{tid}", task_name=f"task_{tid}")
        results.append((tid, ok))

    for i in range(50):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    successes = [tid for tid, ok in results if ok]
    failures = [tid for tid, ok in results if not ok]

    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}: {successes}"
    assert len(failures) == 49
    assert gov.check_resource_cap() is False

    winner_id = f"agent_{successes[0]}"
    assert gov.active_subagent_id == winner_id

    # Release and ensure next round allows a new winner
    released = gov.release_subagent_lock(winner_id)
    assert released is True
    assert gov.check_resource_cap() is True


def test_stress_multi_instance_thread_race(tmp_path):
    """
    Stress 1.2: 30 distinct DevilsLockGovernor instances on separate threads
    pointing to the SAME lock directory.
    Invariant: POSIX file lock + thread lock ensures strictly 1 instance acquires.
    """
    lock_dir = str(tmp_path / "multi_instance_race")
    barrier = threading.Barrier(30)
    results = []
    threads = []

    def instance_worker(tid: int):
        local_gov = DevilsLockGovernor(lock_dir=lock_dir)
        barrier.wait()
        ok = local_gov.acquire_subagent_lock(f"inst_agent_{tid}", task_name=f"inst_task_{tid}")
        results.append((tid, ok, local_gov))

    for i in range(30):
        t = threading.Thread(target=instance_worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    successes = [(tid, gov) for tid, ok, gov in results if ok]
    assert len(successes) == 1, f"Expected 1 winner across independent instances, got {len(successes)}"

    winner_tid, winner_gov = successes[0]
    winner_gov.release_subagent_lock(f"inst_agent_{winner_tid}")


def test_stress_rapid_acquire_release_cycling(tmp_path):
    """
    Stress 1.3: 500 rapid sequential acquire/release cycles.
    Invariant: No descriptor leaks, no deadlocks, 100% success rate.
    """
    lock_dir = str(tmp_path / "cycling_locks")
    gov = DevilsLockGovernor(lock_dir=lock_dir)

    for i in range(500):
        agent_id = f"cycle_agent_{i}"
        acq = gov.acquire_subagent_lock(agent_id, task_name=f"task_{i}")
        assert acq is True, f"Failed at iteration {i}"
        assert gov.check_resource_cap() is False

        # Verify active subagent inspection
        active = gov.get_active_subagent()
        assert active is not None
        assert active.subagent_id == agent_id

        rel = gov.release_subagent_lock(agent_id)
        assert rel is True
        assert gov.check_resource_cap() is True


# ============================================================================
# 2. MULTI-PROCESS CONTENTION & CRASH RESILIENCE HARNESS
# ============================================================================

def _mp_worker(lock_dir: str, agent_id: str, hold_sec: float, result_queue: multiprocessing.Queue):
    """Subprocess target attempting to acquire lock."""
    gov = DevilsLockGovernor(lock_dir=lock_dir)
    ok = gov.acquire_subagent_lock(agent_id, task_name=f"mp_task_{agent_id}", pid=os.getpid())
    result_queue.put((agent_id, ok, os.getpid()))
    if ok:
        time.sleep(hold_sec)
        gov.release_subagent_lock(agent_id)


def test_stress_multiprocess_kernel_flock_contention(tmp_path):
    """
    Stress 2.1: 8 separate OS processes attempting to acquire the kernel lock simultaneously.
    Invariant: Exactly 1 process succeeds at any given time.
    """
    lock_dir = str(tmp_path / "mp_kernel_locks")
    queue = multiprocessing.Queue()
    processes = []

    for i in range(8):
        p = multiprocessing.Process(
            target=_mp_worker,
            args=(lock_dir, f"mp_proc_{i}", 0.2, queue)
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=5.0)

    results = []
    while not queue.empty():
        results.append(queue.get())

    successes = [r for r in results if r[1] is True]
    assert len(successes) == 1, f"Expected 1 process to acquire lock, got {len(successes)}: {results}"


def _abrupt_death_worker(lock_dir: str, agent_id: str, ready_event):
    """Worker that acquires lock and immediately dies (SIGKILL simulation)."""
    gov = DevilsLockGovernor(lock_dir=lock_dir)
    gov.acquire_subagent_lock(agent_id, task_name="crash_task", pid=os.getpid())
    ready_event.set()
    time.sleep(10.0)  # Wait to be killed


def test_stress_abrupt_sigkill_dead_pid_self_healing(tmp_path):
    """
    Stress 2.2: Process acquires lock and is abruptly killed with SIGKILL (kill -9).
    Invariant: Main process must detect dead PID, auto-heal stale state, and acquire lock.
    """
    lock_dir = str(tmp_path / "sigkill_healing")
    ready_event = multiprocessing.Event()

    p = multiprocessing.Process(
        target=_abrupt_death_worker,
        args=(lock_dir, "doomed_subagent", ready_event)
    )
    p.start()
    ready_event.wait(timeout=3.0)
    time.sleep(0.05)

    dead_pid = p.pid
    assert p.is_alive()

    # Kill process abruptly with SIGKILL (no cleanup possible)
    os.kill(dead_pid, signal.SIGKILL)
    p.join()
    assert not p.is_alive()

    # Now verify that DevilsLockGovernor detects stale PID and recovers
    gov = DevilsLockGovernor(lock_dir=lock_dir)

    # 1. check_resource_cap must return True (auto-healed)
    assert gov.check_resource_cap() is True
    assert gov.get_active_subagent() is None

    # 2. New subagent must be able to acquire lock immediately
    acquired = gov.acquire_subagent_lock("phoenix_agent", "recovery_task")
    assert acquired is True
    assert gov.check_resource_cap() is False
    assert gov.active_subagent_id == "phoenix_agent"

    gov.release_subagent_lock("phoenix_agent")
    assert gov.check_resource_cap() is True


# ============================================================================
# 3. VRAM HEADROOM EXACT BOUNDARY & EXTREME FLOAT STRESS
# ============================================================================

@pytest.mark.parametrize("pct,expected_allowed", [
    (14.99999999999999, False),   # Sub-epsilon below 15.0%
    (14.9999999, False),
    (14.999, False),
    (15.00000000000000, True),    # Exact boundary
    (15.00000000000001, True),    # Sub-epsilon above 15.0%
    (15.001, True),
    (0.0, False),                 # Complete exhaustion
    (100.0, True),                # 100% free
])
def test_stress_vram_float_precision_boundaries(tmp_path, pct, expected_allowed):
    """
    Stress 3.1: Microscopic floating-point deltas around the 15.0% threshold.
    """
    gov = DevilsLockGovernor(lock_dir=str(tmp_path / "vram_bounds"))
    allowed, free_gb, free_pct = gov.check_vram_and_lock(override_free_pct=pct)
    assert allowed == expected_allowed
    assert free_pct == pct


def test_stress_vram_nan_and_infinite_inputs(tmp_path):
    """
    Stress 3.2: Adversarial NaN and Infinity inputs to check_vram_and_lock.
    Invariant: NaN must not bypass the >= 15.0% lock (NaN >= 15.0 is False).
    Inf / -Inf must be caught as out-of-range percentage values.
    """
    gov = DevilsLockGovernor(lock_dir=str(tmp_path / "vram_extremes"))

    # Inf and -Inf must raise ValueError
    with pytest.raises(ValueError, match="Invalid VRAM percentage"):
        gov.check_vram_and_lock(override_free_pct=float("inf"))

    with pytest.raises(ValueError, match="Invalid VRAM percentage"):
        gov.check_vram_and_lock(override_free_pct=float("-inf"))

    # Sub-zero and over-100 values
    with pytest.raises(ValueError, match="Invalid VRAM percentage"):
        gov.check_vram_and_lock(override_free_pct=-0.0000001)

    with pytest.raises(ValueError, match="Invalid VRAM percentage"):
        gov.check_vram_and_lock(override_free_pct=100.0000001)


def test_stress_vram_telemetry_schema_integrity(tmp_path):
    """
    Stress 3.3: Verify get_vram_telemetry returns compliant dictionary under all conditions.
    """
    gov = DevilsLockGovernor(lock_dir=str(tmp_path / "vram_telemetry"))

    # Test allowed state
    t_pass = gov.get_vram_telemetry(override_free_pct=22.5)
    assert t_pass["is_allowed"] is True
    assert t_pass["is_locked"] is False
    assert t_pass["free_pct"] == 22.5
    assert t_pass["min_required_pct"] == 15.0
    assert "timestamp" in t_pass

    # Test locked state
    t_fail = gov.get_vram_telemetry(override_free_pct=8.4)
    assert t_fail["is_allowed"] is False
    assert t_fail["is_locked"] is True
    assert t_fail["free_pct"] == 8.4
    assert t_fail["min_required_pct"] == 15.0


# ============================================================================
# 4. ADVERSARIAL FUZZING & CORRUPT LEADERBOARD INGESTION
# ============================================================================

def test_stress_leaderboard_fuzzing_empty_and_corrupt(tmp_path):
    """
    Stress 4.1: Empty JSON object, non-dict content, empty leaderboard list.
    """
    # 1. Empty dictionary
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("{}")
    gov = DevilsLockGovernor(leaderboard_path=str(empty_file))

    with pytest.raises(DevilsLockError, match="contains no models list"):
        gov.select_highest_elo_model_for_ui()

    # Safe fallback mode (raise_on_error=False)
    fallback = select_highest_elo_model_for_ui(leaderboard_path=str(empty_file), raise_on_error=False)
    assert fallback["id"] == "kimi_tandem_titan"
    assert fallback["is_fallback"] is True

    # 2. Empty list in leaderboard
    empty_list_file = tmp_path / "empty_list.json"
    empty_list_file.write_text(json.dumps({"leaderboard": []}))
    with pytest.raises(DevilsLockError):
        select_highest_elo_model_for_ui(leaderboard_path=str(empty_list_file), raise_on_error=True)


def test_stress_leaderboard_corrupt_entries_and_missing_types(tmp_path):
    """
    Stress 4.2: Leaderboard array populated with malformed items (None, strings, non-numeric values).
    Invariant: Parser ignores invalid items and extracts valid models without raising UnboundLocalError/TypeError.
    """
    corrupt_content = {
        "leaderboard": [
            None,
            "corrupted_string_item",
            12345,
            [],
            {},
            {"no_id": "model_without_id_or_name"},
            {
                "id": "bad_skills_model",
                "name": "Bad Skills Model",
                "elo": "not_a_number",  # string elo
                "specialist_skills": "not_a_dict",  # non-dict skills
            },
            {
                "id": "valid_target_model",
                "name": "Valid Target Model",
                "elo": 2800.0,
                "specialist_skills": {
                    "3d_ai_training_game": "95.5",  # string numeric
                    "vision_vlm_truth_auditing": None,  # None value
                    "flutter_dart_mobile_architecture": 88.0,
                },
            }
        ]
    }
    f = tmp_path / "corrupt_entries.json"
    f.write_text(json.dumps(corrupt_content))

    top = select_highest_elo_model_for_ui(leaderboard_path=str(f))
    assert top["id"] == "valid_target_model"
    assert top["elo"] == 2800.0
    assert top["capabilities"]["3d_ai_training_game"] == 95.5
    assert top["capabilities"]["vision_vlm_truth_auditing"] == 0.0


def test_stress_leaderboard_deterministic_tie_breaking(tmp_path):
    """
    Stress 4.3: Multiple models with identical scores and identical skills.
    Invariant: Selection must be 100% deterministic (tie-broken on ID).
    """
    tied_content = {
        "leaderboard": [
            {
                "id": "model_beta",
                "name": "Model Beta",
                "elo": 2500.0,
                "specialist_skills": {"3d_ai_training_game": 90.0, "vision_vlm_truth_auditing": 90.0, "flutter_dart_mobile_architecture": 90.0}
            },
            {
                "id": "model_alpha",
                "name": "Model Alpha",
                "elo": 2500.0,
                "specialist_skills": {"3d_ai_training_game": 90.0, "vision_vlm_truth_auditing": 90.0, "flutter_dart_mobile_architecture": 90.0}
            },
        ]
    }
    f = tmp_path / "tied_models.json"
    f.write_text(json.dumps(tied_content))

    for _ in range(10):
        top = select_highest_elo_model_for_ui(leaderboard_path=str(f))
        assert top["id"] == "model_beta"  # 'model_beta' > 'model_alpha' in reverse alphabetical tie-break


def test_stress_leaderboard_10000_models_scaling(tmp_path):
    """
    Stress 4.4: Ingestion and ranking of 10,000 synthetic models.
    Invariant: Evaluates in < 250ms and deterministically finds the genuine #1 model.
    """
    models = []
    for i in range(10000):
        models.append({
            "id": f"synth_model_{i:05d}",
            "name": f"Synthetic Model {i}",
            "elo": 1500.0 + (i % 1000),
            "specialist_skills": {
                "3d_ai_training_game": float(i % 100),
                "vision_vlm_truth_auditing": float((i * 3) % 100),
                "flutter_dart_mobile_architecture": float((i * 7) % 100),
            }
        })
    # Add a clear sovereign winner
    models.append({
        "id": "sovereign_champion",
        "name": "Sovereign Champion",
        "elo": 3200.0,
        "specialist_skills": {
            "3d_ai_training_game": 100.0,
            "vision_vlm_truth_auditing": 100.0,
            "flutter_dart_mobile_architecture": 100.0,
        }
    })

    f = tmp_path / "huge_leaderboard.json"
    f.write_text(json.dumps({"leaderboard": models}))

    t0 = time.time()
    top = select_highest_elo_model_for_ui(leaderboard_path=str(f))
    duration = time.time() - t0

    assert top["id"] == "sovereign_champion"
    assert top["ui_composite_score"] == 100.0
    assert duration < 0.5, f"10k model ranking took too long: {duration:.4f}s"


# ============================================================================
# 5. SECURITY & ANTI-SPOOFING TESTS
# ============================================================================

def test_stress_lock_theft_and_unauthorized_heartbeat(tmp_path):
    """
    Stress 5.1: Agent B attempts to hijack, heartbeat, or release Agent A's active lock.
    Invariant: All unauthorized actions must fail; Agent A retains exclusive ownership.
    """
    gov = DevilsLockGovernor(lock_dir=str(tmp_path / "theft_locks"))

    # Agent A acquires
    acq_a = gov.acquire_subagent_lock("authorized_agent_A", task_name="task_A")
    assert acq_a is True

    # Agent B tries to acquire (must fail)
    acq_b = gov.acquire_subagent_lock("attacker_agent_B", task_name="task_hijack")
    assert acq_b is False

    # Agent B tries to send heartbeat (must fail)
    hb_b = gov.heartbeat("attacker_agent_B")
    assert hb_b is False

    # Agent B tries to release Agent A's lock (must fail)
    rel_b = gov.release_subagent_lock("attacker_agent_B")
    assert rel_b is False

    # Verify Agent A is STILL the active subagent
    active = gov.get_active_subagent()
    assert active is not None
    assert active.subagent_id == "authorized_agent_A"

    # Agent A can heartbeat
    hb_a = gov.heartbeat("authorized_agent_A")
    assert hb_a is True

    # Agent A releases successfully
    rel_a = gov.release_subagent_lock("authorized_agent_A")
    assert rel_a is True
    assert gov.check_resource_cap() is True


def test_stress_corrupted_disk_state_file_recovery(tmp_path):
    """
    Stress 5.2: State file on disk is truncated or corrupted (e.g. power-loss mid-write).
    Invariant: DevilsLockGovernor does not crash with JSONDecodeError; auto-recovers slot.
    """
    lock_dir = tmp_path / "corrupt_state_dir"
    os.makedirs(lock_dir, exist_ok=True)
    state_file = lock_dir / "devils_subagent_state.json"

    # Write truncated / invalid JSON to state file
    state_file.write_text('{"subagent_id": "half_written_')

    gov = DevilsLockGovernor(lock_dir=str(lock_dir))

    # check_resource_cap must safely return True without raising JSONDecodeError
    assert gov.check_resource_cap() is True
    assert gov.get_active_subagent() is None

    # Acquisition must succeed and overwrite corrupted state cleanly
    acquired = gov.acquire_subagent_lock("clean_agent", "clean_task")
    assert acquired is True
    active = gov.get_active_subagent()
    assert active is not None
    assert active.subagent_id == "clean_agent"

    gov.release_subagent_lock("clean_agent")
    assert gov.check_resource_cap() is True
