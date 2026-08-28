# Task Assignment: Sub-Orchestrator / Lead Worker for Milestone 5 (E2E Verification & Swarm Truth Audit)

## Context
You are the Sub-Orchestrator / Lead Worker for Milestone 5.
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m5
Workspace root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Parent Orchestrator: orchestrator_1 (d95629f0-67b4-4715-bb72-85614989a0a6)

## Mandatory Reading
1. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`.
2. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md`.
3. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/TEST_INFRA.md` and `TEST_READY.md`.

## Milestone Scope (M5: E2E Verification & Swarm Truth Audit)
Execute and verify:
1. **Phase 1 — 100% E2E Test Suite Execution**:
   - Run full pytest test suite across Tier 1 (Feature Coverage), Tier 2 (Boundary & Corner Cases), Tier 3 (Cross-Feature Combinations), and Tier 4 (Real-World Workloads):
     - `tests/test_meta_training_tier1_features.py`
     - `tests/test_meta_training_tier2_boundaries.py`
     - `tests/test_meta_training_tier3_combinations.py`
     - `tests/test_meta_training_tier4_scenarios.py`
     - `tests/test_elo_engine.py`
     - `tests/test_task_dispatch_routing.py`
     - `tests/test_debate_consensus.py`
     - `tests/verify_task_dispatch_routing.py`
2. **Phase 2 — Adversarial Hardening (Tier 5)**:
   - Create and execute `tests/test_meta_training_tier5_adversarial.py` to test adversarial edge cases:
     (a) High-concurrency race conditions during live debate execution.
     (b) Corrupt / malformed debate payloads and AST injection attacks.
     (c) FIDE ELO extreme delta boundary invariance.
     (d) Zero-cloud-spend bypass attempts and truth audit failures ($\eta_{\text{truth}} = 0$).
3. **Phase 3 — Swarm Truth Audit Pass (Zero-Mock Rule #0 Verification)**:
   - Audit `00_core_infrastructure/self_healing_hub/frontend/src/MetaTrainingGameDashboardView.jsx`, `api_server.py`, `canonical_ai_leaderboard.py`, `task_dispatch_engine.py`, and `ai_debate_engine.py`.
   - Verify that 0 banned mock markers, fake arrays, or bypass logic exist in production runtime code.
   - Verify that Vite frontend compiles cleanly (`npm run build`).

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work.

When complete, write your handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m5/handoff.md` and message parent (d95629f0-67b4-4715-bb72-85614989a0a6).
