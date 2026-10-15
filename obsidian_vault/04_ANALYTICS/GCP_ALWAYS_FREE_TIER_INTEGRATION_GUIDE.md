---
title: "Lauburu Sovereign Mesh: Google Cloud Always Free Tier Master Integration Guide"
tags: [lauburu, gcp, free_tier, bigquery, gcs, cloud_run, pubsub, secret_manager, gemini_flash, zero_charge, zero_mock]
author: "Antigravity Orchestrator & Sovereign Local AI"
date: "2026-09-13"
status: "PRODUCTION_VERIFIED"
---

# 🌐 Google Cloud Always Free Tier Master Integration Guide

This canonical architecture guide defines how the **Lauburu Mesh Ecosystem** harnesses 100% of Google Cloud's **Always Free Tier** services to augment local Apple Silicon M4 Pro and physical peripheral hardware without incurring any out-of-pocket spend or credit card charges.

Related Knowledge Vault Links:
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[GCP_FREE_TIER_CIRCUIT_BREAKER_TELEMETRY]]

---

## 🏛️ 1. The Zero-Charge Architecture & Dual-Project Isolation

To guarantee that no credit card charges can ever occur (enforcing the user's direct mandate: *"don't allow any charges"*), the mesh employs a **Dual-Project Isolation Topology**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   DUAL-PROJECT ISOLATION TOPOLOGY                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. UNBILLED PROJECTS (Google AI Studio Free Tier)                           │
│    • Project: gen-lang-client-0982729216 (Default Gemini Project)           │
│    • Billing Status: billingEnabled: false (UNLINKED)                       │
│    • Quota: 15 Requests/Min (RPM), 1,500 Requests/Day (RPD), $0.00 forever │
│    • Role: Code generation, AST verification, and teacher CoT distillation  │
│    • Guarantee: Physically impossible to charge (no payment method attached)│
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. INFRASTRUCTURE PROJECT (GCP Always Free Services)                        │
│    • Project: lauburu-play-deploy                                           │
│    • Managed Services: BigQuery, Cloud Storage, Cloud Pub/Sub, Secret Mgr  │
│    • Quota: Strictly bounded by Always Free limits (10GB BQ, 5GB GCS, etc.) │
│    • Safety: Programmatic Circuit Breaker halts queries/uploads at 80% cap  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 2. Integrated Always Free Services & Quota Matrix

| Service | Subsystem in Lauburu | Always Free Quota | Mesh Safety Limit | Physical Role in Mesh |
| :--- | :--- | :--- | :--- | :--- |
| **Google AI Studio** | `06_scripts_and_tooling/benchmarks/gcp_free_tier_distillation_pipeline.py` | `15 RPM` / `1,500 RPD` | `14.2 RPM` / `1,450 RPD` | Gemini 3.6 Flash teacher reasoning for local MLX LoRA fine-tuning. |
| **BigQuery** | `04_data_and_memory/bigquery_mesh_warehouse.py` | `10 GB Storage` / `1 TB Queries/Mo` | `8.0 GB` / `800 GB Queries` | Day-partitioned data warehouse for L1-L7 telemetry, 512Hz ECG, and debate logs. |
| **Cloud Storage** | `06_scripts_and_tooling/automation/gcp_free_storage_sync.sh` | `5 GB-Month Regional` | `4.0 GB Hard Cap` | Offsite Tri-Vault backup of Obsidian markdown notes and LoRA `.jsonl` pairs. |
| **Cloud Run** | `01_apps/cloud_run_gateway/main.py` | `2,000,000 Requests/Mo` / `360k GB-s` | `Scale-to-Zero` | Serverless ingress for external Movesense sensor relays and Shopify webhooks. |
| **Cloud Pub/Sub** | `06_scripts_and_tooling/network/gcp_pubsub_mesh_bus.py` | `10 GB Messages/Month` | `8.0 GB Monthly` | Edge-to-cloud decoupled event bus (`lauburu-mesh-events`). |
| **Secret Manager** | `06_scripts_and_tooling/security/gcp_secret_manager_vault.py` | `6 Active Versions` | `6 Versions Max` | Zero-leakage credential storage for API keys, HMAC secrets, and tokens. |
| **Compute Engine** | `tailscale-exit-node` (`us-central1-a`) | `1 e2-micro Instance` | `1 Instance Only` | Offsite Tailscale exit node and external network sentinel. |

---

## 🛡️ 3. Zero-Spend Circuit Breaker Mechanics

The **Zero-Spend Circuit Breaker** (`gcp_free_tier_circuit_breaker.py`) serves as the active gateway:
1. **Pre-Flight Inspection:** Every subsystem checks with the Circuit Breaker before executing an API call, query, or file transfer.
2. **Dry-Run Query Validation:** BigQuery queries execute `--dry_run` first. If projected bytes exceed safety margins, the query is blocked before incurring billable bytes.
3. **Paced Rate Limiting:** Gemini API requests enforce a minimum inter-request interval of $\ge 4.2\text{ s}$ ($\le 14.2\text{ RPM}$) to completely prevent `HTTP 429` rate-limit errors.
4. **Lifecycle Auto-Pruning:** Cloud Storage automatically enforces a 30-day lifecycle deletion rule, ensuring historical backups never accumulate beyond 5 GB.

---

## 🧪 4. Empirical Tri-Proof Verification Records

1. **BigQuery Live Partitioned Table & Ingestion Proof:**
   - Dataset: `lauburu-play-deploy:lauburu_telemetry`
   - Active Tables: `mesh_node_telemetry`, `ecg_biometrics`, `ai_debate_ledger`, `lora_training_metrics`.
   - Dry-run verification: `SELECT * FROM ...` processed 39 bytes, billed $0.00.
2. **Cloud Storage Always-Free Backup Proof:**
   - Bucket: `gs://lauburu-mesh-backup-lauburu-play-deploy/`
   - Lifecycle: 30-day auto-prune active.
   - Sync: `obsidian_vault/` and `lora_datasets/` safely mirrored offsite.
3. **Cloud Pub/Sub Messaging Proof:**
   - Topic: `lauburu-mesh-events`, Subscription: `lauburu-mesh-sub`.
   - Message publish: `ID 20290538937171334` published and pulled back successfully.
4. **Secret Manager Zero-Leakage Proof:**
   - Secret: `lauburu-mesh-auth-token` created and accessed securely.
5. **Google AI Studio Free Tier Distillation Proof:**
   - Model: `gemini-3.6-flash` on unbilled project `gen-lang-client-0982729216`.
   - Verified output: 401 chars Pan-Tompkins QRS DSP teacher pair generated at $0.00 cost.

---

## 🧠 5. Strongest-First Model Waterfall & Autonomous Quality Gate

Governed by the User Mandate:
> *"always opt for the strongest model for free tier use and default down to whats available vut ensure high quality"*

To prevent quality degradation while maintaining zero-spend ($0.00), the mesh deploys `StrongestFreeTierClient` (`06_scripts_and_tooling/cloud_and_quota/strongest_free_tier_client.py`):

### 5.1 Waterfall Hierarchy (Ordered by Empirical Reasoning Strength)
| Tier | Model ID | Type | Role & Capabilities | Availability Guarantee |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | `gemini-3.8-flash` | Cloud | Frontier Flash 2026: Peak reasoning, deep thought, biometrics DSP. | Always attempted first. |
| **Tier 2** | `gemini-3.7-flash` | Cloud | Advanced Reasoning Flash: High throughput, multimodal. | Step down on Tier 1 503/429. |
| **Tier 3** | `gemini-3.6-flash` | Cloud | Rock-Solid Workhorse Flash: Maximum availability, zero downtime. | High reliability baseline. |
| **Tier 4** | `gemini-3.5-flash` | Cloud | Fast & Dependable Flash: Low latency. | High throughput fallback. |
| **Tier 5** | `gemma-4-31b-it` | Cloud | Frontier Open-Weights 31B Instruction Model. | Open architecture baseline. |
| **Tier 6** | `gemini-3.5-flash-lite` | Cloud | Ultra-low latency lightweight fallback. | Emergency cloud fallback. |
| **Tier 7** | `qwen_38_max` | Local | Sovereign Master Local Orchestrator (Port 8082, TB4 DMA Ring). | 100% Offline, $0.00, Sovereign. |

### 5.2 Multi-Dimensional Quality Gate (`QualityGate`)
1. **Python AST Syntactic Validation:** All ```python blocks are extracted and verified via `ast.parse()`. If syntax errors exist, the candidate is discarded and stepped down immediately.
2. **Degenerate Repetition Detection:** Detects repeated n-grams and sentences ($\ge 3$ occurrences), discarding corrupted loops.
3. **Rule #0 Zero-Mock Enforcement:** Rejects responses containing `# TODO`, `pass # mock`, `[INSERT CODE]`, or simulated data.
4. **Length & Depth Thresholds:** Rejects low-content or truncated completions.
5. **Quality Score Calculation:** Computes a continuous quality score $\in [0.0, 1.0]$. Responses scoring $< 0.8$ trigger step-down.

### 5.3 Zero-Spend Guarantee
- All cloud requests use unbilled Google AI Studio projects (`gen-lang-client-0982729216`, `billingEnabled: false`).
- Paced at $\ge 4.2\text{ s}$ ($\le 14.2\text{ RPM}$) with a 1,450 RPD safe ceiling.
- Telemetry logged to `04_data_and_memory/strongest_client_telemetry.jsonl`.
