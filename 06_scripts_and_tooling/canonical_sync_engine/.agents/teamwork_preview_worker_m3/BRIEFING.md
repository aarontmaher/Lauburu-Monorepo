# BRIEFING — 2026-08-27T07:30:45+10:00

## Mission
Implement Milestone 3 (M3: Canonical Sync Engine & CLI Interface) for `canonical_sync_engine`, integrating quad-vault syncers, health verification, self-healing, CLI interface, and comprehensive integration test suites.

## 🔒 My Identity
- Archetype: teamwork_preview_worker_m3
- Roles: [implementer, qa, specialist]
- Working directory: /Users/aaron/teamwork_projects/canonical_sync_engine/.agents/teamwork_preview_worker_m3
- Original parent: 9162dc6c-ca26-43f1-9c53-d3d1357db0e1
- Milestone: M3: Canonical Sync Engine & CLI Interface

## 🔒 Key Constraints
- Canonical rule adherence: 7-Layer Mesh, Tri/Quad-Vault Storage Architecture, Rule 6.2 Pre-Flight Self-Healing, Fast-path verification < 3ms.
- Exclusive Write Ownership:
  - `canonical_sync_engine/engine/__init__.py`
  - `canonical_sync_engine/engine/coordinator.py`
  - `canonical_sync_engine/cli/__init__.py`
  - `canonical_sync_engine/cli/main.py`
  - `tests/integration/__init__.py`
  - `tests/integration/test_sync_engine.py`
  - `tests/integration/test_cli.py`
- Zero-mock & Genuine Implementation Mandate: No hardcoded test outputs or dummy facades.
- All tests must pass (100% pass on `pytest tests/ -v`).

## Current Parent
- Conversation ID: 9162dc6c-ca26-43f1-9c53-d3d1357db0e1
- Updated: not yet

## Task Summary
- **What to build**: `CanonicalSyncEngine` in `engine/coordinator.py`, CLI commands in `cli/main.py`, and comprehensive integration tests in `tests/integration/`.
- **Success criteria**: Full integration of storage verifier, self-healing, quad-vault syncers (PySpark, Obsidian, Git, GDrive), parallel/sequential execution, post-sync verification, rollback/degraded tracking, batch sync, CLI tools (`verify`, `heal`, `sync`, `status`, `info`), and 100% passing tests.
- **Interface contracts**: `/Users/aaron/teamwork_projects/canonical_sync_engine/PROJECT.md`
- **Code layout**: `/Users/aaron/teamwork_projects/canonical_sync_engine/PROJECT.md`

## Key Decisions Made
- [TBD]

## Artifact Index
- `.agents/teamwork_preview_worker_m3/DISPATCH.md` — Assignment requirements
- `.agents/teamwork_preview_worker_m3/BRIEFING.md` — Agent state and briefing
- `.agents/teamwork_preview_worker_m3/progress.md` — Progress tracker and heartbeat
- `.agents/teamwork_preview_worker_m3/handoff.md` — Final handoff report

## Change Tracker
- **Files modified**: None yet
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Clean
- **Tests added/modified**: Pending
