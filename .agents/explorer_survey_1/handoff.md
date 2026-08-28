# Handoff Report — explorer_survey_1 (Inference Router Explorer)

**Role**: Inference Router Explorer  
**Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_survey_1/`  
**Timestamp**: 2026-08-28T12:46:30+10:00  
**Handoff Type**: Hard (Task Complete)

---

## 1. Observation

1. **`01_apps/canonical_port/backend/agents/cloud_ai_router.py` (lines 56-115, 118-155)**:
   - `route_request(prompt)` synchronously evaluates fixed tiers: `local_llamacpp` (Priority 1) -> `local_exo` (Priority 2) -> `cloudflare_ai_free` (Priority 3) -> `gemini_flash_free` (Priority 4).
   - `generate_response()` yields to the event loop (`await asyncio.sleep(0)`), calls `route_request()`, generates a single response for the routed model, and returns a single JSON object.
   - Observation: Currently **no shadow or background challenger execution** occurs upon prompt receipt.

2. **`01_apps/canonical_port/backend/agents/smolagents_ecosystem.py` (lines 266-302)**:
   - `SmolagentAgentWrapper.run_autonomous_cycle(task_name)` calls `self.router.route_request()`, executes tool if applicable, and returns single result dictionary.

3. **`00_core_infrastructure/self_healing_hub/src/tiered_multi_model_router.py` (lines 45-200, 377-593)**:
   - Contains an 8-pillar routing engine: `macro_strategy` (Gemini 3.1 Pro Preview), `tactical_planning_shadow_audit` (Gemini 1.5/3.7 Flash High), `local_code_synthesis` (Qwen 2.5 Max via TB4 RPC Port 50052), `local_vision_grounding` (Qwen 2.5 VL Port 8080), `structured_function_calling` (Nous Hermes 3 Port 8081), `pyspark_bigdata_stream` (Port 8750), `ray_distributed_actors` (Port 8265), and `ui_automation` (OpenClaw Port 18789).
   - Has AST context slicing via Port 8750 and 24/7 LoRA logging to `tiered_router_decisions.jsonl`.

4. **`02_ai_models_and_inference/dynamic_agi_fallback_router.py` (lines 22-49, 84-121)**:
   - Evaluates 7-layer mesh health from `data/network/nomad_self_healer_status.json`. If health >= 0.99, activates `TITAN_MODEL = "Kimi-88B-Tandem-IQ3_S"`; otherwise downshifts to device-specific survival models (Qwen-27B on Mac, Llama-8B on MBP, Mistral-7B on Linux, Gemma-9B on Pixel).

5. **`02_ai_models_and_inference/llama_rpc_mesh/` and `model_vault_gguf/`**:
   - `README.md` (lines 5-11): llama.cpp master server on Port 8081, vision on Port 8085, edge vision on Port 8084, RPC sharding on Port 50052.
   - GGUF vault contains: `meta-llama-3.1-8b-instruct-abliterated.Q4_K_M.gguf` (4.92 GB), `Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf` (7.48 GB), `gemma-2-9b-it-abliterated-Q4_K_M.gguf` (5.76 GB), `qwen2.5-coder-7b-instruct-q4_k_m.gguf` (4.68 GB), `command-r-plus.Q3_K_L.gguf` (104B parameter script), `Meta-Llama-3.1-70B-Instruct-abliterated.Q4_K_M.gguf` (70B download target).

6. **`00_core_infrastructure/self_healing_hub/src/canonical_ai_leaderboard.py` & `data/canonical_ai_leaderboard.json`**:
   - `CanonicalAILeaderboardEngine` implements multi-factor dynamic ELO:
     $$K = K_0 \cdot \eta_{type} \cdot \eta_{size} \cdot \eta_{token} \cdot \eta_{consensus} \cdot \eta_{compute} \cdot \eta_{truth}$$
   - Holds 15 model entries with `kimi_tandem_titan` (Base ELO 3089.0), `genetic_moe_orchestrator`, `DeepSeek-R1-Distill-Qwen-32B`, `Llama-3.3-70B`, `Qwen2.5-VL-72B`, etc.

7. **`ai_debate/src/tri_orchestrator_debate.py` (lines 820-948)**:
   - Executes 4-turn state machine debates and updates `data/memory/canonical_ai_leaderboard.json` using `CanonicalAILeaderboardEngine.record_match_victory()`.

---

## 2. Logic Chain

1. **Premise 1 (From Observations 1 & 2)**: The current user-facing prompt ingestion path in `canonical_port` routes through `CloudAIRouter.route_request()` and `generate_response()`, executing only a single model synchronously/serially before returning.
2. **Premise 2 (From Observation 5 & 6)**: The monorepo has an extensive inventory of local and remote model endpoints (ports 8081-8085, 100B+ Command-R+, 70B abliterated Llama, Cloudflare, Julien AI, Gemini) and a mathematically rigorous multi-factor ELO engine (`canonical_ai_leaderboard.py`).
3. **Premise 3 (From Observation 7)**: The Tri-Orchestrator debate engine currently runs in batch/script mode, but already contains the necessary logic (`record_match_victory`, LoRA dataset serialization) to evaluate models and update ELO ratings.
4. **Deduction**: To fulfill **Requirement R1 (Continuous Challenger Format)** without adding user-visible latency:
   - The user's prompt must be dispatched to the `#1 Champion` model synchronously (derived dynamically from the ELO leaderboard).
   - In parallel, an asynchronous background task (`asyncio.create_task`) must dispatch the same prompt to 2 rotating Challenger models (cycling through 100B+, 70B abliterated, and API gateways).
   - The background task pipes the Champion + Challenger outputs into the Tri-Orchestrator blind grading function, updates ELO ratings via `CanonicalAILeaderboardEngine`, and logs the interaction to the 24/7 LoRA dataset.
   - If a Challenger's ELO overtakes the Champion, the dynamic default selection immediately promotes the new Champion for the next incoming prompt.

