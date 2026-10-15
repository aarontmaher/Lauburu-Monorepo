# 👁️ Canonical Lens AI Overview — Autonomous Multimodal VLA Architecture

```
========================================================================================
LAUBURU LENS AI — CANONICAL VISION-LANGUAGE-ACTION (VLA) SPECIFICATION
Version: 3.0.0-LENS-2026 | Authority: Aaron (Sovereign) | Integrity: Zero-Mock
Context Engine: SnapKV + Foveated 32K Token Sharding | DPO Dataset: 2,221+ Triplets
========================================================================================
```

---

<!-- CONTEXT_WINDOW_TIER_0_START: 4K_VLA_CORE_IDENTITY -->
## 🧭 Context Window Tier 0: Core VLA Identity & Fast Directives (~4,000 Tokens)

> **Lens AI Ingestion Target:** Fast Edge Micro-Models (`SmolLM2-135M`, `Pixel 10 Pro XL Edge TPU`, `Termux Edge Daemon`).  
> **Processing Latency:** `<15ms` | **Memory Overhead:** `<64 MB`.

### 1. The Autonomous VLA Mission
**Lauburu Lens AI** is an autonomous multimodal Vision-Language-Action companion and computer-use agent. It continuously observes screen viewports, extracts real-time DOM hierarchy trees, computes WCAG AAA contrast ratios, predicts the Next-Best-Action (NBA), and executes verified accessibility and mouse/keyboard events across macOS, Android, and web interfaces with **zero simulated data** and **sub-50ms Time-to-First-Token (TTFT)**.

### 2. Core Operational Rules
1. **Rule #0 Zero-Mock Grounding:** 100% of predicted action coordinates must match authentic bounding boxes queried directly from Chrome DevTools Protocol or native OS accessibility trees. Guessing coordinates or hardcoding offsets is strictly prohibited.
2. **WCAG AAA Compliance Gate:** Any interactive UI element targeted by Lens must satisfy $\ge 7:1$ visual contrast against its background before an interaction is approved.
3. **Continuous DPO Harvesting:** Every teacher inference from Gemini 3.1 Pro or DeepSeek V4 Pro is structured into an authentic DPO triplet (`prompt`, `chosen`, `rejected`) and committed to `04_data_and_memory/` to fuel continuous local LoRA fine-tuning.
<!-- CONTEXT_WINDOW_TIER_0_END -->

---

<!-- CONTEXT_WINDOW_TIER_1_START: 16K_VISUAL_CORTEX_AND_DEVTOOLS_PROTOCOL -->
## 📦 Context Window Tier 1: Visual Cortex & Chrome DevTools Protocol (~16,000 Tokens)

> **Lens AI Ingestion Target:** Local Workhorse Models (`Qwen2.5-Coder-7B` on Port 8081, `Mistral-Nemo-Instruct` on Port 8083).  
> **Processing Latency:** `30–80ms` | **Memory Overhead:** `<380 MB`.

### 1. Chrome DevTools Protocol Integration (`01_apps/lauburu_lens/chrome_debugging_bridge.py`)
- **Transport:** WebSocket connection to headless or active Google Chrome instance running with `--remote-debugging-port=9222`.
- **DOM Inspection Domains:**
  - `DOM.getDocument`: Ingests full active node hierarchy.
  - `DOM.getBoxModel`: Retrieves exact CSS pixel coordinates (`border`, `padding`, `content` quads).
  - `CSS.getComputedStyleForNode`: Extracts color and background color to compute mathematical luminance contrast ratios:
    $$C = \frac{L_1 + 0.05}{L_2 + 0.05}$$
- **Event Dispatch Domains:**
  - `Input.dispatchMouseEvent`: Synthesizes deterministic mouse moves, button down, button up, and click events.
  - `Input.dispatchKeyEvent`: Injects physical keystrokes with authentic key codes and modifier keys.

### 2. Live DOM Extractor (`01_apps/lauburu_lens/dom_element_extractor.py`)
- **Scanned Surfaces:** 
  - Port 4000 Console (`http://localhost:4000`)
  - Self-Healing Hub (`http://localhost:18802`)
  - Voilà Biometrics Portal (`http://localhost:8890`)
- **Target Tag Coverage:** `<button>`, `<a>`, `<input>`, `<select>`, `<canvas>`, and ARIA role elements.
<!-- CONTEXT_WINDOW_TIER_1_END -->

---

