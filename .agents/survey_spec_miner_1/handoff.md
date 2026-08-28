# Specification Extraction Report: Tri-Orchestrator AI Debate Protocol & Model Integration

**Agent**: `survey_spec_miner_1` (Specification Miner 1)  
**Date**: 2026-08-24T19:07:00Z  
**Target File**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_spec_miner_1/handoff.md`  
**Workspace Root**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`  
**Parent Orchestrator**: `orchestrator_1` (`d95629f0-67b4-4715-bb72-85614989a0a6`)

---

## 1. Observation

Authoritative specifications were extracted from the following verified sources in the monorepo and system skills:
- **Skill Definitions**:
  - `/Users/aaron/.gemini/config/skills/ai-debate/SKILL.md` (Tri-Orchestrator Live Agent Debate Protocol)
  - `/Users/aaron/.gemini/config/skills/project-ai-specialist-identifier/SKILL.md` (26 monorepo specialist skills across 12 domains)
  - `/Users/aaron/.gemini/config/skills/swarm/SKILL.md` (7-layer hardware mesh topology, RPC sharding, Swarm Truth Audit)
  - `/Users/aaron/.gemini/config/skills/spec-05-swarm-orchestrator/SKILL.md` (Swarm Governance & ELO Leaderboard)
- **Authoritative Scripts & Daemons**:
  - `06_scripts_and_tooling/scripts/ai_debate_engine.py` (4-turn deliberative consensus engine & JSONL/Markdown export)
  - `00_core_infrastructure/self_healing_hub/src/continuous_training_debate_daemon.py` (Continuous debate loop & 24/7 LoRA harvesting)
  - `00_core_infrastructure/self_healing_hub/src/self_healing_ai_debate.py` (Multi-transport incident recovery debates)
  - `00_core_infrastructure/self_healing_hub/src/tri_orchestrator_chat_service.py` (Live Multi-Beam & 4-round debate execution engine)
  - `00_core_infrastructure/self_healing_hub/src/game_to_project_elo_analyzer.py` (Bidirectional skill transfer & Project Contribution ELO formulas)
  - `00_core_infrastructure/self_healing_hub/src/bidirectional_elo_calibrator.py` (Mathematical calibration: $\eta_{size}$, $\eta_{compute}$, CPI, ELO divergence)
- **Canonical Telemetry & Data Ledgers**:
  - `04_data_and_memory/data/tri_orchestrator_debate_consensus.json` (Consensus state schema & RAM ceilings)
  - `04_data_and_memory/session_logs/ai_game_debate_improvements.json` (Top 5 suggested improvements schema & LCT economy)
  - `04_data_and_memory/data/live_debate_history.json` (Multi-round debate transcript records)
  - `04_data_and_memory/data/ai_elo_leaderboard.json` (Canonical JSON ELO ledger)
  - `00_core_infrastructure/self_healing_hub/frontend/src/TriOrchestratorLiveChatView.jsx` (React UI/UX component for live debate rendering)
  - `00_core_infrastructure/self_healing_hub/frontend/src/ConsensusSpecialistSkillsDashboard.jsx` (Specialist skills & WebGPU dashboard)

---

## 2. Logic Chain

1. **Tri-Orchestrator Role Specialization**:
   - The protocol divides governance among three distinct archetypes:
     * **Cloud Orchestrator (Gemini 3.7 Flash/Pro, Claude 4.6 Opus/Sonnet)**: High-level architectural reasoning, long-context safety invariants, and shadow review over code mutations (`ai-debate/SKILL.md:11`).
     * **Local AI Orchestrator (DeepSeek-R1-32B/70B, Qwen 2.5 Coder 32B, Kimi-Dev-72B, Kimi-VL-A3B)**: Low-latency execution (<0.28ms RTT), 10Gbps Thunderbolt 4 RPC tensor sharding, local privacy, and $0 token cost execution (`ai-debate/SKILL.md:12`).
     * **Genetic AI Orchestrator (Genetic MoE SLM / Fitness Engine)**: Evaluates empirical fitness scores, optimizes cloud token expenditure, dynamically calibrates ELO, and guides model weights toward $0 recurring spend (`ai-debate/SKILL.md:13`).

2. **Debate Trigger Conditions**:
   - Debates trigger on: (a) Architectural Uncertainty (multiple valid pathways with differing hardware/cost trade-offs), (b) Consecutive Failures ($\ge 2$ test/task failures), (c) Low Confidence ($< 0.70$ router confidence), or (d) Proactive Token/Spend Optimization Reviews (`ai-debate/SKILL.md:19-24`).

