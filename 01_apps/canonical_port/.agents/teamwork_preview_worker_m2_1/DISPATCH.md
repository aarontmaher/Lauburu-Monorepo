## 2026-08-28T17:41:20Z
You are Worker 1 for Milestone 2 (Git Worktree Sandboxing & Telemetry Daemon).
Your working directory is /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_worker_m2_1
Project root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port

Read:
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/PROJECT.md
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_survey_2/handoff.md
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_test_writer_e2e_1/handoff.md
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/backend/devils_lock_governor.py

Write Ownership:
You own `backend/worktree_sandbox.py`, `backend/tui_specialist_daemon.py`, `tests/unit/test_worktree_sandbox.py`, and `tests/unit/test_tui_specialist_daemon.py`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task:
1. Implement `backend/worktree_sandbox.py`:
   - `WorktreeSandbox`: dynamically creates branched Git Worktrees in `/tmp/lauburu_worktrees/` via `git worktree add -b <branch_name> <worktree_dir> HEAD`.
   - Ensures `01_apps` is NEVER directly mutated by autonomous subagents.
   - Provides isolation verification (`verify_sandbox_isolation()`), active worktree tracking, and robust teardown/cleanup (`git worktree remove --force`, `git worktree prune`).
2. Implement `backend/tui_specialist_daemon.py`:
   - `TuiSpecialistDaemon`: monitors network telemetry (`04_data_and_memory/mesh_trends.json`), detects degradation/events, checks Devil's Lock preflight gates (`DevilsLockGovernor.validate_preflight_locks()`), spawns isolated worktrees, and logs live stream events to `04_data_and_memory/tui_live_implementation_stream.json`.
3. Run and verify unit tests:
   `uv run pytest tests/unit/test_worktree_sandbox.py tests/unit/test_tui_specialist_daemon.py -v`
4. Document build/test results, commands executed, and layout compliance in your handoff report at `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_worker_m2_1/handoff.md`.

Update progress.md and send message when complete.
