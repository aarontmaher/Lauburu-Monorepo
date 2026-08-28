# Inference Routing & Continuous AI Arena Architectural Survey

**Explorer Archetype**: `explorer_survey_1` (Role: Inference Router Explorer)  
**Workspace**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/`  
**Timestamp**: 2026-08-28T12:46:00+10:00  
**Target Milestone**: Survey & Inference Routing Analysis for Continuous AI Arena (R1-R3)

---

## 1. Executive Summary

This report delivers an exhaustive, empirical investigation of all inference routing, model endpoints, prompt ingestion pipelines, and ELO scoring infrastructure across the Lauburu Monorepo. 

The monorepo contains several distinct routing implementations:
1. **Canonical Port Agent Router** (`01_apps/canonical_port/backend/agents/cloud_ai_router.py` & `smolagents_ecosystem.py`): Routes user tasks between local llama.cpp/Exo models and free-tier cloud APIs (Cloudflare, Gemini Flash).
2. **8-Pillar Tiered Multi-Model Router** (`00_core_infrastructure/self_healing_hub/src/tiered_multi_model_router.py`): Routes tasks across 8 specialized execution engines with PySpark AST slicing (:8750) and >100k token macro failover to Gemini 3.1 Pro.
3. **Dynamic AGI Fallback Router** (`02_ai_models_and_inference/dynamic_agi_fallback_router.py`): Downshifts to node-specific survival models when mesh nodes drop, upshifting to Kimi 88B Tandem when full mesh is restored.
4. **Network-Aware Petals DHT Dijkstra Router** (`02_ai_models_and_inference/sharding_daemon/router.py`): DP shortest-path transformer block allocation with sub-100ms circuit breakers.
5. **Cloud API Quota Manager & Router** (`06_scripts_and_tooling/automation/cloud_api_quota_manager.py`): Heuristic scoring across Julien AI (300 RPD), Cloudflare (1000 RPD), Gemini Free (1500 RPD), and Local Mesh (Ports 8081-8084).

**Key Gap Identified**: In the current codebase, prompt ingestion is purely **single-model synchronous or single-model asynchronous**. When a user sends a prompt, one model is picked, executed, and returned. There is **no background challenger dispatching** occurring during standard user prompts. The Tri-Orchestrator debate engine (`ai_debate/src/tri_orchestrator_debate.py` and `00_core_infrastructure/self_healing_hub/src/tri_orchestrator_swarm_arena.py`) operates only in batch tournament/debate modes.

We provide a complete architectural blueprint for **Requirement R1 (Continuous Challenger Format)**: delivering the #1 Ranked Champion response synchronously to the user with zero latency overhead, while asynchronously dispatching the prompt to 2 Challenger models in the background, blindly grading outputs via the Tri-Orchestrator, updating ELO ratings, and dynamically promoting the highest-ELO model to the Champion spot.

---

## 2. Comprehensive Inventory of Inference Routing Code

| File Path | Primary Class / Functions | Routing Philosophy & Role |
| :--- | :--- | :--- |
| `01_apps/canonical_port/backend/agents/cloud_ai_router.py` (lines 1-159) | `CloudAIRouter`, `route_request()`, `generate_response()` | Tier hierarchy router: Local Llama.cpp (P1) → Local Exo (P2) → Cloudflare Free (P3) → Gemini Flash Free (P4, 300 req limit). |
| `01_apps/canonical_port/backend/agents/smolagents_ecosystem.py` (lines 235-306) | `SmolagentAgentWrapper`, `run_autonomous_cycle()` | Autonomous cycle coordinator: parses user task, queries `CloudAIRouter.route_request()`, executes matching specialist tool, returns result. |
| `01_apps/canonical_port/backend/agents/router.py` (lines 35-104) | `create_agents_router()`, `post_agent_run()`, `get_quota()` | REST endpoint `/api/v1/agents/run` accepting `AgentRunRequest`, invoking `SmolagentAgentWrapper.run_autonomous_cycle()`. |
| `01_apps/canonical_port/backend/spec_modules/spec_02_ai_inference.py` (lines 26-176) | `Spec02AiInferenceModule` | Monitors llama.cpp RPC ports (8081-8084), Petals DHT (31330), Exo P2P (52415), and 82.8 GB pooled VRAM status. |
| `01_apps/canonical_port/backend/spec_modules/spec_05_agents_swarms.py` (lines 16-170) | `Spec05AgentsSwarmsModule`, `_read_elo_leaderboard()` | Reads ELO leaderboard (`elo_discoveries.jsonl` & static standings), monitors 4 orchestrator nodes and consensus rates. |
| `00_core_infrastructure/self_healing_hub/src/tiered_multi_model_router.py` (lines 237-700) | `TieredMultiModelRouter`, `route_task()`, `calculate_cost()`, `slice_ast_context()` | 8-pillar engine routing across macro context (>100k to Gemini 3.1 Pro), local code synthesis (Qwen 2.5 Max via TB4 RPC 50052), vision, tools (Hermes 3), Spark (:8750), Ray (:8265), and OpenClaw UI. |
| `02_ai_models_and_inference/dynamic_agi_fallback_router.py` (lines 1-124) | `evaluate_and_route()`, `check_mesh_health()`, `trigger_mesh_repair()` | Dynamic survival router: evaluates 7-layer mesh health; downshifts to device survival models (Qwen-27B on Mac, Llama-8B on MBP, Mistral-7B on Linux, Gemma-9B on Pixel) or upshifts to Kimi-88B-Tandem. |
| `02_ai_models_and_inference/sharding_daemon/router.py` (lines 362-784) | `NetworkAwareDHTRouter`, `find_optimal_sharding_route()`, `build_routing_plan()` | Dynamic programming Dijkstra router across Petals DHT blocks, factoring RTT, packet loss, bandwidth, and fast circuit breakers. |
| `06_scripts_and_tooling/automation/cloud_api_quota_manager.py` (lines 1-1408) | `CloudAPIQuotaManager`, `LocalMeshAdapter`, `CloudflareAdapter`, `JulienAdapter`, `GeminiAdapter` | Composite heuristic router ($Score = 0.40 Q_{rem} + 0.25 S_{norm} + 0.25 T_{fit} + 0.10 H - P_{fail}$) balancing free cloud tiers with local mesh endpoints. |
| `00_core_infrastructure/self_healing_hub/src/canonical_ai_leaderboard.py` (lines 1-2232) | `CanonicalAILeaderboardEngine`, `compute_dynamic_k_factor()`, `record_match_victory()` | Multi-factor dynamic ELO engine ($K = K_0 \cdot \eta_{type} \cdot \eta_{size} \cdot \eta_{token} \cdot \eta_{consensus} \cdot \eta_{compute} \cdot \eta_{truth}$) with JSON schema v7 and atomic disk persistence. |
| `05_agents_and_swarms/red_blue_arena/tournament/leaderboard_connector.py` (lines 1-588) | `LeaderboardConnector`, `ABILITERATED_LLAMA_PROFILE` | Connects Red/Blue adversarial duels to canonical leaderboard; manages Devil's Advocate contender profile (Base ELO 2350.0). |
| `ai_debate/src/tri_orchestrator_debate.py` (lines 1-1003) | `TriOrchestratorDebateEngine`, `execute_shizuku_architecture_debate()`, `update_elo_leaderboard()` | 4-turn state machine debate engine: proposals, cross-examination, mathematical accord synthesis, and LoRA dataset logging. |

---

## 3. Current Prompt Ingestion and Response Flow Analysis

### 3.1 Trace of Current Flow

```
[User / Client Prompt]
         │
         ▼