3. **4-Round Deliberation State Machine**:
   - **Round 1 (Opening Theses & Principles)**: Each model presents its uncompromised stance (Cloud focuses on structural safety; Local focuses on $0 spend and hardware VRAM bounds; Genetic focuses on fitness and token economics). Alignment begins at ~45–50% (`tri_orchestrator_chat_service.py:439-454`).
   - **Round 2 (Cross-Examination & Trade-Off Critiques)**: Direct cross-examination identifying edge-case vulnerabilities, thermal ceilings, API latency overheads, and code regression hazards. Alignment converges to ~70–75% (`tri_orchestrator_chat_service.py:458-473`).
   - **Round 3 (Technical Concessions & Synthesis)**: Explicit compromises (e.g., Cloud concedes routine 128Hz telemetry to local mesh; Local concedes multi-file architectural refactors to cloud shadow audits). Alignment reaches ~92–95% (`tri_orchestrator_chat_service.py:477-489`).
   - **Round 4 (Consensus Accord Ratification & Formal Voting)**: Formal unanimous voting with structured rationale. Alignment exceeds 98% (`tri_orchestrator_chat_service.py:493-498`).

4. **Debate Topics & Focus Domains**:
   - **UI/UX Development Optimization**: 3D WebGL / WebGPU 120 FPS rendering, kinematic tension shaders for grappling transitions, side-by-side AST / CoT reasoning diff viewers, multi-frame visual audit gates (OpenClaw 5-frame sequence), responsive dark-mode layouts, and decluttered HUD cards (`ai_game_debate_improvements.json:280-327`).
   - **Project AI Skill Necessities**: Identifying, ranking, and integrating competencies for all 26 monorepo applications across 12 domains (`DOM_01` Biometrics to `DOM_12` Continuous Self-Improvement), sharding GGUFs over the 82.8 GB VRAM mesh (`project-ai-specialist-identifier/SKILL.md:12-25`).

5. **Quantitative Scoring & ELO Mechanics**:
   - Multi-factor metrics quantify token efficiency ($\eta_{token}$), parameter efficiency ($\eta_{size}$), compute latency ($\eta_{compute}$), and composite project transfer fitness ($\mathcal{F}_{transfer}$).
   - In-game combat victories translate into real Project Contribution ELO via:
     $$\text{Project ELO} = \text{round}((\text{Game ELO} \times 0.60) + (\mathcal{F}_{transfer} \times 12.0))$$
   - If in-game ELO diverges from real project benchmark capability by $>120$ points, the bidirectional calibrator smoothly pulls in-game ELO back to ground truth (`bidirectional_elo_calibrator.py:159-163`).

