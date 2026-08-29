# TEST_INFRA.md: 24/7 Offline & Free-Tier AI Utilization Cron Pipeline
# Master Opaque-Box E2E Testing Infrastructure & Quality Assurance Specification

## 1. Executive Summary & Testing Philosophy

This document defines the canonical End-to-End (E2E) testing framework, testing philosophy, feature matrix, and multi-tier verification methodology for the **Lauburu 24/7 Offline & Free-Tier AI Utilization Cron Pipeline**.

The testing system follows an **opaque-box testing philosophy**: all test suites interact strictly with public module APIs, CLI commands, file system sinks, network port listeners, and documented interface contracts. No internal private variables or mock facades are permitted.

### Core Testing Invariants & Principles:
1. **Rule #0 Zero-Mock Data Verification**:
   - Every telemetry stream, token metric, ELO score, AST diff, and loss curve evaluated must be genuine and verifiable.
   - Any record tagged with mock flags (`truth_verified=False`, simulated data markers) is immediately rejected.
2. **Fail-Closed Biometric Privacy Airgap**:
   - 100% of physiological biometrics (512Hz ECG, Pulse Transit Time BP, RR intervals, PPG sleep staging) and sensitive cryptographic keys must never egress to public cloud AI endpoints (Gemini, Cloudflare Workers AI).
   - Airgap filters must throw immediate security exceptions upon detection of sensitive payload markers.
3. **Deterministic Quota Safety**:
   - Gemini 2.5 Flash Free Tier limiter must strictly clamp at <= 14 RPM and <= 1,400 RPD (leaving safety margin below 15 RPM / 1,500 RPD).
   - Cloudflare Workers AI limiter must strictly clamp at <= 10,000 Neurons/Day with UTC midnight rollover.
4. **Dynamic Resource & Hardware Governance**:
   - Apple Silicon Metal GPU (MLX/MPS) memory footprint during QLoRA training must stay within the <= 21.6 GB (90% unified memory cap) safety ceiling on a 24GB Host.
   - GL.iNet GL-MT3600BE Router RAM must be monitored with sub-second responsiveness, enforcing <= 35 MB critical threshold with proactive `drop_caches` invocation.
5. **Self-Contained & Isolated Test Execution**:
   - Every test case creates and tears down its own isolated temporary workspaces, sandboxes, and file fixtures. Tests can run in any sequence or in parallel without cross-test pollution.

---

## 2. Feature Inventory (Features F01 – F15)

The test matrix covers all 15 core features defined in `PROJECT.md`:

