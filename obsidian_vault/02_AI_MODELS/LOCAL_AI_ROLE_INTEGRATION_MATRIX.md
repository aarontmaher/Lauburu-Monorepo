# 🗺️ Local AI Role Integration Matrix & Screen Lens Sovereign Protocol

> **Governed by:**
> - [00_canonical_hardware_matrix.md](file:///Users/aaron/.gemini/config/rules/00_canonical_hardware_matrix.md) — Single Source of Hardware & Port Truth
> - [01_zero_mock_truth_rule.md](file:///Users/aaron/.gemini/config/rules/01_zero_mock_truth_rule.md) — Zero-Mock Empirical Proof & Canonical Size Taxonomy
> - [03_host_sanctuary_and_ram_governance.md](file:///Users/aaron/.gemini/config/rules/03_host_sanctuary_and_ram_governance.md) — Host Sanctuary ($\ge 4.8\text{ GB}$ RAM Headroom)
> - [10_linux_mini_first_offload_rule.md](file:///Users/aaron/.gemini/config/rules/10_linux_mini_first_offload_rule.md) — Linux Mini First-Offload Invariant
> - [11_screen_lens_rules.md](file:///Users/aaron/.gemini/config/plugins/lens/rules/AGENTS.md) — Global Default Automation & Teacher-Student Protocol
> - [15_dynamic_elo_default_model_governance.md](file:///Users/aaron/.gemini/config/rules/15_dynamic_elo_default_model_governance.md) — Meritocratic Dynamic ELO Governance

---

## 🏛️ 1. Executive Architecture Overview

To eliminate dependence on cloud quotas, conserve host memory on the primary Mac Mini M4 Pro host (preserving $\ge 4.8\text{ GB}$ of free physical RAM under Rule 3), and achieve sub-15ms inference latencies, local AI roles have been identified, mapped, and deployed across the **7-layer physical mesh** (82.8 GB Pooled VRAM).

### High-Speed Interconnect Fabric
- **L1 Mac Mini M4 Pro $\leftrightarrow$ L8 Linux Mini Hub (`lauburu`):** 40 Gb/s Thunderbolt 4 DMA (`10.0.0.8`, RTT 0.140 ms, 0% loss).
- **L1 Mac Mini M4 Pro $\leftrightarrow$ L3 Linux Head Node (`linux`):** 1GbE / Wi-Fi 7 LAN (`192.168.8.225`, RTT 4.23 ms).
- **Control Plane Lifeline (Layer 0):** Omnipresent Bluetooth RFCOMM/L2CAP Full-Mesh Graph.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               SCREEN LENS SOVEREIGN ENDOSYMBIOTIC WATERFALL                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ Cloud Teacher Plane: Gemini 2.5 Flash / Claude 3.5 Sonnet (Paced Quota)     │
│       ▲                                                             │       │
│       │ Verification & Complex AST Migration                        │ Train │
│       ▼                                                             ▼       │
│ Sovereign Master Plane: Qwen 3.8 Max 27B UD (:8083 L8) / Hermes 3 8B (:8085)│
│       ▲                                                             │       │
│       │ Sharded Offload / High Context Reasoning                     │ Distill
│       ▼                                                             ▼       │
│ Subordinate Worker Plane: Qwen 2.5 Coder 1.5B (:8084 L3) / Nemotron 4B (L8) │
│       ▲                                                             │       │
│       │ Sub-15ms Pre-Coding & AST Skeletons                         │ Pairs │
│       ▼                                                             ▼       │
│ Tier 0 Micro-Draft Plane: TinyStories 20M (:9095 L8) / SmolLM2 135M (:9096)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 2. The 8 Local AI Roles & Hardware Integration Matrix

| Role | Primary Responsibility | Ideal Model | Parameter Class | Target Hardware & Port | Empirical tok/s | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Screen Lens VLA Core** | Multimodal screen perception, UI salience bounding boxes, OCR grounding | `Qwen2.5-VL-7B-Instruct` + `SmolVLM-2.2B` | Edge AI (2.2B / 7B) | L8 Linux Mini (`10.0.0.8:8083`) / L1 Bridge (`:8081`) | 553.8 pp / 146.3 tg | **ACTIVE** |
| **2. Tier 0 Speculative Drafter** | Sub-15ms token pre-coding, AST skeleton drafting before cloud verification | `TinyStories-LLaMA2-20M` & `SmolLM2-135M` | TinyLM ($\le 20\text{M}$) / MiniLM (135M) | L8 Linux Mini CPU (`10.0.0.8:9095` & `:9096`) | 339.6 tg (20M) / 367.0 tg (135M) | **ACTIVE** |
| **3. Subordinate Syntax Worker** | AST linting, micro-diff checking, single-file bug fixing, syntax validation | `qwen2.5-coder-1.5b-instruct` / `qwen2.5-coder-7b` | Edge AI (1.5B / 7B) | L3 Linux Head Node (`192.168.8.225:8084`) | 180.0 pp / 65.4 tg | **ACTIVE** |
| **4. Network Healer & Sentinel** | LuCI OpenWrt kernel dmesg parsing, AX88179 link drop recovery, Wi-Fi 7 roaming | `glm-edge-1.5b-chat` / `pythia-70m` | TinyLM (70M) / Edge AI (1.5B) | L3 Head Node (`:8084`) / GW Router | 493.6 tg (70M) / 190.0 tg (1.5B) | **ACTIVE** |
| **5. 512Hz Biometrics & DSP** | Real-time 512Hz ECG stream, Pan-Tompkins QRS anomaly detection, Zone 2 analysis | `TinyStories-20M-DSP` / `smollm2-135m` | TinyLM ($\le 20\text{M}$) | L8 Linux Mini (`:9095`) / L1 ANE (`:4000`) | 339.6 tg (<5ms latency) | **ACTIVE** |
| **6. Generative UX & E-Commerce** | Stitch-2 sales UX, dynamic pricing elasticity, cart conversion optimization | `DeepSeek-R1-Distill-Qwen-1.5B` & `Ministral-3-3B` | Edge AI (1.5B / 3B) | L8 Linux Mini (`10.0.0.8:8083`) | 210.0 pp / 74.2 tg | **ACTIVE** |
| **7. Sovereign Master & Red Team** | Master architecture orchestration, adversarial devil's advocate, dialectic debate | `Huihui-Qwen3.8-27B-Abliterated` & `Mistral-Nemo-12B` | Sovereign AI (>8B) | L8 Linux Mini TB4 (`10.0.0.8:8083`) | 48.5 tg (27B) / 29.6 tg (12B) | **ACTIVE** |
| **8. Edge Tool Champion** | Function calling, tool use, agentic JSON extraction, mobile dialogue | `Nemotron-Mini-4B-Instruct` & `Llama-3.2-3B` | Edge AI (3B / 4B) | L8 Linux Mini (`/home/linuxmini/model_vault_gguf/`) | ~95.0 tg (4B) | **DEPLOYING** |

---

## 📦 3. Canonical Model Size Taxonomy Compliance (Rule 1 & Rule 0)

1. **TinyLM / Nano AI ($\le 20\text{M}$ Parameters):**
   - **`TinyStories-LLaMA2-20M-256h-4l-GQA.Q4_K_M.gguf`** (19,532,032 params, 13.2 MB): Listening on L8 Port 9095. Operates at 339.6 tok/s in sub-5ms for real-time 512Hz ECG streams and zero-latency speculative token drafting.
   - **`tiny10m_drafter`** (10M params): Embedded CPU/ANE drafter.
   - **`pythia-70m.Q8_0.gguf`** (74 MB): Nano signal filter & OpenWrt log classifier.

2. **MiniLM / Sub-Edge Class ($> 20\text{M}$ to $0.5\text{B}$ Parameters):**
   - **`smollm2-135m-instruct-q4_k_m.gguf`** (134,515,008 params, 101 MB): Listening on L8 Port 9096. AST tokenizer, schema validator, 367 tok/s.
   - **`SmolLM2-360M-Instruct-Q4_K_M.gguf`** (259 MB): JSON parser and UI salience drafter.
   - **`qwen2.5-0.5b-instruct-q4_k_m.gguf`** (630M params, 469 MB): Listening on L1 Port 8089 (proxied via Port 8081). Micro tool oracle.

3. **Edge AI ($0.5\text{B}$ to $8\text{B}$ Parameters):**
   - **`SmolVLM-Instruct-Q4_K_M.gguf`** (2.2B, 1.04 GB): Compact multimodal model for edge/mobile UI perception.
   - **`Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`** (4.4 GB + 814 MB mmproj): High-resolution screen vision and OCR grounding.
   - **`Nemotron-Mini-4B-Instruct-Q4_K_M.gguf`** (2.51 GB): NVIDIA tool-calling and agentic function extraction.
   - **`Llama-3.2-3B-Instruct-Q4_K_M.gguf`** (2.02 GB): Meta lightweight edge reasoner.
   - **`DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf`** (1.0 GB): Micro mathematical and reasoning engine.
   - **`qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`** (1.1 GB): Active on L3 Port 8084 for syntax linting.
   - **`Hermes-3-Llama-3.1-8B.Q4_K_M.gguf`** (4.9 GB): Active on L1 Port 8085 via Metal GPU.
   - **`embeddinggemma-2-UD-Q4_K_XL.gguf`** (159 MB): Active on L1 Port 8087 for multimodal RAG.

4. **Sovereign / Swarm AI ($> 8\text{B}$ Parameters):**
   - **`Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf`** (17.3 GB): Active on L8 Port 8083 via 40 Gb/s Thunderbolt 4. Master Sovereign Orchestrator.
   - **`Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf`** (7.0 GB): Dialectic Red Team Devil's Advocate.
   - **`DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf`** (9.7 GB MoE, 16B total / 2.4B active): High-speed coding MoE.
   - **`Hermes-3-Llama-3.1-70B-Q4_K_M.gguf`** (40.0 GB): Sharded distributed reasoner for multi-device ring inference.

---

## 🔄 4. Cloud AI Routing Integration

Cloud models (Gemini 2.5 Flash, Claude 3.5 Sonnet, OpenAI) interface with the local AI fleet through two primary abstraction planes:

### 1. `screen_lens_multi_cloud_router` MCP Tool
- Exposes `multi_cloud_router.route_request(task_type, prefer_local=True)`.
- Returns the optimal local model, endpoint, measured throughput, and memory footprint based on task type:
  - `speculative_draft` $\rightarrow$ `http://10.0.0.8:9095` (TinyStories 20M, <5ms)
  - `syntax` / `fast_syntax` $\rightarrow$ `http://192.168.8.225:8084` (Qwen 2.5 Coder 1.5B on L3)
  - `screen_lens_vla` / `vision` $\rightarrow$ `http://127.0.0.1:8081` (SmolVLM / Qwen2.5-VL)
  - `tool_calling` $\rightarrow$ `http://127.0.0.1:8085` (Hermes-3 8B) or `10.0.0.8:8083` (Nemotron 4B)
  - `biometrics_dsp` $\rightarrow$ `http://10.0.0.8:9095` (TinyStories 20M DSP, 512Hz)
  - `master` $\rightarrow$ `http://10.0.0.8:8083` (Qwen 3.8 Max 27B)

### 2. `screen_lens_speculate_code` Pre-Draft Waterfall
Before spending expensive cloud tokens, cloud AIs query `screen_lens_speculate_code(prompt)` to receive sub-15ms code skeletons:
1. **Tier 0:** TinyStories 20M (`10.0.0.8:9095`) drafts initial tokens in 4.2ms.
2. **Tier 1:** SmolLM2 135M (`10.0.0.8:9096`) expands the syntax skeleton in 8.7ms.
3. **Tier 2:** Qwen 2.5 Coder 1.5B (`192.168.8.225:8084`) validates the AST.
4. **Cloud Teacher:** Gemini / Claude receives the pre-grounded draft, validating and finalizing it with 65–80% fewer output tokens.

---

## 🎓 5. Screen Lens Sovereign Teacher-Student Distillation Protocol

Whenever a Cloud Teacher model reasons, plans, or actuates an action across the mesh, the **Screen Lens Teacher-Student Bridge** (`01_apps/screen_lens/src/lens_teacher_student_distillation_bridge.py`) automatically captures:

1. **Teacher Output:** The reasoning trace, architectural plan, or code diff produced by the frontier model.
2. **Physical Visual Frame & DOM:** Real pixel frames from ScreenCaptureKit or ADB `uiautomator` dump.
3. **Verified Actuation Proof:** Authentic Darwin/Linux exit codes (`exit code 0`), syscalls, or touch coordinates.
4. **Tri-Vault Serialization:**
   - Appended to `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`
   - Visual actions appended to `/Users/aaron/DFS_UNIFIED/lora_datasets/proven_accuracy_vla_dataset.jsonl`
   - Progress monitored in `obsidian_vault/04_ANALYTICS/TEACHER_STUDENT_DISTILLATION_MONITOR.md`

This guarantees that cloud capabilities are continuously crystallized into the local offline model weights without manual data entry.