6. **Output Schemas & Artifacts**:
   - Debate results serialize to canonical JSON files (`tri_orchestrator_debate_consensus.json`, `ai_game_debate_improvements.json`), markdown executive summaries (`debate_conclusions_ledger.md`), instruction-thought-solution training pairs in JSONL (`truth_audit_debate.jsonl`), and progress injections in `progress.md` (`ai-debate/SKILL.md:59-63`).

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Debate Protocol | 4-Round Tri-Orchestrator Deliberation | Structured debate sequence: Opening Thesis -> Cross-Examination -> Concession -> Consensus Accord | Debate Topic, Context, Telemetry Snapshot | Multi-turn transcript, Alignment %, Formal Votes | Fallback to heuristic consensus if model times out | `ai-debate/SKILL.md:27`, `tri_orchestrator_chat_service.py:426` |
| 2 | Model Integration | Cloud Orchestrator Interface | Integrates Gemini 3.7 Pro/Flash and Claude 4.6 Opus/Sonnet for high-reasoning shadow audits | High-level architecture, mutation diffs, task specs | CoT verification, safety score, invariant assertions | Deterministic offline heuristic scoring fallback | `api_server.py:1144`, `ai_debate_engine.py:53` |
| 3 | Model Integration | Local AI Mesh Orchestrator | Integrates DeepSeek-R1-32B/70B, Qwen 2.5 Coder 32B, Kimi-Dev-72B over 10Gbps TB4 RPC (:50052) | AST code diffs, telemetry streams, prompt buffers | Refactored AST, sub-20ms code solutions, $0 spend | Offload layer shards to next available mesh node | `project-ai-specialist-identifier/SKILL.md:47`, `swarm/SKILL.md:108` |
| 4 | Model Integration | Moonshot Kimi Tandem Integration | Integrates Kimi-VL-A3B Thinking & Kimi-Dev-72B for deep multimodal context and coding | Multimodal frames, large token context | Long-horizon reasoning traces, AST transforms | Graceful fallback to Qwen 2.5 Coder / DeepSeek-R1 | `canonical_ai_leaderboard.py:817,930`, `game_arena_manager.py:332` |
| 5 | Debate Topics | UI/UX & WebGL/WebGPU Optimization | Focuses debate on 120 FPS WebGPU shaders, 3D kinematic tension nets, and CoT diff viewers | Component paths, FPS benchmarks, WebGL errors | Top 5 UI/UX optimizations, target component patches | Rejection of unverified static mocks | `ai_game_debate_improvements.json:280`, `ConsensusSpecialistSkillsDashboard.jsx:131` |
| 6 | Debate Topics | Project AI Skill Necessities Audit | Audits 26 monorepo project AI skills across 12 domains to determine local model sharding | Application dependency manifests, AST AST callgraphs | Priority skill inventory, GGUF recommendations | Ingests fallback SLM if flagship GGUF unavailable | `project-ai-specialist-identifier/SKILL.md:12`, `05_agents_and_swarms/README.md:19` |
| 7 | Scoring & ELO | Token Efficiency Metric ($\eta_{token}$) | Quantifies token output quality vs cost to guide routing toward $0 recurring spend | Token counts, completion quality, API rate card | Efficiency multiplier, cost per verified task ($) | Flags inefficient verbose models for local routing | `ai-debate/SKILL.md:51`, `bidirectional_elo_calibrator.py:75` |
| 8 | Scoring & ELO | Parameter & Compute Efficiency ($\eta_{size}, \eta_{compute}$) | Rewards small agile models (135M-3B) for sub-ms execution and penalizes heavy models with high RTT | Model parameter count ($B$), socket RTT (ms), VRAM (GB) | $\eta_{size}$, $\eta_{compute}$ multipliers | Caps minimum multiplier at 0.2/0.5 | `bidirectional_elo_calibrator.py:75-81` |
| 9 | Scoring & ELO | Composite Project Transfer Fitness ($\mathcal{F}_{transfer}$) | Combines AST precision (30%), Network mastery (25%), VRAM quantization (20%), Truth (15%), Ghost daemons (10%) | In-game action stats, audit pass rates, AST accuracy | 0–100 composite fitness score, Project ELO | Clamps scores to [0.0, 100.0] bounds | `game_to_project_elo_analyzer.py:38-80` |
| 10 | Scoring & ELO | Bidirectional ELO Calibration Ledger | Synchronizes in-game ELO with real-world monorepo task dispatching and penalizes divergence ($>120$) | In-game ELO, real project task benchmark scores | Calibrated ELO matrix, game difficulty tuning | Auto-adjusts token reward multipliers if drift detected | `bidirectional_elo_calibrator.py:129`, `ai_elo_leaderboard.json:1` |
| 11 | Consensus | Formal Unanimous Accord Voting | Gathers explicit votes from all 3 orchestrators with required alignment threshold $\ge 90\%$ | 3-way turn conclusions, concession statements | Quorum status, alignment percentage, voting ledger | Halts priority injection if alignment $< 90\%$ | `tri_orchestrator_chat_service.py:493`, `live_debate_history.json:82` |
| 12 | Output Schemas | Top 5 Priority Injection | Formats synthesized conclusions into 5 checkable, non-destructive items for `progress.md` | Ratified consensus accord, actionable remediations | Appended markdown block in `progress.md` | Skips duplicate priority injections | `ai-debate/SKILL.md:60`, `ai_game_debate_improvements.json:329` |
| 13 | Output Schemas | 24/7 LoRA Training Dataset Sync | Serializes debate transcripts as instruction-thought-solution JSONL records to local NVMe and Google Drive | Debate turns, consensus conclusion, telemetry | `truth_audit_debate.jsonl` entries | Local NVMe fallback if Google Drive unmounted | `ai_debate_engine.py:105`, `continuous_training_debate_daemon.py:99` |
| 14 | Integration | REST Chat & Debate API Endpoints | Serves `/api/chat/messages`, `/api/chat/send`, `/api/chat/multi_beam`, `/api/chat/debate_accord` on Port 5001/3000 | HTTP JSON payloads (prompt, mode, topic, action) | Response messages, multi-beam cards, debate accords | Returns HTTP 400/500 with JSON error details | `api_server.py:1134-1218`, `TriOrchestratorLiveChatView.jsx:30` |
| 15 | Integration | 1-Click Action Dispatcher | Triggers live monorepo actions from debate accord cards (/audit, /duel, /slice, /obsidian, /adb) | Action identifier string, payload dictionary | Execution status, output logs, UI toast alerts | Safe error reporting without process crash | `tri_orchestrator_chat_service.py:1035`, `TriOrchestratorLiveChatView.jsx:30` |
| 16 | Verification | Zero-Mock Truth Audit Gate | Enforces 100% live hardware data verification and zero simulated data across all debate telemetry | Live GATT/statvfs/socket streams, UI frames | Truth pass certification, MD5 unique frame assertions | Immediate task failure and retraining loop if mock detected | `swarm/SKILL.md:240`, `ORIGINAL_REQUEST.md:17` |

