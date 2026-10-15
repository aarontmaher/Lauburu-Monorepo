---
title: Truth-Auditing Swarm Debate 2026-10-04
tags: [ai_debate, truth_audit, zero_mock]
---
# Truth-Auditing Swarm Debate (2 rounds, real models)
Links: [[Index]] [[FAKE_DATA_BOUNTY_LOG]]

## Participants (actual model per /props or agy model id)
- devils_advocate: `/home/linuxmini/model_vault_gguf/Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf` (FAILED: HTTP Error 400: Bad Request)
- judge_candidate: `/Users/aaron/.local/share/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf` (ok)
- lead_architect: `gemini-3.1-pro-high` (ok)
- bulk_engineer: `gemini-3.8-flash-high` (ok)
- open_weights_peer: `gpt-oss-120b-medium` (ok)
- synthesis: `gemini-3.1-pro-high` (agy exit 0)

## Raw transcript hashes
- round1.json: sha256 1d58d80f851427f0879d6422130e4d2664f549e4703fb81d8f4dfc180eba1577
- round2.json: sha256 8e5fe20189b7768ae8e00ad166b92161fe84a9d3ce5f8119b02575b71a1b215d
- synthesis.json: sha256 6a30fe64d14c3ef94a7505adc0ae2b40ac12998040a433a02eb2e9b726b2c6a5
- raw files: /Users/aaron/.gemini/antigravity/brain/0177d036-307b-49b9-b71b-5f435e97f9bf/scratch/truth_swarm_debate

## Synthesis (unedited Gemini 3.1 Pro output)

Here is the consensus design for the Truth-Auditing Swarm based on the multi-agent debate, synthesizing the physical hardware constraints of the Lauburu mesh and the Zero-Mock truth rules.

### 1. Swarm Roster & Roles with Model Files
To preserve the $\ge 4.8\text{ GB}$ sanctuary headroom on L1 (Mac Mini M4 Pro, 24 GB RAM), the swarm utilizes a strict hardware-anchored cascade. Heavy orchestration remains on L1, while high-volume token processing is offloaded to peripheral nodes.

*   **Tier 0: Numeric / Sensor Pre-Filter**
    *   **Model:** `nanometric_sentinel.pt` (53 KB MLP).
    *   **Location:** L1 CPU.
    *   **Role:** High-speed streaming anomaly detection for raw telemetry arrays. Bypasses LLM token generation entirely.
*   **Tier 1: Code Auditor (Specialist A)**
    *   **Model:** `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf` (or 3B).
    *   **Location:** Node L2 (Intel i7 MacBook Pro, 16 GB RAM) via 20 Gb/s Thunderbolt 4 bridge.
    *   **Role:** Single-file AST syntax parsing and detecting fabricated arrays in source code. Sits comfortably in L2's memory without starving the L1 host.
*   **Tier 2: Text / Log Auditor (Specialist B)**
    *   **Model:** `SmolLM2-1.7B` or `qwen2.5-1.5B`.
    *   **Location:** Node L3 (Ryzen 7 5700U, 15 GB RAM) via Tailscale / LAN.
    *   **Role:** Triage live API outputs, terminal text, and missing provenance logs.
*   **Tier 3: Vision / UI Cross-Reference (Screen Lens)**
    *   **Model:** `Qwen2.5-VL-7B-Instruct-Q4_K_M`.
    *   **Location:** Node L1 (Port 8081).
    *   **Role:** Visual grounding. Verifies what the UI actually renders against what the terminal logs claim. (Already resident in RAM; ~6.9 GB RSS).
*   **Tier 4: Sovereign Judge**
    *   **Model:** `Hermes-3-Llama-3.1-8B.Q4_K_M.gguf`.
    *   **Location:** Node L1 (Port 8090).
    *   **Role:** Adjudicates edge cases, assigns blame for complex logical hallucinations, and writes the final audit verdict.

### 2. The Hermes 3 vs. Hermes 4 Decision
**Decision: Hermes 3 8B.**
*   **Hardware Reality:** The L1 Mac Mini has 24 GB of Unified Memory. Currently, `Hermes-3-8B` consumes ~6.9 GB and `Qwen2.5-VL-7B` consumes ~6.9 GB, leaving ~10.2 GB. System daemons consume 2-3 GB (estimate), leaving ~7.2 GB (estimate) free. Rule 3 mandates maintaining $\ge 4.8\text{ GB}$ of free sanctuary RAM to prevent ACIO2 kernel panics.
*   **Why Hermes 4 14B Fails:** A 14B model quantized at Q4_K_M requires ~8.5 GB to ~12 GB (estimate) of memory. Loading Hermes 4 would breach the 4.8 GB barrier, triggering aggressive swap and zeroing out L1 performance.
*   **Why 27B Fails:** The `Huihui-Qwen3.8-27B` model requires ~22 GB VRAM (estimate). Loading this on L3 (15 GB total RAM) guarantees an immediate Out-Of-Memory (OOM) crash. Offloading it to the Pixel 10 Pro XL (Tensor G5) is physically impossible due to the Android AVF Debian microVM's hard limit of $\le 3.5\text{ GB}$ RAM residency (Rule 9).

