# Comprehensive Analysis: Local AI Training & LoRA Distillation Pipelines

**Explorer Agent:** Explorer 2  
**Date:** 2026-08-27  
**Working Directory:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_2`  
**Target Scope:** Local AI Training, LoRA Distillation, Quota Heuristics & Dataset Persistence across `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo` and `/Users/aaron/DFS_UNIFIED/lora_datasets/`

---

## 1. Executive Summary

This investigation analyzes the architecture, data schemas, training triggers, local inference mesh endpoints, and cloud quota management across the **Lauburu Monorepo** and the **Tri-Vault Storage Architecture** (Obsidian, PySpark Data Lake, GitHub Monorepo).

Key Findings:
1. **Dataset Storage & Ingestion:** LoRA datasets reside primarily in `/Users/aaron/DFS_UNIFIED/lora_datasets/` (23 active JSONL files, ~190 MB) with synchronized local links at `04_data_and_memory/lora_datasets/`, `data/lora_datasets/`, and continuous cloud sync to Google Drive VFS (`/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets/`).
2. **Schema Diversity:** The system utilizes 4 standard JSONL formats: (a) Alpaca Instruction-Thought-Output with real hardware certification, (b) OpenAI/ChatML multi-turn message arrays with winner provenance, (c) DPO preference pairs (prompt/chosen/rejected), and (d) TRL prompt/completion text pairs.
3. **Local Mesh & Training Endpoints:** 7 hardware layers pool 82.8 GB usable AI VRAM across Apple M4 Max, MacBook Pro (10Gbps TB4 DMA Bridge), AMD Ryzen 7 Linux Hub, Pixel 10 Pro XL (Tensor G5 Edge TPU), and Samsung S20+ (USB ADB). Active inference endpoints run on Ports 8081 (Hermes 3 / Master AGI), 50052 (Kimi Tandem / Qwen 2.5 72B sharded `-ts 28,28,24`), 8082 (Linux Gemma 9B), 8083 (BioMistral DSP), 8084 (Qwen2.5-VL-7B, 48.3 tok/s), and 8080 (Tier-0 OpenWrt Gateway).
4. **Local vs Cloud Prioritization:** Free cloud quotas (Julien AI: 300/day, Cloudflare: 1,000/day, Gemini Free: 1,500/day) are harvested as Teacher models for complex macro-architecture and whole-repo context (>50k tokens), with results immediately distilled into local datasets. High-frequency, latency-sensitive (<200ms), privacy-bound, and continuous background tasks default to $0-cost local mesh execution.
5. **Quota Manager Upgrades Needed:** `cloud_api_quota_manager.py` currently contains in-memory mocks. It requires state persistence (`cloud_api_quota_state.json`), mathematical routing heuristics (remaining quota %, context length, speed/TPS, privacy flag), live API execution with Teacher distillation recording, and automatic fallback to local mesh RPC when quotas deplete.

---

## 2. LoRA Distillation Dataset Architecture & Schemas

### 2.1 File Catalog & Domain Partitioning
The directory `/Users/aaron/DFS_UNIFIED/lora_datasets/` and `04_data_and_memory/lora_datasets/` maintain domain-segregated JSONL datasets:

| Dataset File | Primary Schema | Domain / Purpose | Size / Activity |
| :--- | :--- | :--- | :--- |
| `truth_audit_debate.jsonl` | Instruction-Thought-Output | Multi-orchestrator architectural debate consensus | Active (Continuous) |
| `continuous_master_agi_distillation.jsonl` | ChatML `messages` array | 3-way tournament traces (Jules, Gemini Flash, Local Master) | Active |
| `free_tier_harvest.jsonl` | Prompt-Model metadata | Cloud quota harvest log (Shopify, ad generation, refactors) | Active |
| `dpo_router_orchestrator_pairs.jsonl` | DPO `prompt/chosen/rejected` | Direct Preference Optimization for routing & storage physics | 28.6 KB (19 pairs) |
| `sft_router_orchestrator_debate.jsonl` | ChatML `messages` array | Multi-round debate transcripts on router architecture | 18.8 KB (9 rounds) |
| `continuous_lora_dataset.jsonl` | Prompt-Completion | Master 24/7 dataset for `train_mesh_lora.py` SFT | 69.5 MB |
| `device_doctor_telemetry.jsonl` | Instruction-Thought-Output | Real hardware syscalls & OS storage advice | Active |
| `movesense_biometrics_coaching.jsonl` | Instruction-Thought-Output | 128Hz ECG, DFA-alpha1, IMU physiological coaching | Active |
| `swarm_codebase_refactors.jsonl` | Instruction-Thought-Output | Verified AST mutations & zero-mock refactors | Active |
| `cron_governor_decisions.jsonl` | Alpaca Decision Record | Autonomous cron ROI calculation & cadence decisions | Active |
| `tiered_router_decisions.jsonl` | Routing Decision Payload | 8-pillar task routing decisions & fallback logs | Active |
| `on_device_nano_smol_training.jsonl` | Instruction-Thought-Output | Gemini Nano TPU vs SmolLM2-135M benchmarks | Active |

---

### 2.2 Detailed JSONL Schema Specifications

#### Schema A: Alpaca-Style Instruction-Thought-Output (Canonical Supervised Distillation)
Used across debate daemons, biometrics engines, and codebase refactor harvesters. Implements strict Rule #0 anti-simulation metadata.
```json
{
  "instruction": "Perform Tri-Orchestrator AI Debate on project topic: 'Host Storage Headroom Governance'",
  "input": "{\"debate_id\": \"DEBATE_LORA_1787764692_451\", \"topic\": \"Host Storage Headroom Governance\", \"context\": \"Mac Host storage is constrained...\", \"perspectives\": {\"gemini_37_flash\": \"...\", \"local_ai_mesh\": \"...\", \"genetic_moe\": \"...\"}}",
  "thought": "[Turn 1] Cloud Orchestrator analyzed architectural invariants... [Turn 2] Local AI Mesh Orchestrator evaluated hardware feasibility... [Turn 3] Genetic MoE evaluated token economy... [Turn 4] Lead Synthesis established consensus...",
  "output": "Consensus Reached: Enforce zero-copy symlinking and dynamic offload to NAS Model Hub. (Tri-Orchestrator Certified, 0 Fake Data, 0 Hallucinations).",
  "timestamp": "2026-08-27T06:17:00Z",
  "timestamp_utc": "2026-08-27T06:17:00Z",
  "real_data_certified": true,
  "source_data_origin": "100%_REAL_PHYSICAL_HARDWARE",
  "air_gap_simulation_quarantine": true
}
```

#### Schema B: Multi-Turn ChatML Schema (`messages` Array)
Used in `continuous_master_agi_distillation.jsonl` and `sft_router_orchestrator_debate.jsonl` for multi-role agent training (system, user, assistant).
```json
{
  "timestamp": 1787764692.1007302,
  "domain": "DOM_01_BIOMETRICS_PHYSIOLOGY",
  "tournament_task": "Web Bluetooth Movesense 128Hz GATT Heart Rate & ECG Service",
  "models_evaluated": ["jules_gemini_31_pro", "gemini_37_flash", "local_master_smolagent"],
  "winner": "local_master_smolagent + gemini_37_flash",
  "messages": [
    {
      "role": "system",
      "content": "You are the Lauburu Master Local AGI Model specializing in biomedical DSP & Web Bluetooth GATT architectures."
    },
    {
      "role": "user",
      "content": "Implement a high-performance Web Bluetooth API service and React hook for Movesense HR+ strap with GATT parsing..."
    },
    {
      "role": "assistant",
      "content": "Implemented MovesenseBleService with 0x180D Heart Rate measurement parser..."
    }
  ]
}
```

#### Schema C: Direct Preference Optimization (DPO) Pair Schema
Used in `dpo_router_orchestrator_pairs.jsonl` for mathematical alignment and fine-tuning with Hugging Face `TRL` (DPOTrainer).
```json
{
  "prompt": "How should a distributed 7-layer AI mesh coordinate intermediate activation tensor sharding during 128K context window prefill across heterogeneous nodes?",
  "chosen": "In a 7-layer heterogeneous mesh, intermediate activation tensors during 128K context prefill MUST strictly bypass the 1Gbps switched router LAN and transfer point-to-point over dedicated 10Gbps Thunderbolt 4 (TB4) PCIe DMA interconnects...",
  "rejected": "The OpenWrt router should act as the central hub for all distributed network traffic, including tensor sharding. By routing all intermediate layer activation tensors through the router's 1Gbps LAN switch...",
  "metadata": {
    "category": "multi_path_interconnect_physics",
    "consensus_score": 0.99994,
    "dimension": "V2_multi_path_physics",
    "source": "tri_orchestrator_debate_round_2_3"
  }
}
```

#### Schema D: Standard SFT Prompt-Completion Schema
Used in `scripts/train_mesh_lora.py` with `SFTConfig(dataset_text_field="completion")`.
```json
{
  "prompt": "Generate thorough E2E test verification for movesense GATT subscription",
  "completion": "def test_movesense_gatt_subscription():\n    service = MovesenseBleService()\n    assert service.connect()\n    ..."
}
```

---

## 3. Local Training, Batch Generation & Inference Endpoints

### 3.1 Local Training Frameworks & Trigger Scripts

1. **Hugging Face PEFT & TRL SFT Pipeline (`scripts/train_mesh_lora.py`):**
   - **Engine:** PyTorch + Hugging Face `transformers`, `peft` (`LoraConfig`), `trl` (`SFTTrainer`, `SFTConfig`).
   - **Base Model:** `Qwen/Qwen2.5-Coder-7B-Instruct` in 4-bit quantization.
   - **LoRA Configuration:** `r=8, lora_alpha=16`, targeting attention projection matrices `["q_proj", "v_proj", "k_proj", "o_proj"]`, `learning_rate=2e-4`, `max_seq_length=1024`.
   - **Target Output:** `02_ai_models_and_inference/mesh_lora_checkpoints/mesh_healer_lora_final`.
2. **PEFT to GGUF Adapter Converter (`02_ai_models_and_inference/llama_cpp/convert_lora_to_gguf.py`):**
   - Directly converts PyTorch/PEFT `adapter_model.safetensors` into GGUF LoRA format (`.gguf`) compatible with `llama.cpp` (`--lora` / `--lora-scaled`).
3. **Continuous AI Debate & Distillation Daemon (`00_core_infrastructure/self_healing_hub/src/continuous_training_debate_daemon.py`):**
   - Autonomous background loop generating rich 4-turn debate records across 7 architectural topics.
   - Dual serialization: Local JSONL + Google Drive VFS sync.
4. **NPU-Accelerated Multi-Stream Harvester (`00_core_infrastructure/self_healing_hub/src/npu_training_harvesting_engine.py`):**
   - Governs 121 TOPS on-device NPU cluster (Apple ANE 38 TOPS, Tensor G5 TPU 22 TOPS, Qualcomm Hexagon 45 TOPS, AMD XDNA 16 TOPS).
   - Collects 4 empirical data streams (Hardware Syscalls, Sanitized User Chat, Movesense 128Hz DSP, Codebase Refactors).
5. **On-Device Nano & Smol Trainer (`00_core_infrastructure/self_healing_hub/src/on_device_nano_smol_trainer.py`):**
   - Benchmarks Gemini Nano (Edge TPU) and SmolLM2-135M (Samsung S20+ Termux) across GATT deserialization, AST repair, and UI auditing.
6. **Shadow Coding Tournament Engine (`05_agents_and_swarms/local_agi_smolagent/shadow_benchmark_engine.py`):**
   - Triggers Google Jules CLI (`npx -y @google/jules new --repo ...`), compares with Gemini 3.7 Flash and Local Master Smolagent, recording winner outcomes.

---

### 3.2 Physical Mesh Inference Ports & RPC Endpoints

| Port | Protocol / Path | Primary Model / Engine | Node / Hardware | Bandwidth / Latency |
| :--- | :--- | :--- | :--- | :--- |
| **8080** | HTTP / REST Reverse Proxy | Tier-0 OpenWrt Reverse Proxy | GL.iNet Gateway Router | 1Gbps LAN (<1.0ms) |
| **8081** | HTTP / OpenAI `/v1` | Nous Hermes 3 8B (MCP Function Specialist) | L1 Mac Mini M4 Pro | Local Socket (<0.1ms) |
| **50052** | TCP / llama.cpp RPC | Kimi Tandem / Qwen 2.5 72B (`-ts 28,28,24`) | L1 Mac Mini + L2 MBP + L3 Linux | **10Gbps TB4 DMA (0.277ms)** |
| **8082** | HTTP / REST `/v1` | Gemma-2-9B-Q4_K_M / Qwen 3.8 Max | L3 Linux Head Node (Ryzen 7) | 2.5GbE LAN (0.85ms) |
| **8083** | HTTP / REST `/v1` | BioMistral-7B (Pan-Tompkins DSP) | L3 Linux Head Node | 2.5GbE LAN (0.85ms) |
| **8084** | HTTP / REST `/v1` | Qwen2.5-VL-7B (Vision Grounding, 48.3 tok/s) | L5 MacBook Air M4 Metal | Wi-Fi 7 / LAN (1.2ms) |
| **8750** | HTTP `/v1/slice` | PySpark AST Context Slicer & Lakehouse | L3 Linux Head Node | Local / LAN |
| **8265** | HTTP / Ray Dashboard | Ray Distributed Multi-Node Actors | L3 Linux Head Node | Cluster Interconnect |
| **18789** | WebSocket `ws://` | OpenClaw Local Headless VLM | L3 Linux Head Node | LAN (0.27ms) |
| **18802** | HTTP REST API | Wake-on-LAN Hardware Resurrection API | L1 Mac Mini / Hub | Local Socket |

