---
title: "AI Debate Consensus: Integration of Neo Autonomous ML Engineer into Antigravity IDE"
date: 2026-09-04
participants:
  - Local AI Orchestrator (Qwen 3.8 Max / Prima.cpp)
  - Cloud Shadow Orchestrator (Gemini 3.1 Pro / 3.7 Flash)
  - Devil's Advocate (Abliterated Qwen 3.8 Max - Port 8083)
  - Training & Evolution Engine (PySpark / HuggingFace TRL)
consensus_threshold: 0.985
status: RESOLVED
---

# 🏛️ Tri-Orchestrator AI Debate: Neo Extension & MCP Integration

## 📋 Context & Proposal
**Question:** *"Should we integrate Neo (heyneo / neo-mcp) as an extension plugin into Antigravity IDE?"*

---

## 🎙️ Round 1: Divergent Positions

### 1. Cloud Shadow Orchestrator (Gemini 3.7 Flash High)
> **Position: Conditional Integration via MCP.**
> Neo is an autonomous ML engineer specializing in RAG architectures, hyperparameter tuning, and PyTorch pipeline generation. Antigravity IDE supports MCP natively. Rather than reinventing ML boilerplate scripts, Neo could act as an on-demand domain subagent for machine learning workflows.

### 2. Local AI Orchestrator (Qwen 3.8 Max / Prima.cpp)
> **Position: Memory & Cost Skepticism.**
> The Host Mac Mini M4 Pro must maintain $\ge 9.6\text{ GB}$ of free physical RAM. If Neo runs a heavy background language server or requires persistent memory, it endangers host stability. Furthermore, if Neo depends on commercial cloud tokens, it conflicts with our $0 local inference mandate.

### 3. Devil's Advocate (Abliterated Qwen 3.8 Max - Port 8083)
> **Position: Strongly Opposed to IDE Extension; Strict Veto on Black-Box Services.**
> Installing a proprietary extension into Antigravity IDE is an anti-pattern:
> 1. **Agent Collision:** It creates two conflicting autonomous brains (Antigravity vs Neo) fighting over file buffers, terminal processes, and `.git/index.lock`.
> 2. **Data Leakage:** Proprietary SaaS agents phone home telemetry and source code to remote servers.
> 3. **Redundancy:** We already built our own canonical MCP server (`screen_lens_mcp_server.py`), AST optimizer, and Bradley-Terry genetic tuning engine. Why surrender sovereign control to an external proprietary agent?

---

## 🔄 Round 2: Convergence & Rebuttals

- **Local AI Orchestrator:** *"I agree with the Devil's Advocate regarding the IDE extension. A VS Code / Antigravity UI extension is bloated and intrusive. However, could `neo-mcp` be used strictly as a sandboxed CLI tool?"*
- **Cloud Shadow Orchestrator:** *"Precisely. We decouple the tool from the interface. We reject the IDE extension, but preserve the option to query `neo-mcp` via the Model Context Protocol in a sandboxed container."*
- **Devil's Advocate:** *"Acceptable ONLY under strict conditions: (1) Zero external code exfiltration, (2) $0 cost verification, (3) Neo cannot touch production git worktrees without Antigravity's explicit Rule 0.1 Triple Truth Audit."*

---

## ⚖️ Final Consensus Verdict (>0.985 Agreement)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FINAL COUNCIL RESOLUTION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. REJECT THE IDE EXTENSION:                                                │
│    • Do NOT install the Neo VS Code / Antigravity extension.                 │
│    • Prevents UI bloat, shortcut collisions, telemetry leakage & git locks. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. ALLOW OPTIONAL MCP INTEGRATION (neo-mcp) IN RING 0 SANDBOX:              │
│    • If specific ML automation is needed, integrate `neo-mcp` via standard  │
│      Antigravity MCP config, isolated to ~/teamwork_projects/.              │
│    • Must run with zero cloud spend and zero proprietary telemetry leakage. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. SOVEREIGN ENGINE FIRST:                                                  │
│    • Prioritize our native `screen-lens-sovereign` and PySpark/MLX engine   │
│      for all primary model distillation and telemetry tasks.                │
└─────────────────────────────────────────────────────────────────────────────┘
```
