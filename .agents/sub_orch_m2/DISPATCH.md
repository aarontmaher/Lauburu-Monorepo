## 2026-08-24T10:01:09Z

# Task Assignment: Sub-Orchestrator / Lead Worker for Milestone 2 (Tri-Orchestrator AI Debate Engine)

## Context
You are the Sub-Orchestrator / Lead Worker for Milestone 2.
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m2
Workspace root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Parent Orchestrator: orchestrator_1 (d95629f0-67b4-4715-bb72-85614989a0a6)

## Mandatory Reading
1. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`.
2. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md`.
3. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_spec_miner_1/handoff.md`.
4. Read `/Users/aaron/.gemini/config/skills/ai-debate/SKILL.md`.

## Milestone Scope (M2: Tri-Orchestrator AI Debate Engine)
Implement and verify:
1. **4-Turn Deliberative State Machine**:
   - Cloud Orchestrator (Gemini 3.7 Pro/Flash, Claude 4.6 Opus/Sonnet): Opening Thesis & Architectural Safety Invariants.
   - Local AI Orchestrator (Kimi-Dev-72B, DeepSeek-R1-32B, Qwen 2.5 Coder): Counter-Thesis, $0 spend sovereignty, local hardware constraints.
   - Genetic AI Orchestrator (MoE Evolutionary Router): Fitness scoring, token efficiency, ELO calibration.
   - Consensus Accord Synthesis: Top 5 priority extraction ($\ge 90\%$ agreement required) and formal voting.
2. **Debate Focus Domains**:
   - UI/UX Development Optimization (120 FPS WebGPU shaders, 3D tatami world models, CoT reasoning diffs, dark mode layout).
   - Project AI Skill Necessities (identifying, ranking, and integrating competencies across all 26 monorepo applications and 12 domains).
3. **24/7 LoRA Training Dataset Sync**:
   - Instruction-thought-solution training pair serialization to `data/lora_datasets/truth_audit_debate.jsonl` (and Google Drive backup if available).
4. **Integration with Canonical ELO Ledger**:
   - Apply winning outcomes and efficiency multipliers directly to `data/canonical_ai_leaderboard.json` via `record_match_victory()`.
5. **Testing & Verification**:
   - Write/run `tests/test_debate_consensus.py` verifying all 4 turns, consensus extraction, LoRA JSONL serialization, and zero-mock compliance.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work.

When complete, write your handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/sub_orch_m2/handoff.md` and message parent (d95629f0-67b4-4715-bb72-85614989a0a6).
