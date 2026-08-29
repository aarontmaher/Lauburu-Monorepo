# BRIEFING — 2026-08-29T19:02:55+10:00

## Mission
Implement and deploy Unified Lauburu Front-Facing App Architecture & Multi-Mode Game Arena with 100% local airgap biometrics.

## 🔒 My Identity
- Archetype: teamwork_preview_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_1/
- Original parent: parent
- Original parent conversation ID: 23d306eb-b150-4e1b-8954-8e4866f3d375

## 🔒 My Workflow
- **Pattern**: Project Orchestration
- **Scope document**: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md
1. **Decompose**: Survey monorepo, build Feature Inventory, decompose into 3-7 milestones + E2E Testing track.
2. **Dispatch & Execute**:
   - Survey: 3 parallel Explorers (Frontend/Airgap, Biometrics/Movesense DSP, SmolAgents/Multi-Mode Arena).
   - Milestone Implementation: Sub-orchestrator per milestone executing iteration loop (Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate).
   - E2E Testing: Dedicated parallel E2E Testing Orchestrator (Tiers 1-4).
   - Final Milestone: Pass 100% E2E tests + Tier 5 Adversarial Coverage Hardening.
3. **On failure**:
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical, auditor is NON-SKIPPABLE)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
4. **Succession**: Self-succeed at 16 spawns after active subagents complete.
- **Work items**:
  1. Phase 0: Monorepo Survey & Feature Mapping [in-progress]
  2. Phase 1: PROJECT.md Decomposition & Interface Contracts [pending]
  3. Phase 2: Dual-Track Dispatch (Milestones + E2E Testing) [pending]
  4. Phase 3: Final Milestone E2E & Tier 5 Hardening [pending]
- **Current phase**: 0
- **Current focus**: Phase 0 Monorepo Survey

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore problem at code level — dispatch Explorers.
- Rule #0: Strictly zero simulated or fake arrays.
- Tri-Vault Storage rules (Obsidian, PySpark datasets, GitHub worktree).
- Audit is a binary veto — violation means failure, no exceptions.
- Never reuse a subagent after it has delivered its handoff.

## Current Parent
- Conversation ID: 23d306eb-b150-4e1b-8954-8e4866f3d375
- Updated: not yet

## Key Decisions Made
- Initiated 3-way survey across Frontend Airgap, Movesense DSP Suite, and SmolAgents Multi-Mode Arena.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|---|---|---|---|---|
| survey_1 | teamwork_preview_explorer | Survey R1: Frontend & Airgap | in-progress | 04d02729-148a-43f4-b770-6894d9472139 |
| survey_2 | teamwork_preview_explorer | Survey R2: Movesense Biometrics DSP | in-progress | df281b09-190a-4c18-bdfb-58a79986111a |
| survey_3 | teamwork_preview_explorer | Survey R3: SmolAgents & Multi-Mode Arena | in-progress | d9c679c9-bc2a-4871-bc23-5d218f0ebb46 |

## Succession Status
- Succession required: no
- Spawn count: 3 / 16
- Pending subagents: 04d02729-148a-43f4-b770-6894d9472139, df281b09-190a-4c18-bdfb-58a79986111a, d9c679c9-bc2a-4871-bc23-5d218f0ebb46
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: 63ce69b0-c347-4525-baf9-09dde968f198/task-11
- Safety timer: none
- On succession: kill all timers before spawning successor
- On context truncation: run `manage_task(Action="list")` — re-create if missing

## Artifact Index
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md — Verbatim user request
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_1/DISPATCH.md — Dispatch log
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_1/BRIEFING.md — Persistent working memory
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_1/progress.md — Liveness & checklist