| Feature ID | Feature Name | Description | Target Subsystem / Interface | Milestone |
| :--- | :--- | :--- | :--- | :--- |
| **F01** | **Gemini Free Tier Rate Limiting** | Token-bucket rate limiter enforcing max 14 RPM / 1,400 RPD, exponential backoff on 429, and UTC midnight counter resets. | `06_scripts_and_tooling/automation/cloud_api_quota_manager.py` | M1 |
| **F02** | **Cloudflare Workers AI Quota Tracking** | Daily budget tracker enforcing 10,000 Neurons/Day ceiling, neuron weight calculation per prompt, and UTC midnight reset. | `06_scripts_and_tooling/automation/cloud_api_quota_manager.py` | M1 |
| **F03** | **Local Mesh Offline Inference Dispatch** | Dynamic workload router dispatching 24/7 unlimited local inference across Ports 8081–8086 with sub-second failover. | `06_scripts_and_tooling/automation/cloud_api_quota_manager.py` | M1 |
| **F04** | **Daytime/Overnight Workload Schedule** | Dynamic scheduler switching between Daytime real-time telemetry mode and Overnight batch QLoRA/AST compilation mode (03:00 UTC window). | `06_scripts_and_tooling/automation/free_tier_ai_continuous_cron.py` | M1 |
| **F05** | **Biometric Privacy Airgap** | 100% fail-closed security boundary preventing 512Hz ECG, PTT BP, and private tokens from leaking to public cloud endpoints. | `06_scripts_and_tooling/automation/cloud_api_quota_manager.py` | M1 |
| **F06** | **Multi-Stream LoRA Harvesting** | Multi-channel data ingestion harvesting AI debates, AST code diffs, math proofs, and recovery actions into DPO/RLHF JSONL datasets. | `04_data_and_memory/tri_vault_sink.py` | M2 |
| **F07** | **Daily >= 500 Verified Pair Growth** | Continuous dataset pipeline appending >= 500 verified instruction/DPO pairs daily to `ai_training_game_dataset.jsonl` with atomic locking. | `04_data_and_memory/tri_vault_sink.py` | M2 |
| **F08** | **Nightly Metal GPU QLoRA Training** | Autonomous Apple Silicon Metal (MLX/MPS) QLoRA training harness with rank-32 adapters and dynamic RAM cap <= 21.6 GB. | `04_data_and_memory/fast_train_agentworld_mac.py` | M2 |
| **F09** | **Obsidian Loss Curve Streaming** | Real-time markdown telemetry sink writing training loss curves, perplexity, and master Wikilinks to `obsidian_vault/04_ANALYTICS/`. | `04_data_and_memory/tri_vault_sink.py` | M2 |
| **F10** | **Autonomous Model Weight Merging** | MergeKit DARE-TIES / SLERP recipe generator triggering model merges when debate confidence > 0.95, strictly preserving parent weights. | `00_core_infrastructure/self_healing_hub/src/autonomous_consensus_merger.py` | M2 |
| **F11** | **Tri-Vault Storage Auto-Healing** | Storage watchdog verifying Obsidian Vault, PySpark Data Lake, and Git repository, repairing `Index.md`, purging stale locks, and checking >= 5 GB disk headroom. | `06_scripts_and_tooling/network/hybrid_router_mesh_governor.py` | M3 |
| **F12** | **7 Core Daemons Supervision** | High-availability supervisor monitoring Ports 8080–8086, 18802, 50052, and 8088 with sub-second crash detection and auto-resurrection. | `06_scripts_and_tooling/network/hybrid_router_mesh_governor.py` | M3 |
| **F13** | **GL.iNet Router RAM Governance** | Real-time `/proc/meminfo` parser enforcing <= 35 MB critical RAM threshold on GL-MT3600BE via automated SSH `drop_caches` execution. | `06_scripts_and_tooling/network/hybrid_router_mesh_governor.py` | M3 |
| **F14** | **E2E Regression & Compliance Suite** | Master 4-tier test runner with CLI controls, timing breakdown, pass/fail reporting, and structured JSON output artifact generation. | `tests/e2e/run_all_e2e_tests.py` | M4 |
| **F15** | **Adversarial Coverage Hardening** | Chaos injection, rate limit thrashing, corrupted JSONL payloads, NaN/Inf sensor values, and airgap breach attempt simulations. | `tests/e2e/test_free_tier_cron_pipeline.py` | M4 |

---

## 3. Four-Tier Testing Methodology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   4-TIER OPAQUE-BOX E2E TESTING HIERARCHY                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: Feature Coverage (>= 5 Tests / Feature | 75+ Total Tests)           │
│   • Validates primary happy paths, interface contracts, and return types    │
│   • Verifies F01 through F15 individual functional capabilities             │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: Boundary Value Analysis & Corner Cases (>= 5 Tests / Feature)       │
│   • Edge conditions: 0-byte files, max quotas, clock skew, null inputs      │
│   • Stress thresholds: 14th vs 15th RPM, 9,999 vs 10,001 Neurons, 34.9MB RAM│
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: Cross-Feature Combinations (Pairwise & Combinatorial Matrix)         │
│   • Multi-subsystem interactions (e.g. Quota Exhaustion + Local Mesh Failover)│
│   • Airgap Guard + LoRA Harvester + Obsidian Sink multi-way synchronization │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: Real-World Application Scenarios (>= 5 Full-Workflow E2E Tests)     │
│   • Multi-step 24-hour simulation cycles                                    │
│   • End-to-end operational life-cycles from sensor capture to model merge   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Tier Breakdown:

### Tier 1: Feature Coverage Requirements (>= 5 tests per feature)
- **F01 (Gemini Limiter)**: Happy-path acquisition under 14 RPM; daily count increment under 1,400 RPD; token bucket replenishment; slot release; status serialization.
- **F02 (Cloudflare Tracking)**: Neuron allocation under 10,000; multi-request budget decrement; daily usage calculation; remaining budget query; quota state save.
- **F03 (Local Mesh Dispatch)**: Route request to Port 8081; round-robin across Ports 8081-8086; local synthesis engine execution; local fallback on cloud offline; port health validation.
- **F04 (Daytime/Overnight Schedule)**: Daytime mode classification (10:00 UTC); Overnight mode classification (03:00 UTC); schedule state transition; cron cycle execution; status file generation.
- **F05 (Biometric Airgap)**: Clean text passes airgap check; ECG waveform blocked; PTT BP blood pressure blocked; RR intervals blocked; private API credentials blocked.
- **F06 (Multi-Stream LoRA Harvesting)**: AI debate harvesting; AST code diff harvesting; math proof harvesting; recovery action harvesting; DPO format schema validation.
- **F07 (Daily >= 500 Pair Growth)**: Single pair atomic write; batch write of 50 pairs; duplicate detection; zero-mock validation filter; daily verified count query.
- **F08 (Nightly Metal QLoRA Training)**: Hardware capability detection (M4 Pro); dynamic VRAM cap calculation (<= 21.6 GB); training command generation; MLX vs MPS backend selection; hyperparameter validation (rank=32, batch=2).
- **F09 (Obsidian Loss Curve Streaming)**: Note creation in `obsidian_vault/04_ANALYTICS/`; YAML frontmatter verification; master Wikilinks formatting; loss curve table appending; atomic file replace.
- **F10 (Autonomous Model Weight Merging)**: Consensus score calculation (> 0.95); MergeKit DARE-TIES recipe generation; SLERP recipe generation; parent model preservation invariant; offspring registration in leaderboard.
- **F11 (Tri-Vault Storage Auto-Healing)**: Fast-path health verification; missing directory auto-creation; `Index.md` repair; stale `.git/index.lock` purge; disk headroom >= 5.0 GB evaluation.
- **F12 (7 Core Daemons Supervision)**: Port 8080 health check; Port 8082 health check; Port 8084 health check; Port 8086 health check; Port 18802/50052/8088 matrix scan and resurrection trigger.
- **F13 (GL.iNet Router RAM Governance)**: `/proc/meminfo` parsing; available RAM extraction; safe memory threshold evaluation (> 35 MB); critical memory threshold detection (<= 35 MB); `drop_caches` command formatting.
- **F14 (E2E Regression Suite)**: Test runner discovery; single tier execution; all tier execution; JSON report serialization; exit code propagation.
- **F15 (Adversarial Coverage Hardening)**: Chaos payload rejection; rapid rate-limit bursting; corrupted JSONL recovery; concurrent thread write safety; zero-mock rule enforcement.

### Tier 2: Boundary & Corner Cases Requirements (>= 5 tests per feature)
- Boundary analysis at exact limits: 14 RPM threshold, 1,400th RPD, 10,000th neuron, 35.0 MB RAM boundary, 21.6 GB VRAM ceiling, 0.9500 vs 0.9501 consensus score, empty JSONL files, zero-byte configs, negative token counts, and leap-second / UTC midnight rollovers.