---

## 4. Local Mesh vs Cloud Quotas: Prioritization & Fallback Heuristics

### 4.1 Quota Optimization & Task Specialization Matrix

```
                          ┌──────────────────────────────────────────────────┐
                          │               INCOMING AI TASK                   │
                          └─────────────────────────┬────────────────────────┘
                                                    │
                   ┌────────────────────────────────┴────────────────────────────────┐
                   ▼                                                                 ▼
      [Task Attributes Check]                                           [Task Attributes Check]
      • Context > 50,000 tokens                                         • Latency-sensitive (<200ms)
      • Macro Architecture / Formal CoT Proof                           • Real-time Biometrics / 128Hz DSP
      • Cross-repo Whole-AST Invariants                                 • AST Refactoring & Syntax Verification
      • Cloud Quotas Available (>0%)                                    • Privacy-sensitive / Local Credentials
                   │                                                    • 24/7 LoRA Fine-Tuning Loop
                   ▼                                                                 │
    ┌─────────────────────────────┐                                                  ▼
    │   FREE CLOUD AI HARVEST     │                                   ┌─────────────────────────────┐
    ├─────────────────────────────┤                                   │     SOVEREIGN LOCAL MESH    │
    │ 1. Julien AI (300/day):     │                                   ├─────────────────────────────┤
    │    Multi-repo coding agents │                                   │ 1. Port 50052: Kimi Tandem  │
    │ 2. Cloudflare (1,000/day):  │                                   │    72B (TB4 DMA 0.277ms)    │
    │    Telemetry summarization  │                                   │ 2. Port 8084: Qwen2.5-VL-7B │
    │ 3. Gemini Free (1,500/day): │                                   │    (48.3 tok/s visual audit)│
    │    Strategic planning & CoT │                                   │ 3. Port 8081: Hermes 3 8B   │
    └──────────────┬──────────────┘                                   │ 4. Port 8083: BioMistral DSP│
                   │                                                  └──────────────┬──────────────┘
                   ▼                                                                 │
      [TEACHER-STUDENT DISTILLATION]                                                 │
      Cloud output captured as high-quality                                          │
      Instruction-Thought-Solution pair                                              │
                   │                                                                 │
                   └───────────────────────────────┬─────────────────────────────────┘
                                                   ▼
                                 ┌───────────────────────────────────┐
                                 │   24/7 LoRA DATASET PERSISTENCE   │
                                 │  /Users/aaron/DFS_UNIFIED/        │
                                 │  lora_datasets/                   │
                                 └───────────────────────────────────┘
```