### 3. Mathematically Verifiable ELO/Rating Spec
To prevent LLM sycophancy, collusion, and ELO-farming, the rating system must be mechanically anchored.
*   **Rating Algorithm:** Glicko-2. It tracks Rating Volatility ($\sigma$) and Rating Deviation ($\phi$), which is critical for new/untested sub-1B TinyLMs that lack historical accuracy data.
*   **Win Condition (Ground Truth):** A "Win" is **never** granted merely because two LLMs agree (which could just be latent pre-training collusion). A Win is strictly defined as **Mechanical Verification**:
    *   The model flags a bug, and `fake_data_scanner.py` runs and returns `Exit Code 0`.
    *   The model proposes a fix, and the unit test / compiler returns `Exit Code 0`.
*   **Anti-Gaming & Deduplication:** To prevent models from farming ELO by repeatedly reporting the same mock test file, all findings must pass an AST String Hash deduplicator (with whitespace normalization). Submissions matching existing hashes yield $0$ ELO. An explicit `.gitignore`-style whitelist must shield legitimate `tests/mocks/` from being flagged as "fabricated telemetry".
*   **Asymmetric Penalties (Bounty Ledger):**
    *   Verified True Positive: $+ \Delta$ Glicko-2 rating.
    *   Hallucinated Citation / False Positive: $- (2 \times \Delta)$ Glicko-2 rating (tax penalty).

### 4. Swarm Tiers Trial Plan and Throughput Budget
Because LLM throughputs are heavily bounded by I/O and RAM bandwidth, a cascading filter is required to prevent systemic bottlenecking. *(Note: Throughput numbers are marked as estimates to comply with the Zero-Mock rule until empirically benchmarked via continuous integration).*
*   **Tier 0 Cascade (CPU):** `nanometric_sentinel.pt` processes raw numeric streams at ~1-2 kHz (estimate). It drops 99% of normal data.
*   **Tier 1 & Tier 2 Cascade (L2/L3):** MiniLMs (1.5B–3B) process the flagged anomalies. Expected throughput: ~1-10 files/minute (estimate) due to Thunderbolt/Tailscale RPC network overhead and CPU/Metal inference limits.
*   **Tier 3 Adjudication (L1):** `Hermes-3-8B` is only invoked when Tier 1/2 raise a high-confidence alert that requires complex reasoning. Expected throughput: $< 1$ file/minute (estimate).
*   **Tier 4 Cloud Escalation:** Gemini API is used purely as a circuit breaker for deadlocked local debates, paced strictly at ~3.68 RPM (Rule 6).

### 5. Points of Unresolved Disagreement
*   **Cross-Family Judge Independence:**
    *   *Position:* `lead_architect`, `open_weights_peer`, and `bulk_engineer` strongly argue that the Judge (Llama base) MUST be from a different pre-training family than the Detectors (Qwen base) to prevent latent model sycophancy (models from the same family sharing the same blindspots and mutually validating hallucinations).
    *   *Dissent:* `judge_candidate` argues this adds unnecessary complexity and that parameter size (8B vs 1.5B) matters more than base family.
*   **Throughput Delusions vs. Hardware Reality:**
    *   *Position:* `open_weights_peer` and `bulk_engineer` accuse the other agents of hallucinating throughputs (e.g., claiming 5,000 samples/s or 40 files/min) without profiling the PySpark overhead or L2's lack of a discrete GPU.
    *   *Dissent:* `judge_candidate` and `lead_architect` hold onto optimistic speeds based on parameter sizes alone, underestimating the bottleneck of SeaweedFS and distributed mesh latency.

### 6. Agreement Score Per Item
*   **Use Hermes-3-8B over Hermes-4-14B/27B due to strict L1 RAM (4.8 GB buffer) limits:** 4/4 (100%)
*   **Offload 1.5B–3B Detectors to Peripheral Nodes (L2/L3) to spare L1:** 4/4 (100%)
*   **Use Mechanical Execution (Exit Code 0) as Absolute Ground Truth over LLM Consensus:** 3/4 (75%) — Supported by `lead_architect`, `bulk_engineer`, `open_weights_peer`. `judge_candidate` slightly resisted but conceded to mechanical verification in their final round.
*   **Use Glicko-2 / Mathematical Script for Rating over arbitrary scores:** 3/4 (75%) — Supported by `judge_candidate`, `bulk_engineer`, `open_weights_peer`.
*   **Require Judge to be of a different Base Family (Llama) than the Detectors (Qwen):** 3/4 (75%) — Supported by `lead_architect`, `bulk_engineer`, `open_weights_peer`. Opposed by `judge_candidate`.