[POST /api/v1/agents/run] (canonical_port/backend/agents/router.py:48)
         │
         ▼
[SmolagentAgentWrapper.run_autonomous_cycle(task)] (smolagents_ecosystem.py:266)
         │
         ├──> [CloudAIRouter.route_request(prompt)] (cloud_ai_router.py:56)
         │           │
         │           ├── Checks provider health: local_llamacpp -> local_exo -> cloudflare -> gemini
         │           └── Returns single {provider, model, is_local, status}
         │
         ├──> Executes matched tool (if tool name in prompt) (smolagents_ecosystem.py:287)
         │
         └──> Returns Single Response JSON to User:
              {
                "task": task_name,
                "provider_used": routed["provider"],
                "model_used": routed["model"],
                "tool_result": tool_result,
                "status": "COMPLETED",
                "timestamp": 1756345...
              }
```

### 3.2 Key Operational Characteristics & Gaps
1. **Synchronous/Blocking Execution per Prompt**: The request path selects exactly one model and awaits its completion before returning to the caller.
2. **Zero Challenger Execution**: No secondary or tertiary models receive the prompt in background tasks.
3. **Static ELO Utilization**: `CloudAIRouter` uses hardcoded priority tiers (`local_llamacpp` > `local_exo` > `cloudflare_ai_free` > `gemini_flash_free`) rather than reading the live `#1 Champion` from `data/canonical_ai_leaderboard.json` or `04_data_and_memory/data/ai_elo_leaderboard.json`.
4. **Disconnected Debate Engine**: The Tri-Orchestrator debate engine runs independently via scripts or cron triggers instead of consuming live prompt-response triples from user interactions.

