# Dispatch: Worker M3 (Project-Specific ELO & Confidence Evaluation Engine)

## Identity
- Role: Worker for Milestone 3
- TypeName: teamwork_preview_worker
- Assigned Working Directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m3
- Orchestrator: teamwork_preview_orchestrator_23 (878c1253-0956-4401-91a5-0f3927d54244)

## Mandatory Rules & Warnings
MANDATORY FIRST STEP: Read the authoritative original request file:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You exclusively own:
- `00_core_infrastructure/router_ai_daemon/src/elo/elo_engine.py`
- `00_core_infrastructure/router_ai_daemon/tests/test_elo.py`

Do NOT modify any files outside this path.

## Explorer Survey Findings to Implement
Review findings in:
`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_elo/analysis.md`
`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_elo/handoff.md`

Tasks:
1. In `elo_engine.py`:
   - Enforce rating boundary clamping to [1000.0, 3000.0] in `evaluate_match_deltas` and `record_code_off_result` (e.g. `max(1000.0, min(3000.0, new_rating))`).
   - Clamp the exponent in `calculate_expected_score` to [-20.0, 20.0] to prevent `OverflowError`.
   - Implement `calculate_wilson_confidence_interval(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]` for empirical confidence intervals on finite Bernoulli trials without physical sensors.
   - Implement data classes / structures:
     * `CategoryScorecard`: category (str), rating (float), confidence_interval (Tuple[float, float]), trials (int), passes (int).
     * `ProjectEloScorecard`: timestamp, frontend (CategoryScorecard), backend (CategoryScorecard), ai_models (CategoryScorecard), composite_score (float), evaluation_latency_us (float).
   - Implement `evaluate_project_scorecard(frontend_trials: Tuple[int, int], backend_trials: Tuple[int, int], ai_trials: Tuple[int, int], ...) -> ProjectEloScorecard` executing in <= 50 µs.
2. In `tests/test_elo.py`:
   - Preserve all existing 20 unit/integration tests.
   - Add tests for:
     * Upper and lower bounds clamping [1000.0, 3000.0].
     * Exponent overflow protection against huge rating differences.
     * Wilson score confidence interval mathematical correctness across edge cases (k=0, k=n, large n).
     * 3-Category Scorecard evaluation correctness across Frontend, Backend, AI Models.
     * Latency benchmark asserting mean evaluation latency <= 50.0 µs across 10,000 runs.
3. Run tests:
   `pytest -v 00_core_infrastructure/router_ai_daemon/tests/test_elo.py`
   Verify all tests pass cleanly.

## Output Requirements
- Write your completion report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m3/handoff.md`
- Include test execution results in your report.
- Send a completion message to the parent orchestrator via send_message.
