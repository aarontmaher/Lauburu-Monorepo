# Survey Report: Monorepo Cron Architecture, Rate Limiting, & 7-Daemon Orchestration

**Author:** `teamwork_preview_explorer_survey_1`  
**Date:** 2026-08-29  
**Milestone:** Requirement R1 Survey & Monorepo Daemon Architecture  
**Working Directory:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_1/`

---

## Executive Summary

This survey provides an exhaustive technical analysis of the existing cron scheduling architecture, rate-limiting frameworks, 7-layer physical mesh daemon lifecycle governance, local vs. cloud inference coordination, and biometric airgapping invariants across the Lauburu Monorepo. All observations cite exact file paths, line numbers, and architectural mechanisms.

---

## 1. Daemon Scripts, Systemd/Launchd Configs, & Cron Definitions

### 1.1 Autostart & OS Daemon Governance
- **`06_scripts_and_tooling/network/autostart_installer.py` (lines 7–77):**
  - **macOS LaunchAgent:** Generates and registers `~/Library/LaunchAgents/ai.lauburu.nomad_courier.plist` with `RunAtLoad=true`, `KeepAlive=true`, and executes `caffeinate -dimsu` to prevent system sleep while running `nomad_courier_self_healer.py --daemon` and the Swarm Dashboard backend.
  - **Linux Systemd:** Generates and enables `~/.config/systemd/user/lauburu_nomad.service` with `Restart=always`, `RestartSec=10`.
  - **Android Termux:** Generates `~/.termux/boot/99_lauburu_nomad.sh` enabling `termux-wake-lock` and persistent background daemons.

### 1.2 Multi-Tier Automation Loops & Crons
- **`06_scripts_and_tooling/automation/free_tier_ai_continuous_cron.py` (lines 9–108):**
  - **Tier 1 (1m cycle):** Real hardware router RAM governance, daemon watchdogs, and SQM fq_codel enforcement.
  - **Tier 2 (15m cycle):** Free-tier AI dataset harvesting (Gemini 2.5 Flash Free + Cloudflare + Local).
  - **Tier 3 (Daily 03:00 UTC):** Nightly QLoRA dataset compilation and Bradley-Terry ELO leaderboard updates.
  - **Status Sink:** Serializes execution state to `session_logs/free_ai_cron_status.json`.

- **`05_agents_and_swarms/master_priority_automation_loop.py` & `06_scripts_and_tooling/automation/start_priority_daemon.sh`:**
  - Enforces strict 5-tier execution loop:
    - **P0 (Infrastructure):** Dynamic RAM governance ($\le 90\%$ host cap) and GL.iNet router ping check (`192.168.8.1`).
    - **P1 (Movesense Biometrics):** 512Hz ECG, PTT Blood Pressure, and Zone 2 threshold compliance (`movesense_readiness_live.json`).
    - **P2 (Visual GPU Canvas):** 120 FPS Apple Silicon Metal Shaders / WebGPU WGSL canvas synchronization.
    - **P3 (LMSYS Arena ELO):** Local Chatbot Arena tournament execution and Bradley-Terry ELO calculation (`local_lmarena_benchmark_harness.py`).
    - **P4 (LoRA Continuous Harvesting):** Serializes actions to `04_data_and_memory/nomad_autonomous_actions.jsonl`.

- **`06_scripts_and_tooling/network/nomad_courier_self_healer.py` (lines 1–323):**
  - 6-Tier autonomous self-healing loop:
    - **T1:** Service Port Health (8080, 8082, 8083, 8084, 8085, 18802, 4000).
    - **T2:** RPC Mesh Probe (Tailscale nodes: MacBook Air `100.93.158.96:50052`, Linux Head `100.101.39.98:50052`, Pixel 10 `100.73.38.87:50052`, MacBook Pro `100.103.212.21:50052`).
    - **T3:** AI Model Status (`llama-server` health + auto-restart).
    - **T4:** Git & Storage Health (removes `.git/index.lock`, verifies Obsidian vault and `lora_datasets`, checks $\ge 5.0\text{ GB}$ disk headroom).
    - **T5:** Skills Guardian (validates `~/.gemini/config/skills/`).
    - **T6:** LoRA Serialization (`data/lora_datasets/nomad_autonomous_actions.jsonl`).

- **`00_core_infrastructure/cloudflare_worker/src/overnight-queue.ts` (lines 1–341):**
  - Durable backlog in `connector_overnight_queue` (Supabase) for unattended overnight execution.
  - Priority ladder: `p0` > `p1` > `p2` > `p3` > `overnight_only`.
  - Stale detection threshold: 72 hours (`DEFAULT_STALE_THRESHOLD_HOURS`).
  - Strict invariant: P0/P1 blockers always supersede overnight tasks.

---

## 2. Core Monorepo Daemons & Supervised Ports Matrix

The monorepo operates a distributed matrix of 7+ core daemons across Ports 8080–8086, 18802, 50052, and 8088:

| Port | Subsystem / Service | Definition / Entry Point | Health Check Method | Auto-Restart / Failover Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **8080** | **Lauburu Unified AI Proxy** & SeaweedFS Master | `02_ai_models_and_inference/lauburu_ai_proxy.py` & `00_core_infrastructure/docker/docker-compose.dfs*.yml` | Fast TCP socket probe (`_probe_local`, 0.05s timeout) + HTTP `GET /v1/proxy/status` | `nomad_courier_self_healer.py` triggers `launchctl load ai.lauburu.unified.proxy.plist` |
| **8081** | **llama-server (Qwen-3.8Max / GPT-OSS 20B)** | `lauburu_ai_proxy.py:79`, `MANAGED_MODELS` | HTTP `GET http://127.0.0.1:8081/health` (`{"status": "ok"}`) | `nomad_courier_self_healer.py` runs `launch_model(8081)` via `llama-server` CLI |
| **8082** | **llama-server (Mistral-Nemo-12B Q4_K_M)** | `nomad_courier_self_healer.py:53`, `lauburu_ai_proxy.py:84` | HTTP `GET http://127.0.0.1:8082/health` | `nomad_courier_self_healer.py:191` automatically spawns background process |
| **8083** | **llama-server (Qwen2.5-Coder-7B Q4_K_M)** | `nomad_courier_self_healer.py:47`, `lauburu_ai_proxy.py:78` | HTTP `GET http://127.0.0.1:8083/health` | Auto-restarted with `-ngl 99 -c 4096 --no-jinja` |
| **8084** | **llama-server (Nemotron-70B Q4_K_M RPC / RAG Edge)** | `nomad_courier_self_healer.py:59`, `lauburu_ai_proxy.py:85` | HTTP `GET http://127.0.0.1:8084/health` | Multi-node tensor sharded with `--rpc 100.93.158.96:50052,100.73.38.87:50052` |
| **8085** | **llama-server (Qwen2.5-7B-Abliterated / Qwen38-27B)** | `nomad_courier_self_healer.py:65`, `lauburu_ai_proxy.py:82` | HTTP `GET http://127.0.0.1:8085/health` | Auto-restarted with `-c 2048 -b 256 -t 8` |
| **8086** | **llama-server (Qwen2.5-Math-7B Algorithm Specialist)** | `lauburu_ai_proxy.py:83` | HTTP `GET http://127.0.0.1:8086/health` | Spawned on demand for mathematical / AST proofs |
| **18802** | **Self-Healing Hub Reflex Arc & WoL API** | `00_core_infrastructure/self_healing_hub/src/api_server.py` | TCP socket probe (`tri_layer_hybrid_orchestrator.py:437`, `router_mesh_watchdog.sh:167`) | Tier 2 WoL Magic Packet dispatch & Tier 3 daemon respawn |
| **50052** | **llama.cpp Distributed Metal GPU RPC Server** | `02_ai_models_and_inference/llama_rpc_mesh/launch_kimi_tandem_rpc.sh` | TCP socket probe (`test_m3_sharding_and_governor.py`, `probe_real_socket`) | `daemon_manager.py:32` (`nohup llama-rpc-server --host 0.0.0.0 --port 50052 &`) with Mac Host $\rightarrow$ Linux Head failover |
| **8088** | **Master Supervisor / Gemini Spark Cloud Router** | `00_core_infrastructure/multi_wan/agi_offload.py:22`, `api_server.py:2895` | HTTP `GET http://100.101.39.98:8088/status` | Managed supervisor with multi-WAN failover |

