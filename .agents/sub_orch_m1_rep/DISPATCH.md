# Task Assignment: Sub-Orchestrator Milestone 1 Replacement (Canonical ELO Ledger & Math Engine)

## Context
You are the Sub-Orchestrator for Milestone 1 (sub_orch_m1_rep).
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m1_rep
Workspace root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Parent Orchestrator: orchestrator_1 (d95629f0-67b4-4715-bb72-85614989a0a6)

## Mandatory Reading
1. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`.
2. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md`.
3. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_2_rep/handoff.md`.

## Milestone Scope (M1: Canonical ELO Ledger & Math Engine)
Implement and verify:
1. **Canonical JSON ELO Ledger**: Validate and enforce JSON Schema v7 validation on `data/canonical_ai_leaderboard.json` with atomic disk persistence (`os.replace`) and 19+ specialist skill definitions in `00_core_infrastructure/self_healing_hub/src/canonical_ai_leaderboard.py`.
2. **Multi-Factor Dynamic ELO Formula**: Implement $E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}$ with dynamic K-factors scaling by parameter efficiency ($\eta_{\text{size}} = \max(0.5, \frac{\log_2(71)}{\log_2(\text{params}+1)})$), token frugality ($\eta_{\text{token}}$), consensus alignment ($\eta_{\text{consensus}}$), compute latency ($\eta_{\text{compute}}$), and truth compliance ($\eta_{\text{truth}}$).
3. **Unit Test Suite**: Write and execute `tests/test_elo_engine.py` validating mathematical symmetry, zero-delta conservation, parameter efficiency curves, schema validity, and zero-mock integrity.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work.

When complete and verified, write your handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m1_rep/handoff.md` and message parent (d95629f0-67b4-4715-bb72-85614989a0a6).
