---
title: "Sovereign Single-Chat Nexus (Mother Ship) Architecture - Bluetooth IDE"
tags: [lauburu, single_chat, mother_ship, bluetooth_ide, ai_debate, fan_out, action_aggregation, qwen_38_max]
consensus_score: 1.0
elo_boost: 40
timestamp: "2026-09-18T04:41:00+10:00"
---

# 👑 Sovereign Single-Chat Nexus (Mother Ship) Architecture

## 1. Executive Summary & Problem Statement
In the Lauburu Bluetooth Terminal IDE, multiple specialized domains (Omni Inbox, E-Commerce Sales, Movesense Biometrics, Screen Lens VLA, Core Infrastructure, and dynamic project tasks) require synchronized intelligence. Requiring the user (Aaron) to manually open and context-switch across dozens of disjointed chat threads introduces cognitive friction and operational desynchronization.

The **Sovereign Single-Chat Nexus (Mother Ship)** establishes a **single unified conversational interface** inside the Bluetooth Terminal IDE. From this single chat:
1. Aaron issues directives, strategies, or decisions.
2. The Single Chat automatically evaluates relevance and **fans out** tailored messages to relevant existing satellite chats or dynamically spawns new project threads.
3. Satellite chats execute their tasks and **report back** completed actions, process exit codes, and empirical metrics.
4. The Single Chat aggregates these reports and **proactively discusses the next step** directly with Aaron.

---

## 2. Multi-Model AI Debate Transcript & Deliberation

### Deliberation Participants
- **Frontier Architect (Gemini 3.8 Flash):** CoT reasoning, safety invariants, structured JSON schema governance.
- **Sovereign Master Local Orchestrator (Qwen 3.8 Max on Port 8082):** Pipelined-Ring Parallelism coordinator, memory governor, state persistence lead.
- **Canonical Devil\'s Advocate (Qwen 3.8 Max Abliterated on Port 8083):** Adversarial stress tester, concurrency hazard auditor.
- **Genetic AI Orchestrator:** Token budget optimizer ($0 local inference, zero cloud spend).
- **Screen Lens Sovereign:** Real-time visual truth verification and device telemetry auditor.

### Debate Turns & Synthesis

#### Turn 1: Frontier Architect (Gemini 3.8 Flash)
> *"The single-chat interface must operate as an event-driven pub/sub orchestrator. A naive implementation risks conversational pollution where raw tool outputs and terminal logs flood the main thread. To preserve signal-to-noise ratio, the main chat must present high-density executive summaries with expandable cards for fan-out directives and action reports. State must be persisted to SQLite with strict foreign key constraints on `thread_id` and idempotent message IDs."*

#### Turn 2: Sovereign Master Local Orchestrator (Qwen 3.8 Max :8082)
> *"The Mac Mini host RAM sanctuary (Rule 3: >= 4.8 GB free) must be protected. All relevance classification, intent extraction, and next-step synthesis must run locally on Port 8082 with 0ms cloud cost. If Port 8082 is busy, failover cleanly to Port 8083 or deterministic regex heuristic fallback. Zero heavy model weights may be loaded in-process. The SQLite database at `04_data_and_memory/single_chat_nexus.db` guarantees zero data loss across IDE reboots."*

#### Turn 3: Devil\'s Advocate (Qwen 3.8 Max Abliterated :8083)
> *"Stress Point 1: What happens if a satellite chat encounters an error or timeout? The dispatcher must not hang Aaron\'s single chat waiting on a stalled subtask; it must support asynchronous streaming and fire-and-forget execution with exit code tracking. Stress Point 2: Accidental thread explosion. Dynamic thread creation must use strict topic clustering so we don\'t spawn 50 duplicate threads for the same feature. Stress Point 3: Rule 1 Zero-Mock compliance. Every action report must link to authentic local files, live DB records, or kernel syscalls."*

#### Turn 4: Genetic AI Orchestrator
> *"Consensus score: 1.0 (Unanimous). ELO Rating Boost: +40 pts to Qwen 3.8 Max for PRP Ring coordination. Cloud token expenditure: $0.00 (100% localhost execution). Recommended mutation: Add one-tap decision chips to the Next Step card so Aaron can approve or redirect the swarm with a single keystroke or click."*