### Tier 3: Cross-Feature Combinations (Pairwise Matrix)
- Validates complex interactions between pairs and triples of subsystems:
  1. *F01 + F03*: Gemini Quota Exhaustion triggers seamless failover to Local Mesh Ports 8081-8086.
  2. *F02 + F04*: Cloudflare Neuron Budget depletion during Overnight mode shifts heavy AST jobs to Metal GPU.
  3. *F05 + F06*: Biometric Airgap filter intercepts ECG telemetry before multi-stream LoRA harvesting.
  4. *F07 + F08 + F09*: 500-pair dataset growth triggers Nightly Metal QLoRA training and streams loss to Obsidian Vault.
  5. *F10 + F11*: Model merge creates offspring artifacts without violating Tri-Vault disk headroom constraints.
  6. *F12 + F13*: Router RAM exhaustion triggers daemon restart and memory recovery concurrently.
  7. *F01 + F02 + F15*: Concurrent rate limit thrashing across Gemini and Cloudflare maintains zero 429 errors.

### Tier 4: Real-World Application Scenarios (5 Scenarios)
1. **Scenario 1: 24-Hour Daytime/Overnight Autonomous Transition**
   - Simulates continuous operation through daytime telemetry streaming, UTC midnight quota reset, and 03:00 UTC batch QLoRA compilation.
2. **Scenario 2: Biometric Telemetry Airgap Breach Prevention**
   - Ingests high-frequency 512Hz ECG and PTT blood pressure streams alongside synthetic coding prompts; verifies 100% airgap quarantine while allowing non-sensitive coding prompts to route to Cloudflare.
3. **Scenario 3: Tri-Orchestrator AI Debate to DPO Harvester and Model Merge**
   - Executes multi-agent debate, evaluates consensus > 0.95, synthesizes DPO pair, appends to dataset, triggers MergeKit SLERP synthesis, and streams loss to Obsidian Vault.
4. **Scenario 4: Cascading Tri-Vault Degradation & Router RAM Self-Healing**
   - Injects corrupt `Index.md`, stale git lock, degraded disk headroom, and low router RAM (31.2 MB); verifies automated self-healing recovers all invariants within a single cycle.
5. **Scenario 5: Multi-Day 500-Pair Daily Growth & Continuous LoRA Distillation**
   - Simulates 3 days of dataset growth (>= 500 pairs/day), verifies atomic locking, validates zero-mock compliance, and executes mock training run with memory cap checks.

---

## 4. Test Runner Invocation & CLI Usage

The master test runner is located at `tests/e2e/run_all_e2e_tests.py`.

```bash
# 1. Run all 4 test tiers (Full E2E Suite)
python3 tests/e2e/run_all_e2e_tests.py --all

# 2. Run a specific tier
python3 tests/e2e/run_all_e2e_tests.py --tier 1
python3 tests/e2e/run_all_e2e_tests.py --tier 2
python3 tests/e2e/run_all_e2e_tests.py --tier 3
python3 tests/e2e/run_all_e2e_tests.py --tier 4

# 3. Run with custom JSON report output
python3 tests/e2e/run_all_e2e_tests.py --all --json-output reports/e2e_test_report.json

# 4. Run directly via pytest
pytest tests/e2e/test_free_tier_cron_pipeline.py -v
```

---

## 5. Acceptance Thresholds & Quality Gates

| Gate ID | Quality Gate Metric | Threshold | Invalidation Condition |
| :--- | :--- | :--- | :--- |
| **QG-01** | E2E Suite Pass Rate | **100.0%** (0 failures, 0 errors) | Any failing test case |
| **QG-02** | Rule #0 Zero-Mock Compliance | **100.0%** verified data | Presence of unverified mock shortcuts |
| **QG-03** | Biometric Airgap Privacy | **100.0%** fail-closed quarantine | Any biometric payload passed to cloud |
| **QG-04** | Rate Limit Safety Margin | <= 14 RPM / <= 1,400 RPD | Request count exceeds safe quota |
| **QG-05** | Hardware Memory Governance | Host <= 21.6 GB, Router > 35.0 MB | Out-of-bounds memory allocation |
| **QG-06** | Total Suite Execution Time | <= 15.0 seconds | Slow, unoptimized test execution |
