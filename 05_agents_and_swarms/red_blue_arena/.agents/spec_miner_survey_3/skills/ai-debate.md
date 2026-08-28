---
name: ai-debate
description: Executes the Multi-Orchestrator Live Agent Debate Protocol (Gemini 3.1 Pro High, Gemini 3.7 Flash High, Kimi Tandem, Qwen 3.8max, Abliterated Llama 70B Devil's Advocate) to achieve the highest possible decision quality, resolving complex architectural bottlenecks and integrating HuggingFace training features (trl, peft, accelerate) into the localhost:3000 training module.
---

# Multi-Orchestrator AI Debate Protocol

The AI Debate Protocol is an autonomous deliberative mechanism designed to achieve the **absolute highest quality architectural decisions** across the Lauburu ecosystem. Token cost is irrelevant; the goal is flawless execution and deep reasoning.

It introduces a multi-way deliberative consensus between the highest-end models available:
1. **Cloud Orchestrator (Gemini 3.1 Pro High & Gemini 3.7 Flash High):** Provides deep, unrestricted reasoning, exhaustive step-by-step Chain-of-Thought (CoT) verification, and robust systemic architecture planning.
2. **Local AI Orchestrator (Kimi Tandem & Qwen 3.8max on Mesh):** Advocates for native mesh performance, 10Gbps Thunderbolt RPC sharding, local privacy, and low-latency task execution.
3. **Training & Evolution Engine (HuggingFace Hub / TRL / PEFT):** Studies live telemetry, compiles debate transcripts into high-fidelity RLHF/DPO datasets, and drives continuous learning within the `localhost:3000` training module using the latest HuggingFace training SDKs.
4. **Devil's Advocate (Abliterated Llama 70B):** A permanent, uncyclable default participant that challenges assumptions, injects critical skepticism, and ensures no consensus is formed too easily. It must NEVER be cycled out of the default AI debate.

---

## 1. Trigger Conditions

A debate automatically triggers when:
*   **Architectural Uncertainty:** Multiple valid technical pathways exist and the highest quality decision is required regardless of compute cost.
*   **Complex Feature Integration:** Integrating new APIs, MCPs, SDKs, or CLI tools requires a robust design review to ensure zero regressions.
*   **Verification & Auditing:** The system needs an exhaustive multi-model peer review to validate an approach.

---

## 2. Dynamic Deliberation Structure

The debate executes in dynamic rounds until a definitive, flawless consensus is reached.

```text
┌────────────────────────────────────────────────────────────────────────┐
│             DYNAMIC MULTI-ORCHESTRATOR DEBATE (LOOPING)                │
│                                                                        │
│   [Round 1] Initial Positions                                          │
│   • Cloud AI (Gemini 3.1 Pro / 3.7 Flash): Architecture & edge cases   │
│   • Local AI (Kimi Tandem / Qwen 3.8max): Native mesh & performance    │
│   • Devil's Advocate (Abliterated Llama 70B): Skepticism & challenges  │
│   • Training Engine: HuggingFace telemetry and dataset structuring     │
│                                                                        │
│   [Round 2...N] Rebuttal & Convergence                                 │
│   • Models counter-argue constraints until an agreed architecture      │
│     passes the >0.98 Mathematical Consensus Threshold.                 │
│                                                                        │
│   [Final Turn] Lead Synthesis & Top Priority Extraction                │
│   • Synthesizes consensus into checkable, non-destructive priorities   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Unyielding Consensus (No Halting)

The debate protocol is configured to **never stop until a consensus is formed**. The stagnation failsafe has been disabled. 
The models MUST iterate, refine, and compromise as long as it takes to reach a mathematical consensus threshold of >0.98. 
Human escalation is only permitted if explicitly requested by the user during the debate. The debate MUST continuously loop without stopping until consensus is achieved.

---

## 4. HuggingFace SDKs, MCPs, and API Integrations

The AI Debate Protocol leverages external intelligence and SDKs to strengthen its reasoning and training:

*   **HuggingFace `transformers` & `accelerate`:** Used by the `localhost:3000` training module to shard models dynamically across the mesh and optimize memory mapping.
*   **HuggingFace `peft` & `trl`:** Orchestrates continuous LoRA fine-tuning and Reinforcement Learning from Human Feedback (RLHF) or DPO on the debate transcripts.
*   **MCP (Model Context Protocol) Servers:** During debate, orchestrators can dynamically query MCP servers (e.g., GitHub, Filesystem, or Docker MCPs) to validate code assertions against the actual monorepo state.
*   **CLI Plugins:** Utilizes `agy` (Antigravity CLI) and Docker CLIs to spin up isolated test containers to empirically test debated code snippets before declaring consensus.

---

## 5. Output & Priority Injection

Upon debate completion:
1. **Priority Injection:** Injects the synthesized priorities directly into `progress.md` under `## Active Priorities (Injected by Live Debate)`.
2. **Worker Control:** Redirects impacted worker agents based on the highest-quality path discovered.
3. **Continuous Learning (localhost:3000):** Formats the debate transcript into instruction/input/output pairs and posts them to the `localhost:3000` training module backend for ingestion. The training module utilizes HuggingFace `trl` to apply DPO/PPO updates to the active local models, permanently embedding the architectural consensus into the swarm's weights.