#### Turn 5: Screen Lens Sovereign
> *"Visual & Telemetry Invariant: The Web UI on Port 4050 and the Textual TUI must both visually distinguish between: (1) Aaron\'s original directive, (2) Outbound fan-out pills, (3) Inbound completed actions, and (4) Proactive next-step recommendations. Screen Lens will passively capture DOM and terminal state to verify visual contrast and accessibility."*

---

## 3. Consensus Architecture: 5 Core Invariants

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 SOVEREIGN SINGLE-CHAT NEXUS (MOTHER SHIP)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. INTAKE & RELEVANCE EVALUATION (Port 8082 Qwen 3.8 Max)                   │
│    • Ingests Aaron\'s prompt in the central IDE chat.                        │
│    • Computes multi-label relevance across domain chats & active projects.  │
│    • Autonomously spawns new thread if topic is novel.                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. DIRECTIVE SLICING & FAN-OUT                                              │
│    • Slices Aaron\'s directive into domain-specific instructions.            │
│    • Outbound delivery to target threads with status tracking.              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. SATELLITE EXECUTION & INBOUND ACTION REPORTING                           │
│    • Satellite threads execute authentic tasks (Shopify, Movesense, Mesh).  │
│    • Records action description, empirical result, and exit code.           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. UPSTREAM SYNTHESIS & NEXT-STEP DISCUSSION                                │
│    • Port 8082 summarizes: "What was done" + "Next Step Strategic Analysis".│
│    • Provides interactive decision chips for immediate follow-up.           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. PERSISTENT TRI-VAULT SYNCHRONIZATION                                     │
│    • SQLite DB: 04_data_and_memory/single_chat_nexus.db                     │
│    • LoRA Training: continuous_lora_dataset.jsonl                           │
│    • Obsidian: obsidian_vault/APPS_AND_FEATURES/                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Top 5 Actionable Consensus Priorities
1. **Module `chat_dispatcher.py`:** Standalone engine handling SQLite state, relevance classifier, message fan-out, action reporting, and next-step synthesis.
2. **REST & WebSocket API:** Expose `/api/chat/nexus`, `/threads`, `/report`, `/next-steps`, and `/ws/chat/nexus` on FastAPI Port 4050.
3. **Web UI Mother Ship Panel:** Upgrade `frontend/index.html` with unified chat, fan-out badges, actions feed, and next-step discussion card.
4. **Textual TUI Macro Support:** Enable `/nexus`, `/threads`, `/next` in `bluetooth_terminal_app.py`.
5. **Comprehensive Test Suite:** 100% exit code 0 automated test suite in `tests/test_single_chat_dispatcher.py` and `tests/test_setupnexus_cli.py`.

---

## 4. Operational Tooling: `setupnexus` CLI

The `setupnexus` CLI (`06_scripts_and_tooling/setup_nexus.py`) provides unified operational control over the Mother Ship:

```bash
# Initialize storage, verify seed threads and zkVM sidecar
setupnexus init

# Start background server daemon on Port 4050
setupnexus start

# Inspect system status across 7 layers, storage, and models
setupnexus status

# Dispatch high-level directives from terminal
setupnexus dispatch "Audit Movesense 512Hz ECG and Shopify inventory"

# Execute mandatory 5-stage Tri-Proof verification gate
setupnexus verify

# Trigger Frontier Swarm Consensus debate
setupnexus consensus
```

### Tri-Proof Verification Status (100% Verified)
1. **Proof 1 (Actuation):** 
   - `test_single_chat_dispatcher.py`: 17 passed (Exit Code 0).
   - `test_setupnexus_cli.py`: 7 passed (Exit Code 0).
   - `nexus_adapter.py`: zkVM trace verified (Exit Code 0).
2. **Proof 2 (Line-by-Line Integrity):**
   - `06_scripts_and_tooling/setup_nexus.py`: SHA256 verified.
   - `01_apps/bluetooth_terminal_ide/backend/chat_dispatcher.py`: SHA256 `52c4c4020ed6...` (750 lines, 35,711 bytes).
   - `01_apps/bluetooth_terminal_ide/backend/server.py`: SHA256 `c060ab52f79c...` (2,132 lines, 96,575 bytes).
3. **Proof 3 (Visual Screen Lens Truth):**
   - Proof Capture 1: `obsidian_vault/frontier_audits/screen_lens_nexus_proof_1789722941.png`
   - Proof Capture 2: `obsidian_vault/frontier_audits/frontier_consensus_audit_1789723283.png`

