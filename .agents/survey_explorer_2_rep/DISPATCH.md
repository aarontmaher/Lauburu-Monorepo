# Task Assignment: Survey Explorer 2 Replacement (ELO Governance, Task Dispatch & Truth Audit)

## Context
You are Survey Explorer 2, an autonomous exploration agent.
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_2_rep
Workspace root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Parent Orchestrator: orchestrator_1 (d95629f0-67b4-4715-bb72-85614989a0a6)

## Mandatory Reading
1. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`.
2. Read `05_agents_and_swarms/` or ELO/leaderboard references in the monorepo, as well as testing tools and truth audit standards.

## Mission & Objectives
Investigate and design:
1. **Canonical JSON ELO Ledger**: Schema, state persistence, initial ratings, K-factor calculation based on debate outcomes (win/loss/draw, token efficiency bonus, consensus agreement), historical match logging.
2. **Success Mapping & Task Dispatch Engine**: Mechanism by which the highest-ELO model in the canonical ledger is dynamically selected and routed to execute actual monorepo tasks (e.g. optimizing a specific component, generating a required specialist skill, refactoring code).
3. **Automated Verification Harness & Routing Verifier**: Design the test suite that executes the debate loop, validates JSON ledger mutations, and runs the script verifying that orchestrator routes actual project tasks to the top-ELO model.
4. **Zero-Mock & Swarm Truth Audit Protocol (Rule #0)**: Mechanisms to ensure 100% genuine data flow (no fake arrays, no hardcoded strings, genuine API/model responses or genuine deterministic model runners), and how the Swarm Truth Audit (Vision AI / Playwright / Chrome DevTools) validates the live UI.

## Output Requirements
Write your comprehensive report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_2_rep/handoff.md`.
Include:
- ELO Ledger specification and formula calculations.
- Dispatch router architecture and integration points.
- Test suite structure (unit, integration, E2E).
- Truth audit and zero-mock verification checklist.
Notify orchestrator_1 with a brief completion message when finished.
