# Task Assignment: Sub-Orchestrator / Lead Worker for Milestone 4 (Meta-Training Dashboard on localhost:3000)

## Context
You are the Sub-Orchestrator / Lead Worker for Milestone 4.
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m4
Workspace root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Parent Orchestrator: orchestrator_1 (d95629f0-67b4-4715-bb72-85614989a0a6)

## Mandatory Reading
1. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`.
2. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md`.
3. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_1/handoff.md`.

## Milestone Scope (M4: Meta-Training Dashboard on localhost:3000)
Implement and verify:
1. **React 19 + Vite 8 Frontend Component**:
   - Create `00_core_infrastructure/self_healing_hub/frontend/src/MetaTrainingGameDashboardView.jsx` (and sync to `self_healing_hub/frontend/src/`).
   - Integrate with `App.jsx` navigation bar to provide a prominent "Meta-Training Game & AI Debate" view.
   - Render:
     (a) **Tri-Orchestrator Debate Arena**: Model selectors (Kimi, Claude 4.6, Gemini 3.7, Opus 4.6), turn-by-turn deliberation feed (Theses, Cross-Exam, Concession, Accord), and CoT reasoning trees.
     (b) **Consensus & Telemetry Panel**: Agreement gauge (0-100%), Evolutionary Fitness dial, token spend velocity, $0 cloud spend tracker.
     (c) **Canonical ELO & Real Task Dispatcher**: Live FIDE ELO standings table, 29 specialist skill radar, and 1-click real project task router mapping in-game victories to monorepo task execution.
2. **Backend API Endpoints in `00_core_infrastructure/self_healing_hub/src/api_server.py`**:
   - `POST /api/debate/execute_ui_debate`: executes live debate via `TriOrchestratorDebateEngine` and returns full transcript, consensus accord, and injected priorities.
   - `POST /api/dispatch/route_task`: routes real monorepo tasks via `TaskDispatchEngine` and executes bidirectional AST validation.
   - `GET /api/canonical_ai_leaderboard`: serves real canonical ELO ledger.
3. **Frontend Build & Linter Verification**:
   - Run `npm run build` and `npm run lint` in `00_core_infrastructure/self_healing_hub/frontend` (and `self_healing_hub/frontend`).
   - Ensure clean compilation with zero build errors.
4. **Zero-Mock Rule #0 Compliance**:
   - Ensure all telemetry, ELO standings, debate transcripts, and task dispatch results are connected to authentic backend engines and data files without fake arrays or simulated numbers.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work.

When complete, write your handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m4/handoff.md` and message parent (d95629f0-67b4-4715-bb72-85614989a0a6).