### 4.2 Mathematical Routing Heuristics for Quota Manager

To self-optimize task distribution across free cloud AI quotas and local mesh compute, `cloud_api_quota_manager.py` should implement the following heuristic scoring function:

For a task $T$ with context size $C(T)$ tokens, latency tolerance $L(T)$ ms, and privacy constraint $P(T) \in \{0, 1\}$:

$$S_{\text{provider}} = w_Q \cdot Q_{\text{rem}}\% + w_S \cdot \text{TPS}_{\text{norm}} + w_C \cdot \text{Fit}_{\text{context}} - w_P \cdot P(T)$$

Where:
- $Q_{\text{rem}}\% = \frac{\text{Quota}_{\text{limit}} - \text{Quota}_{\text{used}}}{\text{Quota}_{\text{limit}}}$ (Remaining daily quota fraction)
- $\text{TPS}_{\text{norm}} = \frac{\text{TokensPerSec}}{200.0}$ (Provider throughput normalized)
- $\text{Fit}_{\text{context}} = \min\left(1.0, \frac{\text{MaxContext}}{C(T)}\right)$
- If $P(T) = 1$ (private biometric/credential data), cloud score becomes $-\infty$, forcing Local Mesh.

### 4.3 Multi-Tier Fallback Cascade

1. **Tier 0 (Free Cloud Quota):** Primary candidate selected via highest heuristic score among providers with $Q_{\text{rem}} > 0$.
2. **Tier 1 (Cloud Exhaustion / Rate Limit / Timeout):** Immediate sub-200ms failover to **Local Sovereign Titan** (Kimi Tandem 72B sharded on Port 50052 over 10Gbps TB4 DMA Bridge).
3. **Tier 2 (Heavy Node Disconnected):** Standalone local models (Linux Gemma-2-9B on Port 8082, Qwen2.5-VL-7B on Port 8084, Hermes 3 on Port 8081).
4. **Tier 3 (Edge Mobile Survival Mode):** On-device Edge TPU / Termux models (Gemini Nano / SmolLM2-135M) for essential socket keepalive and syntax repairs.
5. **Tier 4 (Paid Cloud Fallback):** Strictly throttled emergency fallback, invoked only when local nodes are offline and free quotas are exhausted.

