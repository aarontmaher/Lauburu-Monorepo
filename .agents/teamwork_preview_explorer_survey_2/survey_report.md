# Technical Survey Report: LoRA Dataset Harvesting, AST Optimization & Local Metal GPU Training (Requirement R2)

**Author:** `teamwork_preview_explorer_survey_2` (Teamwork Explorer)  
**Date:** 2026-08-29  
**Subsystem Scope:** Requirement R2 (Continuous Multi-Model LoRA Dataset Harvesting & Model Merging), Tri-Vault Logging, AST Code Extraction, Apple Silicon Metal Training, and Weight Fusion  
**Working Directory:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_2/`

---

## Executive Summary

This survey provides an exhaustive technical inventory and architectural assessment of the continuous 24/7 LoRA dataset harvesting pipelines, AST code optimization crawlers, local Apple Silicon Metal GPU training runtimes (PEFT / TRL / MLX), loss curve logging in Obsidian Vault, and autonomous model weight merging engines in the Lauburu Monorepo. 

Key high-level findings include:
1. **Active Data Lake Ingestion**: The ecosystem hosts **over 40 distinct `.jsonl` dataset collections** across `/Users/aaron/DFS_UNIFIED/lora_datasets/`, `04_data_and_memory/`, and `12_continuous_lora_evolution/`, totaling **>400,000 empirical training samples** (including 210K+ truth audit debates, 145K+ biometrics coaching samples, and 14.7K+ continuous multi-domain LoRA pairs).
2. **Standardized Dual Schemas**: Harvesting supports both HuggingFace TRL DPO pair format (`prompt`, `chosen`, `rejected`, `meta`) and multi-turn SFT / ShareGPT format (`instruction`, `thought`, `output`, `messages`). All data is strictly validated against **Rule #0 Zero-Mock Data Invariants** with cryptographic SHA-256 and Delta Lake PyArrow schema enforcement.
3. **Daily $\ge 500$ Verified Pair Harvest Rate**: Automated continuous daemons (`continuous_training_debate_daemon.py`, `npu_training_harvesting_engine.py`, `free_tier_ai_continuous_cron.py`, and `autonomous_math_trend_optimizer.py`) harvest from 4 empirical sources: 4-round Tri-Orchestrator debate transcripts, 3,679-file PySpark AST extractions, Qwen-Math closed-form RAM/loss proofs, and self-healing recovery actions.
4. **Dual Apple Silicon Metal GPU Training Engine**: On-device fine-tuning is implemented via **Apple MLX QLoRA** (zero-copy unified memory @ 273 GB/s bandwidth on M4 Pro / M4 Air) and **PyTorch MPS + HuggingFace PEFT / TRL `SFTTrainer`** (`r=64`, `alpha=128`, `fp16=True`, `dataloader_num_workers=0`). Dynamic RAM governors cap Host M4 Pro VRAM at $\le 21.6\text{ GB}$ (90%) and enforce thermal/battery cutoffs.
5. **Obsidian Vault & Model Merging**: Loss trajectories ($L(t) = 0.42 + 1.76 \cdot e^{-0.0008t}$) are live-streamed to `obsidian_vault/04_ANALYTICS/QWEN_MATH_CONTINUOUS_OPTIMIZATION_TRENDS_2026.md`. Autonomous consensus merging (`autonomous_consensus_merger.py` and `mergekit_optuna_genetic_engine.py`) triggers at $>0.95$ consensus, synthesizing MergeKit `SPARSE_MOE_DARE_TIES` / `SLERP` recipes while strictly preserving parent model weights.

---

## 1. Inventory & Architecture of `/Users/aaron/DFS_UNIFIED/lora_datasets/` & `04_data_and_memory/`

### 1.1 Physical Storage Topology & Tri-Vault Synchronization
The data storage architecture adheres to the Canonical Tri-Vault Storage Rule:
- **Layer 1: Local NVMe Fast Sync (`/Users/aaron/DFS_UNIFIED/lora_datasets/`)**: Fast, zero-latency dataset generation used directly by local training loops.
- **Layer 2: Monorepo Central Data Store (`04_data_and_memory/`)**: Master data lake housing AST indexes, preference pairs, Delta Lake tables, and session ledgers.
- **Layer 3: Google Drive VFS Mirror (`/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets/`)**: Hourly synced cloud backup maintained at $0 recurring spend via native macOS mount and fallback caching.

### 1.2 Master Dataset Catalog & Empirical Counts

| Dataset Filename | Location | Record Count | File Size | Primary Domain & Task Type |
| :--- | :--- | :--- | :--- | :--- |
| `continuous_lora_dataset.jsonl` | `/lora_datasets/` | **14,721** | 105.09 MB | Multi-domain DPO / SFT training pairs across 7 agent domains |
| `truth_audit_debate.jsonl` | `/lora_datasets/` & `04_data/` | **2,330** (Active) / **210,113** (Archive) | 10.73 MB / 160.4 MB | Tri-Orchestrator 4-round debate transcripts & consensus proofs |
| `movesense_biometrics_coaching.jsonl` | `/lora_datasets/` | **12,457** (Active) / **145,949** (Archive) | 12.75 MB / 116.0 MB | 512Hz ECG, Pan-Tompkins QRS, DFA-$\alpha_1$, and Zone 2 coaching |
| `lmarena_human_preference_pairs.jsonl` | `04_data_and_memory/` | **12,075** | 5.57 MB | Human preference comparison pairs across model tiers |
| `truth_audit_storage_2026.jsonl` | `/lora_datasets/` | **5,155** | 3.38 MB | Storage headroom audits, NVMe lifecycle, and symlink proofs |
| `anti_lag_stability.jsonl` | `/lora_datasets/` | **2,232** | 1.91 MB | 120 FPS WebGPU frame latency, circular ring buffer telemetry |
| `channel_bonding_trajectories.jsonl` | `/lora_datasets/` | **2,191** | 2.65 MB | 44-byte Speedify wire framing & TB4 DMA packet striping |
| `antigravity_sdk_lora.jsonl` | `/lora_datasets/` | **2,023** | 53.61 MB | Antigravity 2.0 SDK tool-calling, multi-agent coordination |
| `3d_spatial_instructional_map_lora.jsonl`| `/lora_datasets/` | **1,959** | 1.44 MB | 955-node OPML spatial trees & 3D biomechanical kinematics |
| `glinet_luci_dev_training.jsonl` | `/lora_datasets/` | **1,000** | 2.95 MB | OpenWrt / LuCI POSIX micro-daemon & SQM fq_codel rules |
| `router_telemetry.jsonl` | `/lora_datasets/` | **1,064** | 5.46 MB | GL-MT3600BE live RAM / CPU / interface telemetry |
| `ancestral_tool_memory.jsonl` | `/lora_datasets/` | **822** | 0.79 MB | Tool execution success rates, vulnerability discovery |
| `devils_advocate_training.jsonl` | `/lora_datasets/` | **398** | 0.88 MB | Adversarial stress testing, token economy critique |
| `dpo_router_orchestrator_pairs.jsonl` | `/lora_datasets/` & `04_data/` | **21** (Active) / **18** (Sink) | 0.03 MB | HuggingFace TRL DPO pair records from blind grading |
| `sft_router_orchestrator_debate.jsonl` | `/lora_datasets/` & `04_data/` | **12** (Active) / **8** (Sink) | 0.03 MB | Multi-turn ShareGPT system-user-assistant SFT instructions |
| `ai_training_game_dataset.jsonl` | `04_data_and_memory/` | **1** | 479 bytes | Smolagents duel state next-action prediction format |
| `qwen_math_optimization_trends.jsonl` | `04_data_and_memory/` | Continuous stream | Variable | Closed-form RAM headroom equations & loss projections |

### 1.3 Delta Engine Storage & Schema Layer (`04_data_and_memory/delta_engine/`)
To support high-throughput ACID transactions and memory-mapped loading over the 10Gbps Thunderbolt 4 bridge, the repository implements `delta_engine/`:
- **`schema.py`**: Defines Apache PyArrow schemas (`TRUTH_AUDIT_ARROW_SCHEMA`, `SFT_TRAINING_ARROW_SCHEMA`, `DPO_PREFERENCE_ARROW_SCHEMA`, `MESH_TELEMETRY_ARROW_SCHEMA`, `WEARABLES_TELEMETRY_ARROW_SCHEMA`).
- **`writer.py`**: Thread-safe Delta Lake writer with schema enforcement and atomic commits.
- **`compactor.py`**: Bin-packing micro-compaction of small JSONL records into optimized Parquet files.
- **`mmap_loader.py`**: Zero-copy HuggingFace `datasets` memory-mapped dataset loader for instantaneous multi-GPU consumption without memory duplication.

---

## 2. Dataset Formats, Schemas, Validation & Daily Harvesting Mechanism

### 2.1 Schema Specifications

#### Schema A: Hugging Face DPO Pair Format (TRL `DPOTrainer` Compliant)
Used in `continuous_lora_dataset.jsonl`, `dpo_router_orchestrator_pairs.jsonl`, `ai_training_game_dataset.jsonl`:
```json
{
  "trial_id": "trial_5f9a2b8e1c0d",
  "timestamp": "2026-08-29T10:30:00Z",
  "domain": "continuous_ai_arena_tournament",
  "task_type": "tri_orchestrator_blind_debate",
  "prompt": "Analyze GL.iNet router MemAvailable at 88.5MB with MT798x Wi-Fi 7 drivers. Determine safe onboard AI footprint.",
  "chosen": "Winner (qwen_38_max_flagship [Alias alpha]): Deploy a 1.8MB POSIX micro-daemon directly on OpenWrt to enforce SQM fq_codel, while offloading the 31.9MB Canonical TUI to Host Mac Mini.",
  "rejected": "Sub-optimal reasoning solution (Competitor: command_r_plus_104b) rejected by Tri-Orchestrator Judicial Council. Failed on AST syntax precision, reasoning depth, or token economy.",
  "meta": {
    "winner": "qwen_38_max_flagship",
    "winner_alias": "alpha",
    "loser_ids": ["command_r_plus_104b"],
    "total_scores": {"alpha": 96.95, "beta": 93.65, "gamma": 92.70},
    "scores": {
      "alpha": {"syntax": 98.0, "depth": 95.0, "economy": 96.0, "safety": 100.0, "truth": 100.0}
    },
    "zero_mock_certified": true,
    "truth_verified": true,
    "truth_compliance_pct": 100.0
  }
}
```

#### Schema B: ShareGPT / Multi-Turn SFT Format (TRL `SFTTrainer` Compliant)
Used in `sft_router_orchestrator_debate.jsonl`, `truth_audit_debate.jsonl`, `agentworld_stage1_training.jsonl`:
```json
{
  "trial_id": "trial_5f9a2b8e1c0d",
  "timestamp": "2026-08-29T10:30:00Z",
  "instruction": "Perform a high-level technical evaluation for the prompt: Analyze GL.iNet router MemAvailable...",
  "input": "Analyze GL.iNet router MemAvailable at 88.5MB...",
  "thought": "1. Blind participant responses received and stripped of headers.\n2. Frontier Judge verified AST structural integrity.\n3. Swarm Judge evaluated reasoning depth.\n4. Devil's Advocate tested boundary conditions.\n5. Consensus outcome: qwen_38_max_flagship proved mathematically superior.",
  "output": "Consensus Reached: Enforce 1.8MB POSIX daemon on router; offload TUI to Mac Host.",
  "messages": [
    {
      "role": "system",
      "content": "You are the Tri-Orchestrator AI Debate Council governing the Lauburu 7-Layer Mesh Network. Deliver verified, zero-mock technical solutions."
    },
    {
      "role": "user",
      "content": "Analyze GL.iNet router MemAvailable at 88.5MB..."
    },
    {
      "role": "assistant",
      "content": "<thought>\n1. Blind participant responses evaluated...\n</thought>\nConsensus Reached: Enforce 1.8MB POSIX daemon on router; offload TUI to Mac Host."
    }
  ],
  "metadata": {
    "winner_id": "qwen_38_max_flagship",
    "total_scores": {"alpha": 96.95},
    "truth_verified": true,
    "truth_compliance_pct": 100.0,
    "zero_mock_certified": true
  }
}
```

### 2.2 Validation Mechanisms & Invariant Verification
Dataset ingestion is protected by multiple programmatic gates:
1. **Rule #0 Zero-Mock Data Validator (`tri_vault_sink.py` § 78-126)**:
   - `verify_zero_mock_compliance(record)` verifies that `truth_verified != False`, `truth_compliance_pct == 100.0`, `prompt` is non-empty, `winner_id` is present, and latency/tokens are non-negative empirical values.
   - Any synthetic or fake records are immediately quarantined to `quarantine_anomalies.jsonl`.
2. **Storage Health & Headroom Verifier (`tri_vault_sink.py` § 132-192)**:
   - `check_storage_health()` writes a temporary probe file (`.health_check_<pid>_<timestamp>.tmp`) to test write permissions and verifies free disk space $\ge 5.0\text{ GB}$.
   - If the primary directory `/Users/aaron/DFS_UNIFIED/lora_datasets` is inaccessible, it automatically switches to `04_data_and_memory/lora_datasets/` or `lora_datasets_fallback/` without dropping records.
3. **Atomic POSIX Persistence**:
   - `atomic_write_file()` executes writes to a unique temporary file (`.tmp.<pid>.<tid>.<hex>`), flushes, calls `os.fsync()`, and applies `os.replace()` to ensure zero partial/corrupted records.
   - `safe_append_jsonl()` uses thread-safe reentrant locks (`threading.RLock`) and POSIX fsync.

### 2.3 Daily Harvesting Mechanisms ($\ge 500$ Verified Pairs Daily)
The pipeline aggregates $\ge 500$ verified pairs daily across four independent harvesting pipelines:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CONTINUOUS 24/7 DATASET HARVESTING PIPELINES                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. AI DEBATE TRANSCRIPTS (150–200 pairs/day)                                │
│    • Daemon: continuous_training_debate_daemon.py & continuous_arena_grader.py│
│    • Mechanism: 4-round debates evaluated by 3-Judge Council (Frontier,     │
│      Swarm, Devil's Advocate) scored across 5 pillars (Syntax, Depth,       │
│      Economy, Safety, Truth). Winners converted to DPO & SFT records.       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. AST CODE EXTRACTIONS & REFACTORS (150–200 pairs/day)                     │
│    • Daemon: deep_pyspark_network_project_analyser.py & Ray workers         │
│    • Mechanism: Traverses 3,679+ monorepo files (184.5K LOC), parses Python  │
│      ast.FunctionDef/ClassDef trees, extracts AST mutations and code diffs. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. MATHEMATICAL PROOFS & HARDWARE EQUATIONS (100–150 pairs/day)             │
│    • Daemon: autonomous_math_trend_optimizer.py (Port 8086 Qwen-Math)       │
│    • Mechanism: Computes closed-form RAM safety headroom (Headroom >= 2.5GB)│
│      and inverse-variance packet striping weights (TB4 97.5%, WG 2.1%).     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. RECOVERY ACTIONS & HARDWARE TELEMETRY (50–100 pairs/day)                 │
│    • Daemon: npu_training_harvesting_engine.py & sharded_training_supervisor│
│    • Mechanism: Real sys/ADB calls, battery thermal cuts, and Movesense     │
│      GATT biometrics formatted into instruction-thought-solution pairs.     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Local Metal GPU Training Scripts & Nightly Scheduling

### 3.1 Training Engine 1: Apple MLX QLoRA (`fast_train_agentworld_mac.py`)
- **Backend**: Apple MLX (`mlx_lm.lora`) utilizing unified zero-copy Metal memory @ 273 GB/s bandwidth.
- **Target Model**: `mlx-community/Qwen-AgentWorld-35B-A3B-4bit` (35B MoE Native World Model).
- **Hyperparameters**:
  - Batch Size: `2`
  - LoRA Rank: `32` (LoRA Layers: `16`)
  - Learning Rate: `1e-4` (scaled via $\eta = 10^{-4} \cdot \sqrt{\frac{\text{batch} \cdot \text{accum}}{4}}$)
  - Iterations: `500` (Stage 1 SFT on MCP + Terminal domains)
  - Memory Bandwidth: 273 GB/s (Apple M4 Pro unified memory)
  - Target Adapter Output: `02_ai_models_and_inference/lora_adapters/agentworld_35b`

### 3.2 Training Engine 2: PyTorch MPS + HuggingFace PEFT / TRL (`agentworld_train.py`)
- **Backend**: PyTorch MPS (`device = "mps"` on Apple Silicon Metal Performance Shaders).
- **Target Models**:
  - `huihui-ai/Huihui-Qwen3.8-27B-abliterated` (Port 8085, Q4_K_XL GGUF, best for terminal/mesh)
  - `Qwen/Qwen2.5-7B-Instruct` (Port 8086, Q4_K_M GGUF, fast iteration)
  - `Qwen/Qwen-AgentWorld-35B-A3B` (Port 8087)
- **PEFT LoRA Configuration**:
  ```python
  LoraConfig(
      r=64,
      lora_alpha=128,
      target_modules="all-linear",
      lora_dropout=0.05,
      bias="none",
      task_type="CAUSAL_LM",
  )
  ```
- **TRL SFT Configuration**:
  ```python
  SFTConfig(
      output_dir="02_ai_models_and_inference/lora_adapters/agentworld_abliterated_stage1",
      num_train_epochs=3,
      per_device_train_batch_size=1,
      gradient_accumulation_steps=8,
      learning_rate=2e-4,
      warmup_ratio=0.03,
      lr_scheduler_type="cosine",
      logging_steps=10,
      save_steps=100,
      save_total_limit=2,
      bf16=False,
      fp16=True,
      dataloader_num_workers=0,  # CRITICAL: Required for Apple MPS stability
      report_to="none",
      max_seq_length=2048,
  )
  ```

### 3.3 Hardware Governance & Dynamic RAM Allocation
During local training, `ShardedTrainingSupervisor` and `ElasticTrainingRAMGovernor` enforce strict dynamic limits across the 7-node mesh:
- **Host Mac Mini (M4 Pro, 24GB System RAM)**: AI VRAM cap $\le 21.6\text{ GB}$ (90% dynamic ceiling). Base model: 14.5 GB, KV Cache: 2.1 GB, Activation VRAM: 1.8 GB $\rightarrow$ **RAM Headroom $= 3.20\text{ GB} \ge 2.50\text{ GB}$** mandatory safety threshold.
- **MacBook Pro Worker (16GB RAM)**: AI VRAM cap $\le 14.0\text{ GB}$ (90%) over 10Gbps Thunderbolt 4 bridge (0.277ms RTT).
- **Linux Head Node (16GB RAM)**: AI VRAM cap $\le 13.8\text{ GB}$ (80%) for NVMe caching and Ray workers.
- **Mobile Nodes (Pixel 10 Pro XL / Samsung S20+)**: Capped at 70% capacity with hard thermal cutoff at $41^\circ\text{C}$ and battery discharge protection ($<25\%$).

### 3.4 Nightly Training Schedule & Execution
- **Cron Scheduling**: Governed by `06_scripts_and_tooling/automation/free_tier_ai_continuous_cron.py`:
  - **Tier 1 (1m)**: Real hardware router RAM + daemon watchdogs + SQM lock.
  - **Tier 2 (15m)**: Free-tier AI dataset harvesting (Gemini 2.5 Flash Free max 14 RPM + Cloudflare Workers AI + Local).
  - **Tier 3 (Daily 03:00 Off-Peak Window)**: Nightly QLoRA dataset aggregation, dataset compilation into `agentworld_mlx_train.jsonl`, execution of `fast_train_agentworld_mac.py`, adapter weight compilation, and ELO leaderboard update.
- **Audit Logging**: Every training session logs status to `agentworld_training_runs.jsonl` and Obsidian Vault.

---

## 4. Loss Curve Logging to Obsidian Vault & Model Weight Compilation/Merging

### 4.1 Loss Curve Modeling & Live Obsidian Synchronization
1. **Mathematical Loss Decay Formulation**:
   The loss trajectory is computed using the closed-form exponential decay model:
   $$L(t) = 0.42 + 1.76 \cdot e^{-0.0008 \cdot t}$$
   - Step 100: $L(100) = 2.0447$
   - Step 500: $L(500) = 1.5998$
   - Step 1000: $L(1000) = 1.2108$
   - Step 2500: $L(2500) = 0.6582$
   - Step 5000: $L(5000) = 0.4522$ (asymptotic floor $\approx 0.42$)
2. **Obsidian Vault Live Stream**:
   - `autonomous_math_trend_optimizer.py` continuously updates `obsidian_vault/04_ANALYTICS/QWEN_MATH_CONTINUOUS_OPTIMIZATION_TRENDS_2026.md` with:
     - Optimal TB4 / WireGuard / Wi-Fi 7 striping weights
     - RAM safety status (`CERTIFIED_HEALTHY (Headroom: 3.20 GB)`)
     - Projected loss at Step 1000 ($1.2108$)
     - Formal mathematical proof block and closed-form equations.
   - `tri_vault_sink.py` atomically writes Markdown debate transcripts with YAML frontmatter, 3-judge scoring breakdowns, and master Wikilinks (`[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`, `[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]`, `[[Index]]`) to `obsidian_vault/01_DEBATES/ARENA_TRIAL_{trial_id}.md`.

### 4.2 Autonomous Consensus Merging & Weight Compilation
Model compilation and genetic weight merging are governed by `autonomous_consensus_merger.py` and `mergekit_optuna_genetic_engine.py`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS MODEL MERGING ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. CONSENSUS EVALUATION (Threshold: score > 0.95)                           │
│    • Weights: Cloud (0.35), Local AI (0.35), Genetic MoE (0.30)             │
│    • If score > 0.95: Triggers merge pipeline.                              │
│    • If score <= 0.95: Rejection logged, zero weight modification.          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. MERGEKIT RECIPE SYNTHESIS (data/mergekit_recipes/)                       │
│    • Algorithms: SPARSE_MOE_DARE_TIES, SLERP_MANIFOLD_INTERPOLATION,        │
│      DARE_TIES_FUSION, PASSTHROUGH_STACKING.                                │
│    • Density scaling: density = 0.28 + (consensus - 0.95) * 0.4             │
│    • Weight scaling: weight = 0.85 + (consensus - 0.95) * 0.3               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. OFFSPRING MODEL ARTIFACT GENERATION (data/models/)                       │
│    • Generates specialized offspring GGUF / Safetensors model artifact      │
│      (e.g., Lauburu Offspring MoE: DeepSeek-R1-32B + Qwen-2.5-VL-30B).      │
│    • STRICT PARENT RETENTION: Verifies Parent 1 and Parent 2 remain intact  │
│      both before and after offspring artifact creation.                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. CANONICAL AI LEADERBOARD & TRACE REGISTRATION                            │
│    • Registers offspring in data/canonical_ai_leaderboard.json.             │
│    • Computes initial offspring ELO = max(P1_elo, P2_elo) + 15.             │
│    • Logs training trace to truth_audit_debate.jsonl.                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. OPTUNA BAYESIAN HYPERPARAMETER OPTIMIZATION                              │
│    • 28+ evaluated trials optimizing DARE density (0.20-0.38), router top-k,│
│      and SLERP gradient angles to evolve Pareto-optimal champions.          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Architectural Synthesis & Recommendations for Requirement R2 Implementation

Based on this comprehensive survey, the implementation of Requirement R2 (Continuous Multi-Model LoRA Dataset Harvesting & Model Merging) should adopt the following recommendations:

1. **Unify Dataset Entry Points via `TriVaultSink`**:
   - Route all debate transcripts, code diffs, math proofs, and recovery events through `TriVaultSink` (`04_data_and_memory/tri_vault_sink.py`), ensuring single-point Rule #0 validation, POSIX atomic appending, and synchronized Obsidian transcript creation.
2. **Standardize Target File for Daily Harvesting**:
   - Align primary aggregation to `04_data_and_memory/ai_training_game_dataset.jsonl` and `04_data_and_memory/lora_datasets/continuous_lora_dataset.jsonl`, maintaining the $\ge 500$ verified pairs daily acceptance criterion.
3. **Calibrate 24/7 Off-Peak Nightly Training Window**:
   - Schedule the nightly MLX/MPS QLoRA training run at `03:00 UTC` via `free_tier_ai_continuous_cron.py`, executing on the Host Apple M4 Pro / MacBook Air Metal GPU with batch size 2, rank 32, and dynamic RAM limit $\le 21.6\text{ GB}$.
4. **Automate Continuous Loss Curve Updates**:
   - Keep `autonomous_math_trend_optimizer.py` coupled with the cron heartbeat to continuously refresh loss projections in `obsidian_vault/04_ANALYTICS/QWEN_MATH_CONTINUOUS_OPTIMIZATION_TRENDS_2026.md`.
5. **Enforce Strict Parent Retention in Weight Merging**:
   - Maintain the dual-verification invariant in `autonomous_consensus_merger.py` ensuring base GGUF/Safetensors weights are never deleted during MergeKit fusion.

---

## 6. Artifact & File Reference Index

| File Path | Purpose |
| :--- | :--- |
| `04_data_and_memory/tri_vault_sink.py` | Canonical Tri-Vault logging engine (DPO/SFT/Chat/Obsidian) |
| `04_data_and_memory/fast_train_agentworld_mac.py` | Apple Silicon MLX QLoRA fast training orchestrator |
| `04_data_and_memory/agentworld_train.py` | PyTorch MPS + HuggingFace PEFT / TRL SFT training pipeline |
| `02_ai_models_and_inference/quantum/autonomous_math_trend_optimizer.py` | Qwen-Math RAM headroom proofs & loss curve forecasting |
| `00_core_infrastructure/self_healing_hub/src/autonomous_consensus_merger.py` | Autonomous model merge engine with parent retention |
| `00_core_infrastructure/self_healing_hub/src/mergekit_optuna_genetic_engine.py` | Optuna Bayesian TPE hyperparameter optimizer for MergeKit |
| `00_core_infrastructure/self_healing_hub/src/continuous_training_debate_daemon.py` | 24/7 debate harvesting daemon logging to JSONL |
| `00_core_infrastructure/self_healing_hub/src/npu_training_harvesting_engine.py` | 4-stream real-data hardware harvester and NPU governor |
| `00_core_infrastructure/self_healing_hub/src/sharded_training_supervisor.py` | Multi-device thermal/battery safety supervisor |
| `00_core_infrastructure/self_healing_hub/src/deep_pyspark_network_project_analyser.py`| PySpark AST codebase crawler & training pair generator |
| `06_scripts_and_tooling/automation/free_tier_ai_continuous_cron.py` | 3-tier multi-rate cron scheduler & quota enforcer |
| `04_data_and_memory/delta_engine/schema.py` | PyArrow & Delta Lake schema definitions |
| `obsidian_vault/04_ANALYTICS/QWEN_MATH_CONTINUOUS_OPTIMIZATION_TRENDS_2026.md` | Live mathematical loss curve and RAM headroom document |
| `obsidian_vault/01_DEBATES/` | Master directory for Obsidian Markdown debate transcripts |
