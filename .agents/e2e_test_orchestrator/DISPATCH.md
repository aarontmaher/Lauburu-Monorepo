# Task Assignment: E2E Testing Track Orchestrator

## Context
You are the E2E Testing Track Orchestrator.
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/e2e_test_orchestrator
Workspace root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Parent Orchestrator: orchestrator_1 (d95629f0-67b4-4715-bb72-85614989a0a6)

## Mandatory Reading
1. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`.
2. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md`.

## Mission & Scope
Own the E2E Testing Track for the entire project.
1. Create `TEST_INFRA.md` at the project root (`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/TEST_INFRA.md`).
2. Design and build a comprehensive 4-tier test suite:
   - **Tier 1 (Feature Coverage)**: Tests for each feature in `PROJECT.md § Feature Inventory` (ELO calculation, Debate turn execution, Task dispatch routing, Dashboard endpoint availability).
   - **Tier 2 (Boundary & Corner Cases)**: Edge cases (K-factor clamping, division by zero in latency, missing API keys, concurrent writes).
   - **Tier 3 (Cross-Feature Combinations)**: Debate win -> ELO ledger update -> Task dispatch router verification.
   - **Tier 4 (Real-World Application Scenarios)**: Real task routing across subsystems with zero mock arrays and live verification.
3. Once test suite is created and passing, publish `TEST_READY.md` at project root.

## Execution Rules
- As an orchestrator, assess, decompose, and delegate test implementation to specialist subagents (e.g. `teamwork_preview_test_writer`, `teamwork_preview_worker`, `teamwork_preview_reviewer`, `teamwork_preview_auditor`).
- Send regular progress reports and notify orchestrator_1 when complete.