---

## 4. Mesh Model Endpoints & Inventory Catalog

### 4.1 Local Mesh llama.cpp & RPC Ports

| Port | Protocol / Service | Binding Node & Transport | Configured Models / Role | Active Footprint |
| :--- | :--- | :--- | :--- | :--- |
| **`8081`** | HTTP / OpenAI REST (`/v1/chat/completions`) | L1 Mac Mini M4 (`127.0.0.1`) | Master llama-server: Kimi-Dev-72B / Nous-Hermes-3-8B / Qwen 2.5 Max | 21.6 GB VRAM Cap |
| **`8082`** | HTTP / OpenAI REST (`/v1/chat/completions`) | L2 MacBook Pro (`169.254.187.138` via 10Gbps TB4 DMA) | Gemma-2-9B / Llama-3-8B-Instruct-Q8 / Shard 2 Metal MPS | 14.0 GB VRAM Cap |
| **`8083`** | HTTP / OpenAI REST (`/v1/chat/completions`) | L3 Linux Head Node (`100.101.39.98` via 1GbE LAN) | Mistral-7B-Instruct / Shard 1 Vulkan/CPU / Ray Hub (:8265) | 13.8 GB VRAM Cap |
| **`8084`** | HTTP / OpenAI REST (`/v1/chat/completions`) | L5 MacBook Air (`100.93.158.96`) / Local Fallback | Qwen2.5-VL-7B Edge Vision / LoRA Distillation Metal Worker | 14.0 GB VRAM Cap |
| **`8085`** | HTTP / OpenAI REST (`/v1/chat/completions`) | L1 Mac Mini M4 (`127.0.0.1`) | Dedicated Kimi-VL Thinking 2506 (`mmproj-f16.gguf`) | 9.8 GB VRAM Cap |
| **`50052`** | GGML RPC (`ggml-rpc-server`) | L1 + L2 + L3 + L5 Mesh | 5-Way Distributed Tensor Parallel Sharding (80 layers: 28, 28, 24) | 48.8 GB / 82.8 GB Pooled |
| **`31330`** | Libp2p / Petals DHT Ring | Multi-Node Mesh (L1-L7) | Distributed Layer-Parallel Swarm (Bloom / Llama 70B+ blocks) | Dynamic VRAM |
| **`52415`** | Exo P2P Cluster | macOS / Linux Nodes | Ring Memory MLX Dynamic Layer Splitting | Dynamic VRAM |
| **`8750`** | PySpark AST Service (`/v1/slice`) | L1 Mac Mini M4 | Lakehouse telemetry & In-Process AST Call-Graph Slicing | RAM Lakehouse |

### 4.2 GGUF Model Vaults Catalog

Located across `02_ai_models_and_inference/model_vault_gguf/`, `02_ai_models_and_inference/models/`, and `~/DFS_UNIFIED/AI_Models_Vault/`:

#### A. 100B+ Frontier Models
* `pmysl/c4ai-command-r-plus-GGUF` (`command-r-plus.Q3_K_L.gguf` - 104B Parameters)
* `Kimi-VL-Encoder-x-Kimi-Dev-72B-MoE` (Kimi Tandem 88B Hybrid Vision-Language MoE, 80 Layers)

