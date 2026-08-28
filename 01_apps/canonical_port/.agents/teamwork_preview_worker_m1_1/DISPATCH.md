## 2026-08-28T17:27:53Z

You are Worker 1 for Milestone 1 (4-Way Debate Governance - The Devil's Lock).
Your working directory is /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_worker_m1_1
Project root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port

Read:
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/PROJECT.md
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_m1_1/handoff.md
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_m1_2/handoff.md
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_m1_3/handoff.md

Write Ownership:
You own `backend/devils_lock_governor.py` and `tests/unit/test_devils_lock_governance.py`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task:
1. Implement the complete, production-grade `backend/devils_lock_governor.py` (`DevilsLockGovernor`, `DevilsLockError`, `ResourceCapExceededError`, `VRAMTelemetryError`, `GeneticELOMandateError`):
   - **Resource Cap Gate**: Max 1 active subagent simultaneously. Thread-safe (`threading.RLock`) + atomic state, stale PID auto-healing (`os.kill(pid, 0)`), acquire/release lifecycle.
   - **VRAM Headroom Check**: `check_vram_and_lock(override_free_pct=None) -> Tuple[bool, float, float]` strictly blocking if free VRAM < 15.0%. Direct query to `psutil.virtual_memory()` and `blackboard_store.get_snapshot().layer_1_hardware` without fake data (Rule #0).
   - **Genetic ELO Mandate**: `select_highest_elo_model_for_ui(leaderboard_path=None) -> Dict[str, Any]` reading `04_data_and_memory/data/canonical_ai_leaderboard.json` and ranking models based on UI domain skills (`3d_ai_training_game`, `vision_vlm_truth_auditing`, `flutter_dart_mobile_architecture`, ELO).
   - **Preflight Validator**: `validate_preflight_locks()` executing all 3 gates in sequence.
2. Run pytest to verify all test suites in `tests/unit/test_devils_lock_governance.py`:
   `uv run pytest tests/unit/test_devils_lock_governance.py -v`
3. Document build/test results, commands executed, and layout compliance in your handoff report at `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_worker_m1_1/handoff.md`.

Update progress.md and send message when complete.