---

## 3. Caveats

- **Active Network Sockets**: Under offline or disconnected testing environments, local RPC ports (8081-8084) may be simulated or in fallback mode; the router must employ adaptive timeouts (< 50ms) and fallback gracefully to `LocalMeshAdapter._synthesize_local_mesh_output` or survival models to prevent hanging.
- **Quota Limits**: Free-tier cloud endpoints (Cloudflare 1000 RPD, Julien 300 RPD, Gemini Free 1500 RPD) must continue to be tracked by `QuotaGovernor` so challenger rotations do not exhaust daily limits.
- No other caveats.

---

## 4. Conclusion

The monorepo has all foundational components (GGUF model catalog, ports 8081-8085, multi-factor ELO engine, Tri-Orchestrator debate engine) required for the Continuous AI Arena. The missing link is the **dual-path execution router** (`ContinuousArenaInferenceRouter` / enhanced `CloudAIRouter`) that bifurcates prompt ingestion into:
1. **Synchronous Immediate Response** from the current `#1 Champion`.
2. **Asynchronous Non-Blocking Shadow Arena** with 2 rotating Challengers, Tri-Orchestrator blind evaluation, and live ELO ledger mutation.

---

## 5. Verification Method

1. **Verify Files and Line References**:
   - `view_file` on `01_apps/canonical_port/backend/agents/cloud_ai_router.py` (lines 56-115).
   - `view_file` on `00_core_infrastructure/self_healing_hub/src/canonical_ai_leaderboard.py` (lines 1-100).
   - `view_file` on `02_ai_models_and_inference/dynamic_agi_fallback_router.py` (lines 20-50).
2. **Inspect Survey Reports**:
   - `view_file` on `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_survey_1/analysis.md`.
3. **Execution Command**:
   - Run `python3 -m pytest 02_ai_models_and_inference/tests/test_dht_and_router.py` or inspect python syntax of proposed designs.