---

## 5. Target Directories & Dataset Persistence Schemas

### 5.1 Canonical Directory Hierarchy

```
/Users/aaron/DFS_UNIFIED/
├── lora_datasets/                                    # Canonical Active LoRA Data Lake (Primary Write Target)
│   ├── continuous_master_agi_distillation.jsonl     # ChatML multi-turn distillation traces
│   ├── free_tier_harvest.jsonl                       # Cloud quota harvest log
│   ├── truth_audit_debate.jsonl                      # Multi-orchestrator architectural debate records
│   ├── dpo_router_orchestrator_pairs.jsonl           # DPO preference pairs (prompt/chosen/rejected)
│   ├── sft_router_orchestrator_debate.jsonl          # SFT debate transcripts
│   └── continuous_lora_dataset.jsonl                 # Master SFT training corpus
└── Lauburu-Monorepo/
    ├── 04_data_and_memory/
    │   ├── lora_datasets/                            # Monorepo mirror of lora_datasets/
    │   └── session_logs/
    │       ├── cloud_api_quota_state.json            # Persistent JSON tracking for Julien/Cloudflare/Gemini quotas
    │       └── master_cron_portfolio.json            # Cron execution ledger
    ├── data/
    │   ├── lora_datasets/                            # Local working directory for router & governor decisions
    │   └── gdrive_cache/Lauburu_AI_Memory/lora_datasets/ # Local VFS fallback when Google Drive is unmounted
    └── 06_scripts_and_tooling/automation/
        └── cloud_api_quota_manager.py                # Upgraded Quota Manager Cron Daemon
```