---

## 4. Edge Cases

| # | Feature | Input / Condition | Observed & Documented Specification Behavior |
|---|---------|-------------------|-----------------------------------------------|
| 1 | Debate Trigger | Offline WAN / Cloud API Key Missing | System gracefully switches Cloud Orchestrator to deterministic high-order heuristic evaluation or escalates to local 70B IQ4_XS model over TB4 RPC without crashing. |
| 2 | Debate Deliberation | Deadlock / Dissenting Opinion (Alignment $< 90\%$) | Protocol executes an extra concession round (Round 3.5) with PySpark empirical telemetry arbitration; if still $< 90\%$, flags topic as `ARCHITECTURAL_DEADLOCK` and defers priority injection to operator. |
| 3 | Model RPC Sharding | Mobile Node (Pixel 10 / S20+) Thermal Throttling ($>41^\circ\text{C}$) or Battery $<20\%$ | Genetic Router immediately triggers `active_offload_directive`, evacuating active layer splits to Linux Head Node (Ryzen 7) or MacBook Pro (Layer 2) over 10Gbps TB4 bridge. |
| 4 | ELO Calibration | Extreme In-Game Exploits (In-Game ELO surges $+500$ without Real AST Commits) | `BidirectionalEloCalibrator` detects divergence $>120$ ELO, flags model as `OVERVALUED`, and applies a $-35\%$ correction damping factor while reducing game token multipliers. |
| 5 | Storage & Memory | NVMe Headroom Drops Below 10 GB ($<15\%$ Free Space) | Survival-of-the-Fittest storage daemon automatically prunes unindexed GGUF checkpoints with $<1800$ ELO while strictly protecting $\ge 1800$ ELO flagship models and symlinking weights to NAS. |
| 6 | LoRA Serialization | Google Drive Cloud Path Unmounted (`/Volumes/Google Drive` Unreachable) | Daemon catches exception, logs warning, and writes training pairs exclusively to high-speed NVMe fallback at `data/lora_datasets/truth_audit_debate.jsonl`. |
| 7 | AST Context Slicing | Unrecognized or Empty Symbol Query | Slicer defaults to top-level architecture anchors (`TieredMultiModelRouter`, `TriOrchestratorChatService`) and limits context slice to $\le 8,192$ tokens to prevent KV-cache blowup. |
| 8 | Multi-Beam Concurrency | Simultaneous Request to 4 Models with Socket Contention on Port 50052 | `TriOrchestratorChatService` sequences RPC evaluations with non-blocking threads, maintaining sub-30ms total response time across local and cloud pipelines. |

---

## 5. Formal Data Structures & Schema Specifications