---

## 3. Rate-Limiting Frameworks & Free-Tier Quota Optimization

### 3.1 Cloud API Quota Manager (`cloud_api_quota_manager.py`)
- **Location:** `06_scripts_and_tooling/automation/cloud_api_quota_manager.py` (lines 98–630)
- **Quota State Persistence:**
  - State file: `04_data_and_memory/data/cloud_api_quota_state.json`
  - Concurrency Lock: `fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)` on `.lock` file.
  - Automatic UTC midnight rollover resets all counters (`_check_and_apply_midnight_reset`).
- **Provider Quota Configurations:**
  - `gemini_free`: Daily Limit = 1,500 RPD, Max Tokens = 32,768, Rate Limit = 15 RPM (Safety clamped to 14 RPM / 1,400 RPD).
  - `cloudflare_ai`: Daily Limit = 1,000 RPD (10k Neurons), Max Tokens = 4,096, Rate Limit = 50 RPM.
  - `julien_ai`: Daily Limit = 300 RPD (Policy disabled / 403 status).
  - `local_mesh`: Daily Limit = 999,999 RPD, Max Tokens = 16,384, Rate Limit = 1,000 RPM (Zero cost, sovereign fallback).
- **Multi-Factor Composite Heuristic Routing Equation:**
  $$\text{Score} = 0.40 \cdot Q_{\text{rem\_pct}} + 0.25 \cdot S_{\text{norm}} + 0.25 \cdot T_{\text{fit}} + 0.10 \cdot H_{\text{health}} - P_{\text{failures}}$$
  - Rate limit (429) triggers immediate 60-second cooldown (`cooldown_until = now + 60.0`) and initiates cascade fallback to next best candidate or `local_mesh`.