### 5.2 Target Dataset Schemas for Quota Manager Integration

#### 1. Free Tier Harvest Record (`free_tier_harvest.jsonl`)
Appended every time Julien AI, Cloudflare AI, or Gemini Free processes a task:
```json
{
  "timestamp": "2026-08-27T06:20:00.000000",
  "provider": "julien_ai",
  "model": "jules_gemini_31_pro",
  "task_type": "continuous_lora_distillation_batch",
  "prompt": "Synthesize 10-layer AST refactoring plan for 00_core_infrastructure",
  "response": "Refactoring plan synthesized with 0 syntax errors...",
  "tokens_in": 350,
  "tokens_out": 820,
  "latency_ms": 1420.5,
  "quota_remaining_pct": 87.3,
  "real_data_certified": true
}
```

#### 2. Master Distillation Pair (`continuous_master_agi_distillation.jsonl`)
Appended when cloud response provides a verified Teacher training sample:
```json
{
  "timestamp": 1787764800.0,
  "domain": "DOM_00_CORE_INFRASTRUCTURE",
  "tournament_task": "Cloud API Quota Self-Optimization Heuristic",
  "models_evaluated": ["julien_ai", "cloudflare_ai", "gemini_free", "local_mesh"],
  "winner": "julien_ai",
  "messages": [
    {
      "role": "system",
      "content": "You are the Lauburu Master Local AGI Model specializing in distributed multi-cloud quota optimization."
    },
    {
      "role": "user",
      "content": "How should free API quotas be scheduled against a 7-layer local AI mesh?"
    },
    {
      "role": "assistant",
      "content": "Free API quotas must be scheduled by evaluating daily remaining percentages against context requirements..."
    }
  ]
}
```