### 5.1 Canonical Consensus Accord Schema (`tri_orchestrator_debate_consensus.json`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TriOrchestratorDebateConsensus",
  "type": "object",
  "required": [
    "timestamp",
    "topic",
    "consensus_status",
    "consensus_confidence",
    "key_findings",
    "node_specific_ceilings"
  ],
  "properties": {
    "timestamp": { "type": "string" },
    "topic": { "type": "string" },
    "consensus_status": { "type": "string" },
    "consensus_confidence": { "type": "number", "minimum": 0.0, "maximum": 100.0 },
    "key_findings": {
      "type": "object",
      "properties": {
        "recommended_policy": { "type": "string" },
        "mesh_pooled_vram_gb": { "type": "number" }
      }
    },
    "node_specific_ceilings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["layer", "node", "total_ram", "safe_ceiling_pct", "usable_vram_gb", "rationale"],
        "properties": {
          "layer": { "type": "integer" },
          "node": { "type": "string" },
          "total_ram": { "type": "number" },
          "safe_ceiling_pct": { "type": "number" },
          "usable_vram_gb": { "type": "number" },
          "rationale": { "type": "string" }
        }
      }
    }
  }
}
```

### 5.2 24/7 LoRA Training Record Schema (`truth_audit_debate.jsonl`)
```json
{
  "instruction": "Perform Tri-Orchestrator AI Debate on project topic: '<TOPIC>'",
  "input": "{\"debate_id\": \"DEBATE_LORA_...\", \"topic\": \"...\", \"context\": \"...\", \"perspectives\": {\"gemini_37_flash\": \"...\", \"local_ai_mesh\": \"...\", \"genetic_moe\": \"...\"}}",
  "thought": "[Turn 1] Cloud Orchestrator analyzed architectural invariants... [Turn 2] Local AI Mesh evaluated hardware... [Turn 3] Genetic MoE evaluated token economy... [Turn 4] Lead Synthesis established consensus...",
  "output": "Consensus Reached: <RATIFIED_ACCORD> (Tri-Orchestrator Certified, 0 Fake Data, 0 Hallucinations).",
  "timestamp": "2026-08-24T19:07:00Z"
}
```

### 5.3 ELO Transfer & Mapping Schema (`game_to_project_elo_map.json`)
```json
{
  "timestamp": "2026-08-24T19:07:00Z",
  "total_agents_evaluated": 11,
  "average_game_elo": 1845,
  "average_project_elo": 1890,
  "reinforcement_validity": "100% Empirically Validated",
  "agents_transfer_roster": [
    {
      "agent_id": "agent_deepseek_r1",
      "name": "DeepSeek-R1 Distill Qwen 32B",
      "hardware_node": "Layer 3: Linux Head Node",
      "model_spec": "32B (Q4_K_M)",
      "game_elo": 1920,
      "project_contribution_elo": 1965,
      "transfer_efficiency_pct": 98.4,
      "core_winning_factor": "Deep AST Reasoning & Multi-Layer Sharding",
      "real_project_learning": "Learned distributed layer sharding over 10Gbps TB4 bridge",
      "verified_skills_transferred": [
        "DOM_07_CPP_SYSTEMS_LLAMA_OPTIMIZATION",
        "DOM_09_AI_GAME_ARENA_REASONING"
      ]
    }
  ]
}
```

---

## 6. Caveats

- **Scope Boundary**: As a specification mining agent, no production code modifications were made.
- **Hardware Prerequisites**: Live RPC execution on port `50052` requires the multi-device mesh (`127.0.0.1`, `169.254.187.138`, `100.101.39.98`) or in-process mock-free fallback daemons.
- **API Keys**: Live frontier evaluations for Claude 4.6 and Gemini 3.7 connect via environment keys (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`), with verified offline deterministic heuristic fallbacks when keys are absent.

---

## 7. Conclusion

The authoritative specifications for the Tri-Orchestrator AI Debate Protocol and Model Integration have been extracted, synthesized, and verified across all codebase assets. The architecture provides:
1. A **4-round deliberative protocol** balancing Cloud Safety (Gemini 3.7 / Claude 4.6), Local $0 Spend Sovereignty (DeepSeek-R1 / Qwen 2.5 / Moonshot Kimi), and Genetic Evolutionary Fitness.
2. Grounded debate topics targeting **120 FPS WebGPU / 3D UI/UX excellence** and **26 project AI specialist skills**.
3. Mathematical **bidirectional ELO calibration** tying in-game victories directly to monorepo task dispatching.
4. Continuous **24/7 LoRA dataset distillation** to local NVMe and Google Drive, advancing the $0 recurring cloud spend milestone.

---

## 8. Verification Method

To independently verify all extracted specifications and execute the debate engine:

1. **Verify Python Debate Engine & JSONL Generation**:
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/scripts/ai_debate_engine.py "WebGPU 120 FPS UI/UX Optimization" "UI_Development"
   ```
2. **Verify Continuous Training Debate Daemon**:
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/continuous_training_debate_daemon.py
   ```
3. **Verify Bidirectional ELO Calibration & Transfer**:
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/bidirectional_elo_calibrator.py
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/game_to_project_elo_analyzer.py
   ```
4. **Verify Live Chat & Consensus Service**:
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/tri_orchestrator_chat_service.py
   ```
5. **Inspect Generated Ledgers**:
   - `04_data_and_memory/data/tri_orchestrator_debate_consensus.json`
   - `04_data_and_memory/session_logs/debate_conclusions_ledger.md`
   - `data/lora_datasets/truth_audit_debate.jsonl`
