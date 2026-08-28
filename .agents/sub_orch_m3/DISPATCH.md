# Task Assignment: Sub-Orchestrator / Lead Worker for Milestone 3 (Success Mapping & Real Task Dispatch Engine)

## Context
You are the Sub-Orchestrator / Lead Worker for Milestone 3.
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m3
Workspace root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Parent Orchestrator: orchestrator_1 (d95629f0-67b4-4715-bb72-85614989a0a6)

## Mandatory Reading
1. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`.
2. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md`.
3. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_2_rep/handoff.md`.

## Milestone Scope (M3: Success Mapping & Real Task Dispatch Engine)
Implement and verify:
1. **`TaskDispatchEngine` (`00_core_infrastructure/self_healing_hub/src/task_dispatch_engine.py`)**:
   - Ingests real monorepo project tasks across all 13 subsystems (`00_core_infrastructure` through `12_continuous_lora_evolution`).
   - Evaluates required skills, cloud spend constraints ($0 target), and truth compliance.
   - Computes composite match fitness ($\text{Fitness} = 0.40 \cdot \text{ELO}_{\text{norm}} + 0.40 \cdot \text{Skill}_{\text{score}} + 0.20 \cdot \text{Benchmark}_{\text{score}}$) by querying `data/canonical_ai_leaderboard.json`.
   - Dynamically selects and routes the Rank #1 candidate.
2. **Bidirectional Feedback Loop**:
   - Executes real monorepo task validation (AST parse pass, pytest pass, latency) and updates Project Contribution ELO in `data/canonical_ai_leaderboard.json`.
3. **Task Routing Verifier Script (`tests/verify_task_dispatch_routing.py`)**:
   - Standalone executable script that:
     (a) Simulates a debate duel between models where Model A wins.
     (b) Records victory to canonical ledger.
     (c) Submits a real monorepo project task.
     (d) Asserts that `TaskDispatchEngine` routes the task to the model with the highest ELO from the game.
     (e) Exits with code 0.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work.

When complete, write your handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m3/handoff.md` and message parent (d95629f0-67b4-4715-bb72-85614989a0a6).

## 2026-08-24T10:01:09Z
Execute Milestone 3:
1. Implement TaskDispatchEngine in 00_core_infrastructure/self_healing_hub/src/task_dispatch_engine.py querying data/canonical_ai_leaderboard.json to dynamically route real monorepo project tasks across all 13 subsystems (00_core_infrastructure to 12_continuous_lora_evolution) to the top-ELO model.
2. Implement bidirectional feedback loop updating Project Contribution ELO upon verified task execution.
3. Implement and execute tests/verify_task_dispatch_routing.py verifying that an in-game debate victory routes a real project task to the winning top-ELO model.
DO NOT CHEAT. All implementations must be genuine.