<!-- CONTEXT_WINDOW_TIER_2_START: 32K_CONTEXT_EXPANSION_AND_SPECULATIVE_REDUCTION -->
## 🌐 Context Window Tier 2: Context Expansion & Speculative Reduction (~32,000 Tokens)

> **Lens AI Ingestion Target:** Distributed Swarm Coordinator (`prima.cpp` 80B Ring on Port 8082, Whole-Monorepo AST Evaluator).  
> **Processing Latency:** `120–250ms` | **Memory Overhead:** `<1.2 GB`.

### 1. Foveated 32K Token Sharding Architecture
Rather than forcing massive 1,000,000-token full-context trees into local host RAM (which would trigger OOM panics on the 24 GB Mac Mini), Lens employs a **foveated context sharding strategy**:
```
┌────────────────────────┬────────────────────────────────┬───────────────────────────────────────────────────────┐
│ Mesh Node              │ Context Allocation             │ Content Stored in Window                              │
├────────────────────────┼────────────────────────────────┼───────────────────────────────────────────────────────┤
│ L1: Mac Mini M4 Pro    │ Chunk 0 (Root Intent & CoT)    │ 4K Tokens: Active objective, current action, memory   │
│ L2: MacBook Pro (TB4)  │ Chunks 1..N (AST & Repo Index) │ 32K Tokens: Deep monorepo AST via 10Gbps TB4 DMA     │
│ L6: Pixel 10 Pro XL    │ Edge Cache (Sensory Viewport)  │ 8K Tokens: Recent 10 visual frames & OCR text streams │
│ L7: Samsung Galaxy S20 │ Log Buffer (Execution History) │ 8K Tokens: Rolling accessibility event stream logs    │
└────────────────────────┴────────────────────────────────┴───────────────────────────────────────────────────────┘
```

### 2. SnapKV & Speculative Token Compression (`01_apps/screen_lens/src/lens_speculative_draft_engine.py`)
- **SnapKV Clustering:** Retains key visual anchor tokens and evicts up to **80% of repetitive whitespace and syntax tokens** without degrading action generation accuracy.
- **Speculative Drafting:** Micro-models (`SmolLM2-135M` at 367 tok/s) draft initial action predictions. If confidence exceeds $\ge 0.95$, the action executes immediately; otherwise, it escalates to `Qwen2.5-Coder-7B` or cloud teachers.
<!-- CONTEXT_WINDOW_TIER_2_END -->

---

<!-- CONTEXT_WINDOW_TIER_3_START: 128K_DPO_DISTILLATION_AND_WEIGHT_MERGING -->
## 🔮 Context Window Tier 3: Multimodal DPO Distillation & Model Weights (~128,000+ Tokens)

> **Lens AI Ingestion Target:** Frontier Cloud Teachers (`Gemini 3.1 Pro Preview` 2M Context, `DeepSeek V4 Pro 1.6T` 1M Context).  
> **Processing Latency:** Cloud Async (`1–3s`) | **Memory Overhead:** Cloud Offloaded ($0 Cost).

### 1. DPO Triplet Harvesting Pipeline (`lens_rapid_quota_maximizer.py`)
- **Total Verified Dataset:** **2,221+ authentic records (2.6 MB)** in `/Users/aaron/DFS_UNIFIED/lora_datasets/lens_ai/lens_multimodal_dpo.jsonl`.
- **DPO Triplet Schema:**
  - `prompt`: Surface target, URL, target element tag, and intent.
  - `chosen`: High-precision viewport coordinates, Chrome CDP event dispatch string, WCAG contrast verification, 0.0ms synthetic lag.
  - `rejected`: Default origin click (0, 0) or unverified coordinate guess lacking DOM tree confirmation.
  - `teacher_engine`: Gemini 3.1 Pro, DeepSeek V4 Pro 1.6T, Cloudflare Llama 3.3 70B, or xAI Grok-2.

### 2. Continuous Local Apple Silicon QLoRA Training
- **Framework:** Apple MLX (`mlx-lm.lora`) and PyTorch Metal Performance Shaders (MPS).
- **Target Base Weights:** `Qwen2.5-Coder-7B-Instruct` and `SmolLM2-1.7B-Instruct`.
- **Tournament ELO Integration:** Checkpoints participate in Bradley-Terry tournaments (`qwen-moe --local-burst`) to validate token generation velocity and action accuracy before merging.
<!-- CONTEXT_WINDOW_TIER_3_END -->
