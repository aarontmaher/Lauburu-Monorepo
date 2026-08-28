---
name: ai-debate
description: Executes the Tri-Orchestrator Live Agent Debate Protocol (Cloud Orchestrator, Local AI Orchestrator, Genetic AI Orchestrator) to resolve architectural bottlenecks, co-optimize token efficiency, and inject top 5 verified priorities into the swarm.
---

# Tri-Orchestrator AI Debate Protocol

The AI Debate Protocol is an autonomous deliberative mechanism designed to resolve architectural uncertainties, deadlocks, and optimization challenges across the Lauburu ecosystem.

It introduces a 3-way deliberative consensus between:
1. **Cloud Orchestrator (Gemini 3.7 Flash):** Provides deep reasoning, step-by-step Chain-of-Thought (CoT) verification, and acts as a protective shadow guard over genetic mutations.
2. **Local AI Orchestrator (DeepSeek-R1 / Qwen3-VL on Mesh):** Advocates for zero-latency local execution, 10Gbps Thunderbolt RPC sharding, RAM ceilings, and local privacy.
3. **Genetic AI Orchestrator (Fitness & ELO Optimizer):** Studies live telemetry, optimizes cloud token expenditure, manages dynamic mutation rates, and drives the system toward the **$0 recurring cloud spend** milestone.

---

## 1. Trigger Conditions & Consensus Standard
 
 A debate automatically triggers when:
 *   **Operational / Decision Confidence < 100% (1.0):** Any uncertainty or missing verification triggers dynamic deliberation.
 *   **Consecutive Failures (>= 2):** A task or test fails twice in succession, preventing blind looping.
 *   **Consensus Convergence Requirement:** The debating AIs continue for as many rounds as necessary until **100% Unanimous Consensus (agreement_score = 1.0)** is mathematically and architecturally achieved across all 3 orchestrators.
 *   **Token & Spend Optimization Review:** Proactive analysis to minimize API calls and transition tasks to local edge models.

---

## 2. Tri-Orchestrator Deliberation Structure

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TRI-ORCHESTRATOR DEBATE                         │
│                                                                        │
│   [Turn 1] Cloud Orchestrator (Gemini 3.7 Flash - High Thinking)       │
│   • Architectural recommendations, standards, safety & shadow checks   │
│                               ↕                                        │
│   [Turn 2] Local AI Orchestrator (DeepSeek-R1-32B on Mesh)             │
│   • Local VRAM/Metal constraints, Thunderbolt RPC sharding, $0 spend   │
│                               ↕                                        │
│   [Turn 3] Genetic AI Orchestrator (Fitness Engine)                    │
│   • Token cost analysis, telemetry review, ELO adjustments, mutations  │
│                               ↕                                        │
│   [Turn 4] Lead Synthesis & Top 5 Priority Extraction                  │
│   • Synthesizes consensus into 5 checkable, non-destructive priorities │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Mutual Shadowing & Co-Optimization

*   **Genetic AI Studies Cloud Tokens:** Analyzes Gemini 3.7 Flash prompt/completion lengths and routes routine tasks (linting, JSON formatting, telemetry parsing) to Tier 3 fast low-token routes or local models.
*   **Cloud AI Shadows Genetic Mutations:** Evaluates proposed genetic genome mutations before application, preventing regressions, false correlations, or broken dependencies.
*   **Standardized Telemetry Export:** All orchestrators format telemetry streams (`data/live_debate_telemetry.json`) with structured schema tags for direct ingestion by the Genetic Evaluator.

---

## 4. Output & Priority Injection

Upon debate completion:
1. **Non-Destructive Priority Injection:** Injects the synthesized top 5 priority items directly into `progress.md` under `## Active Priorities (Injected by Live Debate)`.
2. **Worker Control:** Halts or redirects impacted worker agents in `workers/active.json`.
3. **LoRA Dataset Sync:** Automatically serializes the debate transcript as an `instruction/input/output` training pair to `lora_datasets/architectural_decisions.jsonl` and `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets/`.
