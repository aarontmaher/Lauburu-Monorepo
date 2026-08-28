# BRIEFING — 2026-08-29T03:24:00Z

## Mission
Investigate and design the Resource Cap (max 1 active subagent) locking mechanism for backend/devils_lock_governor.py (Milestone 1 - The Devil's Lock).

## 🔒 My Identity
- Archetype: explorer
- Roles: [explorer, investigator, architect]
- Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_m1_1
- Original parent: 64c5f266-2327-4c3a-b1ed-10c1d5e6a5c7
- Milestone: Milestone 1 (4-Way Debate Governance - The Devil's Lock)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Design thread-safe and process-safe concurrency locking (e.g. threading.Lock + file-based PID lock / atomic state)
- Max 1 active subagent enforcement
- Clean recovery from crashed/dead PIDs without leaving stale locks
- Output findings and recommendation in handoff.md

## Current Parent
- Conversation ID: 64c5f266-2327-4c3a-b1ed-10c1d5e6a5c7
- Updated: not yet

## Investigation State
- **Explored paths**: `PROJECT.md`, `ORIGINAL_REQUEST.md`, `TEST_INFRA.md`, `backend/`, `tui/services/blackboard_store.py`, `tests/conftest.py`, peer explorer dispatch files (`teamwork_preview_explorer_m1_2`, `teamwork_preview_explorer_m1_3`).
- **Key findings**: Designed dual-layer locking mechanism: in-memory `threading.RLock()` for thread safety + kernel advisory `fcntl.flock(LOCK_EX | LOCK_NB)` for process safety with zero stale-lock vulnerability on process crash; paired with atomic metadata state (`devils_subagent_state.json`) and active `os.kill(pid, 0)` liveness probing for dead PID self-healing.
- **Unexplored areas**: None. Architecture, contracts, error hierarchy, crash recovery, and unit test specifications fully analyzed and ready for synthesis.

## Key Decisions Made
- Use POSIX `fcntl.flock` + `threading.RLock` to guarantee both multi-thread and multi-process exclusivity.
- Use `os.kill(pid, 0)` with POSIX error handling (`ProcessLookupError` vs `PermissionError`) to determine genuine PID liveness.
- Implement atomic JSON persistence (`.tmp.<pid>.<tid>` + `os.replace`) for subagent registration state.
- Formulate rich error hierarchy with base `DevilsLockError` and subclasses `ResourceCapExceededError`, `VRAMHeadroomExceededError`, and `LeaderboardSelectionError`.
- Specify 8 comprehensive unit test categories for test writer and implementer.

## Artifact Index
- DISPATCH.md — Task assignment from parent orchestrator
- BRIEFING.md — Situational awareness memory
- progress.md — Liveness heartbeat
- handoff.md — Comprehensive 5-component handoff report