#### 3. Quota Tracking State (`cloud_api_quota_state.json`)
Persistent state written to `04_data_and_memory/session_logs/cloud_api_quota_state.json`:
```json
{
  "last_updated": "2026-08-27T06:20:00Z",
  "providers": {
    "julien_ai": {
      "limit": 300,
      "used": 14,
      "remaining": 286,
      "remaining_pct": 95.3,
      "reset_time": "2026-08-28T00:00:00Z",
      "tps": 45.0,
      "max_context": 100000
    },
    "cloudflare_ai": {
      "limit": 1000,
      "used": 85,
      "remaining": 915,
      "remaining_pct": 91.5,
      "reset_time": "2026-08-28T00:00:00Z",
      "tps": 120.0,
      "max_context": 32768
    },
    "gemini_free": {
      "limit": 1500,
      "used": 110,
      "remaining": 1390,
      "remaining_pct": 92.7,
      "reset_time": "2026-08-28T00:00:00Z",
      "tps": 185.0,
      "max_context": 1048576
    }
  },
  "local_mesh_fallback_count": 42,
  "total_lora_samples_harvested": 209
}
```

---

## 6. Recommendations for Implementation

1. **Persistent State Engine in `cloud_api_quota_manager.py`:**
   - Load and persist `cloud_api_quota_state.json` on every evaluation cycle so state survives daemon restarts.
   - Implement automatic daily reset logic based on UTC midnight.
2. **Dynamic Heuristic Task Router:**
   - Implement task classification: macro context / whole-repo -> Gemini Free / Julien; telemetry summaries / short tasks -> Cloudflare AI; real-time code synthesis & private biometrics -> Local Mesh.
   - Log explicit routing rationale: `[QuotaManager]: Routing task 'X' to Julien AI (Reason: High context fit, remaining quota 95.3% > threshold)`.
3. **Live Dataset Generation:**
   - On every executed task (cloud or local), construct a valid training record adhering to Schema A/B and append to `/Users/aaron/DFS_UNIFIED/lora_datasets/free_tier_harvest.jsonl` and `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_master_agi_distillation.jsonl`.
4. **Local Mesh Fallback Integration:**
   - When all cloud quotas are exhausted or when local compute is preferred, invoke local endpoints on Port 8081 or Port 50052, decrementing the local fallback counter and verifying zero unhandled exceptions.
5. **E2E Verification Suite:**
   - Implement a test harness that verifies:
     - Clear heuristic decision logging.
     - Accurate decrementing of quota state across Julien AI, Cloudflare, and Gemini.
     - Actual filesystem append to LoRA JSONL dataset files.
     - Full execution without unhandled exceptions.