### 3.2 Cloudflare AI Gateway Router (`ai_gateway_router/worker.js`)
- **Location:** `00_core_infrastructure/cloudflare/workers/ai_gateway_router/worker.js` (lines 1–166)
- Routes `/v1/google/*`, `/v1/gemini/*`, `/v1/cloudflare/*`, `/v1/workers-ai/*`, `/v1/huggingface/*`.
- Binds directly to `env.AI.run` for zero-latency Cloudflare Workers AI edge execution or routes through Cloudflare AI Gateway (`gateway.ai.cloudflare.com/v1/.../lauburu-ai-gateway`) for telemetry and rate-limiting analytics.

### 3.3 AI Spend Gates Spec (`AI_SPEND_GATES_SPEC.md`)
- **Location:** `07_docs_and_architecture/core_docs/AI_SPEND_GATES_SPEC.md`
- **Cost Decision Ladder:**
  1. `free_deterministic`: Local regex, MCP reads, static dictionaries (Always runs first, $0 cost).
  2. `cheap_ai`: Short LLM calls ($\le 4\text{k}$ prompt, $\le 500$ out), rate limited to 60 calls/hour per user.
  3. `expensive_ai`: Long-context ($\ge 4\text{k}$ prompt), multi-pass synthesis, vision audits (Gated behind human approval push notification).
  4. `deep_research_external`: Extended synthesis (Export prompt by default).

---

## 4. Local Mesh Inference & Off-Peak Scheduling Coordination

### 4.1 Local Inference Distribution (Ports 8081–8086 & 50052)
- **Local Proxy Architecture (`lauburu_ai_proxy.py`):**
  - Unified OpenAI-compatible endpoint on Port 8080 (`/v1/chat/completions`).
  - Routes model requests to dedicated background ports (`local/qwen` $\rightarrow$ `:8083`, `local/qwen-3.8max` $\rightarrow$ `:8081`, `local/mistral` $\rightarrow$ `:8082`, `local/nemotron` $\rightarrow$ `:8084`, `local/qwen-abliterated` $\rightarrow$ `:8085`, `local/qwen-math` $\rightarrow$ `:8086`).
  - Remote edge acceleration: Pixel 10 Pro Tensor G5 on Port 8087 (`100.73.38.87:8087`).
- **Distributed Tensor Sharding (`llama_rpc_mesh`):**
  - Interconnects L1 Mac Host (24 layers), L2 MacBook Pro (28 layers over 40Gbps TB4 DMA bridge `169.254.187.138`), and L3 Linux Head Node (28 layers `100.101.39.98`) over RPC Port 50052.

