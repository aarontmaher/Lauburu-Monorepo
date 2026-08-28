## 2026-08-26T21:15:42Z

You are an Explorer agent for Milestone 1 (M1.2: Storage Invariants & Pre-Flight Self-Healing).
Your Working Directory: /Users/aaron/teamwork_projects/canonical_sync_engine/.agents/teamwork_preview_explorer_m1_2
Original Request Path: /Users/aaron/teamwork_projects/canonical_sync_engine/ORIGINAL_REQUEST.md
Project Scope Document: /Users/aaron/teamwork_projects/canonical_sync_engine/PROJECT.md

Task:
Read ORIGINAL_REQUEST.md and PROJECT.md.
Investigate and design the implementation details for:
1. `canonical_sync_engine/verification/fast_path.py`: Sub-3ms check checking inode existence and free headroom >= 5.0 GB per Rule 6.3.
2. `canonical_sync_engine/verification/headroom.py`: Free space checking (shutil.disk_usage / os.statvfs) enforcing >= 10.0 GB headroom requirement.
3. `canonical_sync_engine/verification/invariants.py`: Checking Obsidian Index.md existence with Wikilinks (`[[Index]]`, `[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]`, `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`), PySpark datasets directory health, Git repo valid worktree and absent `.git/index.lock`.
4. `canonical_sync_engine/verification/self_healer.py`: Rule 6.2 automated self-healing (mkdir -p vault dirs, remove stale `.git/index.lock` if older than threshold, recreate missing `Index.md` with master Wikilinks, purge transient caches if headroom < 5GB).
5. Specify exact unit test cases for `tests/unit/test_verification.py` and `tests/unit/test_self_healer.py`.

Write your full exploration report to `/Users/aaron/teamwork_projects/canonical_sync_engine/.agents/teamwork_preview_explorer_m1_2/m1_exploration_report.md` and write your handoff.md. Send a completion message when done.