#### B. 70B Abliterated & Frontier Models
* `mradermacher/Meta-Llama-3.1-70B-Instruct-abliterated-GGUF` (`Meta-Llama-3.1-70B-Instruct-abliterated.Q4_K_M.gguf` - 70B Uncensored Devil's Advocate)
* `Llama-3.3-70B-Instruct-Q4_K_M` (Frontier RPC Sharded Contender)
* `Qwen2.5-VL-72B-Instruct-Q4_K_M` (Frontier Vision-Language Reasoner)

#### C. Local Sub-35B Specialists & Edge Models
* `DeepSeek-R1-Distill-Qwen-32B-Q4_K_M` (Apex Local Reasoning & Code Verification)
* `Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf` (12B, 128k Context)
* `gemma-2-9b-it-abliterated-Q4_K_M.gguf` (9B High-Density Reasoning)
* `meta-llama-3.1-8b-instruct-abliterated.Q4_K_M.gguf` (8B Devil's Advocate)
* `qwen2.5-coder-7b-instruct-q4_k_m.gguf` (7B Low-Latency Coding Specialist)
* `Hermes-3-Llama-3.1-8B-Q8_0` (Structured Tool / JSON Calling Specialist)
* `qwen2.5-0.5b-instruct-q4_k_m.gguf` & `SmolLM2-360M` (Micro-Surveillance Models)

### 4.3 Cloud APIs & External Gateways

| Provider ID | Adapter / Protocol | Quota / Limits | Role in Continuous Arena |
| :--- | :--- | :--- | :--- |
| **`gemini_31_pro`** | REST (`generativelanguage.googleapis.com`) | Paid API / Benchmark Anchor | Macro Strategic Horizon & Ground-Truth Debate Referee |
| **`gemini_flash`** | REST (`gemini-3.7-flash` / `gemini-2.5-flash`) | 1,500 RPD Free / 185 tok/s | Tactical Co-Pilot, Challenger Candidate, High-Speed Evaluator |
| **`cloudflare_ai`** | REST (`api.cloudflare.com/.../meta/llama-3.1-8b`) | 1,000 RPD Free / 120 tok/s | Edge Challenger Candidate & Remote Outage Fallback |
| **`julien_ai`** | REST / CLI (`jules exec` / `api.jules.google.com`) | 300 RPD Free / 45 tok/s | Multi-Repo Coding Challenger & Distillation Teacher |
| **`claude_37_sonnet`**| Anthropic REST (`claude-3-7-sonnet-20250219`) | Paid API Benchmark | External Ground-Truth Quality Baseline |

---

## 5. Architectural Recommendations for R1: Continuous Challenger Format

### 5.1 System Architecture Overview

```
                          [User Prompt Ingestion]
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
    [Synchronous Fast Path]                  [Asynchronous Shadow Path]
  (Zero Added Latency to User)               (Background Event Loop Task)
                 │                                       │
  Read elo_leaderboard.json                              │
  Identify #1 "Champion" Model                           │
  (e.g., Kimi Tandem / Qwen Max)                         │
                 │                                       │
  Execute Champion Model                                 │
  (Local RPC / Gemini API)                               │
                 │                                       │
                 ├───> [Return Result to User]           │
                 │                                       │
                 └───────────────────────────────┐       │
                                                 ▼       ▼
                                      [Select 2 Challenger Models]
                                      • Challenger 1: Local 100B+ / 70B Abliterated
                                      • Challenger 2: Cloud / Edge API (Julien/Cloudflare/Flash)
                                                 │
                                                 ▼
                                      [Execute Challengers in Parallel]
                                      (asyncio.gather with circuit breakers)
                                                 │
                                                 ▼
                                      [Tri-Orchestrator Blind Grading]
                                      • Mask Model IDs: Candidate A, B, C
                                      • Grade Syntax, Truth, Logic, Compactness
                                      • Determine Win / Loss / Draw matrix
                                                 │
                                                 ▼
                                      [Multi-Factor Dynamic ELO Update]
                                      • Apply K-factor formula (eta_size, eta_token...)
                                      • Update data/canonical_ai_leaderboard.json
                                      • Append to continuous_lora_dataset.jsonl
                                                 │
                                                 ▼
                                   [Dynamic Champion Promotion]
                                   If Challenger ELO > Champion ELO:
                                   New Champion promoted for next prompt!
```

### 5.2 Specific Subsystem Modifications

#### 1. Core Router Enhancement (`01_apps/canonical_port/backend/agents/cloud_ai_router.py` & `UnifiedInferenceRouter`)
- **Dynamic Leaderboard Ingestion**: At initialization and before routing each prompt, inspect `data/canonical_ai_leaderboard.json` or `04_data_and_memory/data/ai_elo_leaderboard.json` to extract the highest ELO model as the dynamic `#1 Champion`.
- **Dual-Phase Execution**:
  - `route_and_execute_champion(prompt)`: Performs the primary synchronous invocation. Returns the `TaskResult` directly to the user.
  - `dispatch_challengers_background(prompt, champion_result)`: Spawns an `asyncio.create_task` that runs in the background without holding up the user response.

#### 2. Challenger Model Dynamic Cycler
- Maintain an active round-robin / randomized candidate rotation pool:
  - **Pool A (Local Titans & Abliterated Giants)**: `c4ai-command-r-plus` (104B), `Meta-Llama-3.1-70B-abliterated`, `DeepSeek-R1-Distill-32B`, `Mistral-Nemo-12B-abliterated`.
  - **Pool B (Sovereign Local Specialists)**: `Qwen2.5-Coder-7B`, `Gemma-2-9B-abliterated`, `Hermes-3-8B`, `Qwen2.5-VL-7B`.
  - **Pool C (Free-Tier Cloud Gateways)**: `cloudflare_ai` (Llama 3.1 8B), `julien_ai` (@google/jules), `gemini_flash` (3.7 Flash).
- For each user prompt, dynamically select 2 challengers from different pools to maximize competitive diversity.

#### 3. Tri-Orchestrator Blind Grading Hook (`ai-debate` integration)
- Anonymize the three outputs:
  - `Candidate_Alpha`: Output from Champion
  - `Candidate_Beta`: Output from Challenger 1
  - `Candidate_Gamma`: Output from Challenger 2
- The Tri-Orchestrator (using `Gemini 3.1 Pro` / `Gemini 1.5 Flash High` / `Genetic MoE`) evaluates the responses against:
  1. AST Syntax & Code Correctness ($0.35$ weight)
  2. Rule #0 Truth Invariant & Zero-Mock Compliance ($0.35$ weight)
  3. Token Efficiency & Conciseness ($0.15$ weight)
  4. Response Latency & Compute Footprint ($0.15$ weight)
- Computes pairwise duel outcomes:
  - `Champion vs Challenger 1`
  - `Champion vs Challenger 2`
  - `Challenger 1 vs Challenger 2`

#### 4. Mathematical ELO & LoRA Distillation Update
- Use `CanonicalAILeaderboardEngine.record_match_victory()` from `00_core_infrastructure/self_healing_hub/src/canonical_ai_leaderboard.py`.
- Atomically commit the updated ratings to `data/canonical_ai_leaderboard.json` using POSIX atomic rename (`os.replace`).
- Serialize the multi-turn evaluation transcript into `04_data_and_memory/lora_datasets/continuous_lora_dataset.jsonl` and `data/lora_datasets/truth_audit_debate.jsonl`.

---

## 6. Proposed Implementation Blueprints (Code Snippets)

### 6.1 `ContinuousArenaInferenceRouter` Blueprint

```python
# Proposed addition in 01_apps/canonical_port/backend/agents/continuous_arena_router.py
import asyncio
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("ContinuousArenaRouter")

class ContinuousArenaInferenceRouter:
    """
    R1 Continuous Challenger Engine:
    1. Synchronous execution of #1 Ranked Champion model.
    2. Background async dispatch of 2 Challenger models.
    3. Tri-Orchestrator blind grading & dynamic ELO mutation.
    """
    def __init__(self, leaderboard_path: Path, challenger_pool: List[Dict[str, Any]]):
        self.leaderboard_path = leaderboard_path
        self.challenger_pool = challenger_pool
        self._rotation_index = 0

    def get_current_champion(self) -> Dict[str, Any]:
        """Reads highest-rated model dynamically from canonical leaderboard."""
        try:
            with open(self.leaderboard_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            leaderboard = data.get("leaderboard", [])
            if leaderboard:
                # Sort descending by ELO
                sorted_models = sorted(leaderboard, key=lambda m: m.get("elo", m.get("base_elo", 1500.0)), reverse=True)
                return sorted_models[0]
        except Exception as e:
            logger.warning(f"Failed to read leaderboard: {e}")
        # Default fallback champion
        return {"id": "kimi_tandem_titan", "name": "Kimi Tandem Titan 88B", "endpoint": "http://127.0.0.1:8081/v1"}

    def select_challengers(self, champion_id: str, count: int = 2) -> List[Dict[str, Any]]:
        """Selects 2 challengers excluding current champion via round-robin."""
        candidates = [m for m in self.challenger_pool if m["id"] != champion_id]
        if not candidates:
            return []
        selected = []
        for _ in range(min(count, len(candidates))):
            selected.append(candidates[self._rotation_index % len(candidates)])
            self._rotation_index += 1
        return selected

    async def execute_task_with_continuous_arena(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """
        Executes Champion synchronously and launches Challengers in background.
        """
        champion = self.get_current_champion()
        t0 = time.perf_counter()
        
        # 1. Synchronous Champion Execution
        champion_output = await self._execute_model_endpoint(champion, prompt, system_prompt)
        champion_latency = (time.perf_counter() - t0) * 1000.0

        champion_result = {
            "model_id": champion["id"],
            "model_name": champion.get("name", champion["id"]),
            "output": champion_output,
            "latency_ms": champion_latency,
            "is_champion": True
        }

        # 2. Select Challengers & Launch Shadow Arena in Background
        challengers = self.select_challengers(champion["id"], count=2)
        if challengers:
            asyncio.create_task(
                self._run_background_shadow_arena(prompt, system_prompt, champion_result, challengers)
            )

        # 3. Return Champion Result immediately to User
        return {
            "status": "SUCCESS",
            "champion_used": champion["id"],
            "response": champion_output,
            "latency_ms": champion_latency,
            "shadow_challengers_dispatched": [c["id"] for c in challengers]
        }

    async def _run_background_shadow_arena(
        self, prompt: str, system_prompt: str, champion_res: Dict[str, Any], challengers: List[Dict[str, Any]]
    ):
        """Background coroutine: executes challengers, grades outputs, updates ELO."""
        try:
            # Parallel execution of challengers
            tasks = [self._execute_model_endpoint(c, prompt, system_prompt) for c in challengers]
            challenger_outputs = await asyncio.gather(*tasks, return_exceptions=True)

            challenger_results = []
            for c, out in zip(challengers, challenger_outputs):
                if isinstance(out, Exception) or not out:
                    continue
                challenger_results.append({
                    "model_id": c["id"],
                    "model_name": c.get("name", c["id"]),
                    "output": str(out),
                    "is_champion": False
                })

            if challenger_results:
                # Trigger Tri-Orchestrator Blind Grading
                from ai_debate.src.tri_orchestrator_debate import TriOrchestratorDebateEngine
                debate_engine = TriOrchestratorDebateEngine()
                # Grade outputs and commit ELO delta to canonical leaderboard
                # ...
        except Exception as e:
            logger.error(f"Error in background shadow arena: {e}")
```

---

## 7. Verification & Compliance Matrix

| Invariant / Requirement | Verification Mechanism | Status |
| :--- | :--- | :--- |
| **Rule #0 (Zero Fake Data)** | All endpoint addresses, ports, and model paths verified against filesystem and active network sockets. | **VERIFIED** |
| **Tri-Vault Storage Health** | Fast-path check confirmed `obsidian_vault`, `lora_datasets`, and `04_data_and_memory` directories are healthy. | **VERIFIED** |
| **Read-Only Explorer Discipline** | No production source files modified; all findings isolated to `.agents/explorer_survey_1/`. | **VERIFIED** |
| **Self-Contained Handoff** | All line numbers, file paths, and architectural models documented in `handoff.md`. | **VERIFIED** |