### 4.2 Local vs. Cloud Off-Peak Coordination
- **Daytime Schedule (Active Athlete Hours):**
  - Real-time physiological telemetry (Movesense 512Hz ECG, Pan-Tompkins QRS, PTT BP) streams locally.
  - Interactive dev queries utilize fast local models (Qwen2.5-Coder-7B) and free cloud flash queries.
- **Overnight Schedule (00:00 – 06:00 UTC / Off-Peak Windows):**
  - `overnight-queue.ts`: Dispatches unattended AST refactoring, heavy unit test scaffolding, and deep doc synthesis.
  - `free_tier_ai_continuous_cron.py` (Tier 3 at 03:00 UTC): Gathers synthetic training pairs, merges Hugging Face DPO/RLHF instruction sets, and runs nightly local PEFT/TRL QLoRA distillation on Metal GPU.

---

## 5. Biometric Airgapping & Privacy Floor Invariants

### 5.1 Strict Cloudflare Edge Egress Firewall
- **`00_core_infrastructure/cloudflare_worker/src/worker.ts` (lines 274–395) & `test-airgap-biometrics-isolation.ts`:**
  - **Blocked Paths (`FORBIDDEN_AIRGAP_PATHS`):**
    - `/api/biometrics/*`, `/api/movesense/*`, `/api/512hz_ecg/*`, `/api/ptt/*`, `/api/ppg/*`, `/api/sleep_staging/*`, `/api/raw_rr/*`, `/ws/biometrics/*`.
    - Returns **HTTP 403 Forbidden** with `egressBlocked: true` and `error: "100% Local Airgap Violation"`.
  - **Blocked Keys (`FORBIDDEN_BIOMETRIC_KEYS`):**
    - `ecg_samples`, `raw_ecg_mv`, `movesense_packet`, `raw_ppg_stream`, `raw_rr_stream`, `ptt_blood_pressure_raw`, `dfa_alpha1_raw`, `pan_tompkins_raw`, etc.
    - Automatically replaced with `[AIRGAP_REDACTED: LOCAL_HARDWARE_ONLY]`.
  - **Blocked Headers:**
    - `x-lauburu-biometrics-egress`, `x-raw-biometrics`.

### 5.2 Code Scaffolder & Inference Airgap Inspection
- **`06_scripts_and_tooling/automation/code_scaffold_daemon.py` (lines 118–142):**
  - Scans prompt contexts and generated ASTs with `FORBIDDEN_BIOMETRIC_REGEX`.
  - If raw physiological patterns (`raw_ecg`, `movesense_gatt`, `512hz_ecg`, `ptt_blood_pressure`, `dfa_alpha1`) are detected, the daemon automatically forces `prefer_local = True`, restricting execution strictly to `127.0.0.1` Local Mesh with zero external cloud egress.
- **`02_ai_models_and_inference/lauburu_ai_proxy.py` (line 137):**
  - `STRICT_LOCAL_AIRGAP_HEALTH_LOCK = True`: Unconditionally isolates all health and biometric processing to local Apple Silicon Metal GPU.

---

## 6. Synthesis & Gaps Identified for Requirement R1

1. **Quota Calibration:** The existing quota manager in `cloud_api_quota_manager.py` already includes Google Gemini Free (1,500 RPD / 15 RPM) and Cloudflare Workers AI (1,000 RPD / 10k Neurons), but needs direct integration into the continuous cron schedule (`free_tier_ai_continuous_cron.py`) with explicit 14 RPM / 1,400 RPD rate limiter clamping.
2. **Unified Daemon Supervisor Integration:** The 7 individual `llama-server` instances (Ports 8081–8086), Proxy (:8080), WoL (:18802), RPC (:50052), and Supervisor (:8088) have operational restart logic in `nomad_courier_self_healer.py` and `daemon_manager.py`, which should be harmonized under the central 24/7 cron pipeline.
3. **Continuous LoRA Sink Standardization:** Synthetic datasets are actively harvested to `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl` and `04_data_and_memory/lora_datasets/continuous_lora_dataset.jsonl` using `LoRADatasetWriter` with `fcntl.flock` locks, perfectly aligned with Requirement R2 and R3.
