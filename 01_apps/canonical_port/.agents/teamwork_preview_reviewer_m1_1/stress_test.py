import os
import sys
import tempfile
import threading
import multiprocessing
import time
from pathlib import Path

# Add project root
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port")

from backend.devils_lock_governor import (
    DevilsLockGovernor,
    DevilsLockError,
    ResourceCapExceededError,
    VRAMHeadroomExceededError,
    select_highest_elo_model_for_ui,
)

def _worker_proc(proc_id, lock_dir_path, success_list):
    gov = DevilsLockGovernor(lock_dir=lock_dir_path)
    ok = gov.acquire_subagent_lock(f"proc_agent_{proc_id}", f"task_{proc_id}")
    if ok:
        time.sleep(0.05)
        gov.release_subagent_lock(f"proc_agent_{proc_id}")
        success_list.append(proc_id)

def test_multiprocess_contention(lock_dir_path, num_procs=8):
    manager = multiprocessing.Manager()
    success_list = manager.list()
    processes = []
    for i in range(num_procs):
        p = multiprocessing.Process(target=_worker_proc, args=(i, lock_dir_path, success_list))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    print(f"Multiprocess contention test: {len(success_list)} total sequential completions")
    assert len(success_list) >= 1

def test_leaderboard_edge_cases():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Edge case: Empty dict
        empty_file = Path(tmpdir) / "empty.json"
        empty_file.write_text("{}")
        try:
            select_highest_elo_model_for_ui(leaderboard_path=empty_file)
            print("FAILED: Empty dict should have raised DevilsLockError")
            assert False
        except DevilsLockError:
            print("PASSED: Empty dict correctly raised DevilsLockError")

        # Edge case: Corrupt types in specialist skills
        corrupt_skills_file = Path(tmpdir) / "corrupt_skills.json"
        corrupt_skills_file.write_text('''
        {
            "leaderboard": [
                {
                    "id": "bad_model_1",
                    "name": "Bad Model",
                    "elo": "invalid_elo",
                    "specialist_skills": {
                        "3d_ai_training_game": "not_a_number",
                        "vision_vlm_truth_auditing": null
                    }
                },
                {
                    "id": "good_model_1",
                    "name": "Good Model",
                    "elo": 2500,
                    "specialist_skills": {
                        "3d_ai_training_game": 90,
                        "vision_vlm_truth_auditing": 90
                    }
                }
            ]
        }
        ''')
        res = select_highest_elo_model_for_ui(leaderboard_path=corrupt_skills_file)
        assert res["id"] == "good_model_1", f"Expected good_model_1, got {res['id']}"
        print("PASSED: Corrupt types in skills handled gracefully, selected good model")

def test_reentrancy():
    with tempfile.TemporaryDirectory() as tmpdir:
        gov = DevilsLockGovernor(lock_dir=tmpdir)
        # Acquire
        assert gov.acquire_subagent_lock("agent_x", "task_x") is True
        # Re-acquire with same agent_id should succeed (reentrant heartbeat)
        assert gov.acquire_subagent_lock("agent_x", "task_x") is True
        # Acquire with different agent_id should fail
        assert gov.acquire_subagent_lock("agent_y", "task_y") is False
        # Release by agent_x
        assert gov.release_subagent_lock("agent_x") is True
        # Now agent_y can acquire
        assert gov.acquire_subagent_lock("agent_y", "task_y") is True
        gov.release_subagent_lock("agent_y")
        print("PASSED: Reentrancy and ownership enforcement works as expected")

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        test_multiprocess_contention(tmpdir)
    test_leaderboard_edge_cases()
    test_reentrancy()
    print("ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY!")
