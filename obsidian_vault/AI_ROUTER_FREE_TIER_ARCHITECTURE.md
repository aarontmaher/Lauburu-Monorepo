---
title: "Lauburu AI Router Free Tier & Multi-Tier Gateway Architecture"
updated: "2026-08-29T03:45:00Z"
tags: [lauburu, ai_router, free_tier, gemini, cloudflare_workers_ai, huggingface, jules, local_mesh, ai_debate]
---

# 🌐 Lauburu AI Router: Free API Usage & Multi-Tier Gateway Architecture

## 1. Executive Summary & Zero-Spend Mandate
The **Lauburu AI Router** provides an adaptive, edge-to-local AI routing infrastructure designed to achieve **$0.00 recurring monthly cloud AI spend** while maximizing intelligence, throughput, and reliability across the 7-layer hardware mesh.

It establishes a deterministic multi-tier routing cascade that prioritizes free-tier cloud quotas and local hardware acceleration before engaging metered fallback APIs under a strict **$1.00 hard kill-switch**.

---

## 🏛️ 2. Four-Tier AI Routing Cascade

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LAUBURU AI ROUTING PRIORITY MATRIX                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 0: LOCAL HARDWARE MESH (0ms Egress, $0.00 Cost, Infinite Quota)       │
│ • llama.cpp RPC Mesh: Ports 8081-8084 sharded across TB4 10Gbps Bridge     │
│ • Models: Kimi-88B Tandem, Qwen-27B, Mistral-Nemo-12B, Llama-3.1-8B       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: FREE CLOUD QUOTAS ($0.00 Cost, Rate-Limit Governed)                 │
│ • Google Gemini API Free Tier (Gemini 2.0 Flash, Gemini 1.5 Pro)            │
│ • Cloudflare Workers AI Free Tier (10,000 Neurons/day, Llama 3.3 70B, etc.) │
│ • Hugging Face / Julien Serverless Inference API (Open Source Models)       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: ASYNCHRONOUS AGENT WORKFLOWS ($0.00 Task Automation)                │
│ • Google Jules CLI (npx @google/jules) for repo-scale background refactors  │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: BUDGET-CONTROLLED PAID FALLBACK (Hard $1.00 Kill-Switch)             │
│ • Anthropic Claude 3.5 Sonnet / Opus / Haiku via Budget Proxy (Port 9000)   │
│ • OpenAI GPT-4o / o1 via Budget Proxy                                       │
│ • Cloudflare AI Gateway unified observability & latency tracking            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 3. Unified Endpoints & Route Definitions

### 3.1 Local Budget Proxy & Router (Port 9000)
- **Status & Health:** `GET http://localhost:9000/status`
- **Unified Chat Completions:** `POST http://localhost:9000/v1/chat/completions`
  - Automatic model prefix routing:
    - `gemini/*` or `google/*` -> Gemini Free Tier API
    - `cf/*` or `@cf/*` -> Cloudflare Workers AI Free Tier
    - `hf/*` or `julien/*` -> Hugging Face Serverless API
    - `local/*` or `mesh/*` -> Local llama.cpp Mesh (Port 8081/8083)
    - `claude/*` -> Anthropic Claude API ($1 kill-switch protected)
    - `gpt/*` -> OpenAI GPT-4o ($1 kill-switch protected)
- **Direct Provider Proxies:**
  - `POST http://localhost:9000/v1/google/...`
  - `POST http://localhost:9000/v1/cloudflare/...`
  - `POST http://localhost:9000/v1/huggingface/...`
  - `POST http://localhost:9000/v1/julien/...`
  - `POST http://localhost:9000/v1/local/...`

### 3.2 Cloudflare Edge AI Gateway Worker
- **Location:** `00_core_infrastructure/cloudflare/workers/ai_gateway_router/worker.js`
- **Gateway Base:** `https://gateway.ai.cloudflare.com/v1/16282271f1eccb56f0b96afed09d21ff/lauburu-ai-gateway`
- **Native Binding:** `env.AI.run()` for sub-50ms global inference on Cloudflare edge.

---

## 🛡️ 4. Devil's Advocate Audit Mitigations
During the AI Debate Protocol, the real abliterated model (**Llama-3.1-8B-Abliterated** on Port 8083) identified 8 systemic failure modes. The architecture mitigates every risk:

| Vulnerability | Identified Risk | Architectural Mitigation |
| :--- | :--- | :--- |
| **Rate-Limit Storms** | HTTP 429 errors halting swarm pipelines | Automatic sliding-window governor + transparent fallback to local mesh on Port 8081/8083. |
| **Silent API Throttling** | Cloud providers degrading latency under load | Continuous latency tracking headers (`X-Lauburu-Latency-Ms`) and dynamic re-routing. |
| **Data & Secret Leaks** | API keys persisted in transaction ledgers | Ephemeral header forwarding (`x-goog-api-key`, `Authorization`) without storing secrets. |
| **Cascading Downstream Crashes** | Cloud provider outages bringing down mesh | Decentralized survival matrix; if all cloud links fail, local mesh operates 100% offline. |
| **Opaque Black Boxes** | Model behavioral drift | Every interaction serialized to `/Users/aaron/DFS_UNIFIED/lora_datasets/api_interactions.jsonl` for continuous audit. |

---

## 🔄 5. Continuous LoRA Dataset Harvesting & Tri-Vault Sync
All transactions through the AI router (free and paid) generate structured instruction/response pairs logged to:
- `/Users/aaron/DFS_UNIFIED/lora_datasets/api_interactions.jsonl`
- Synchronized to the PySpark Big Data Lake and Obsidian Knowledge Graph for 24/7 continuous distillation.

---
## 🔗 Related Knowledge Vault Notes
- [[Index]] — Master Knowledge Vault Core
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]] — Tri-Vault Storage & Tooling Architecture
- [[02_ai_models_and_inference]] — Distributed AI & Compute Mesh
- [[ai-debate]] — Tri-Orchestrator AI Debate Protocol
- [[CLOUDFLARE_DEEP_RESEARCH]] — Cloudflare Ecosystem Deep Technical Research
