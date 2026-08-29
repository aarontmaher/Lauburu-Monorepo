# Project: Lauburu 24/7 Offline & Free-Tier AI Utilization Cron Pipeline

## Architecture
The system integrates an autonomous 24/7 cron and daemon governance pipeline across the 7-node physical mesh, pooling 108.0 GB RAM (82.8 GB usable AI VRAM) and enforcing $0 recurring cloud spend.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│             24/7 OFFLINE & FREE-TIER AI UTILIZATION CRON PIPELINE           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Rate Limiter & Quota Governor (R1)                                       │
│    • Gemini 2.5 Flash Free Tier: Enforces max 14 RPM / 1,400 RPD            │
│    • Cloudflare Workers AI: Enforces max 10,000 Neurons/Day                 │
│    • Local Mesh Inference: Ports 8081-8086 unlimited local offline compute   │
│    • Airgapping: 100% fail-closed privacy lock for biometrics (ECG/PTT BP)  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. LoRA Harvesting & Local Metal Training Pipeline (R2)                     │
│    • Multi-Stream Harvester: Debates, code diffs, math proofs, recoveries    │
│    • Daily Quota: >= 500 verified DPO/RLHF pairs in ai_training_game_dataset│
│    • Nightly Distillation: Apple Metal GPU QLoRA (MLX/MPS), Dynamic RAM <=90%│
│    • Loss & Model Sync: Obsidian Vault loss curves, MergeKit DARE-TIES/SLERP│
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Tri-Vault Storage Auto-Healing & Daemon Governance (R3)                  │
│    • Tri-Vault Watchdog: Obsidian Index.md, PySpark Lake, Git worktrees     │
│    • 7 Core Daemons: Ports 8080-8086, 18802, 50052, 8088 sub-second failover│
│    • Hardware Governor: GL-MT3600BE Router RAM <= 35MB with drop_caches     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Opaque-Box E2E Testing Track (Tiers 1-4) & Adversarial Hardening (Tier 5)│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Gemini Free Tier Rate Limiting | Enforce max 14 RPM and 1,400 RPD token-bucket limiter preventing 429 errors | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Cloudflare Workers AI Quota Tracking | Enforce 10,000 Neurons/Day ceiling with daily UTC midnight reset | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Local Mesh Offline Inference Dispatch | Route unlimited 24/7 inference to Ports 8081-8086 (llama-servers) | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Daytime/Overnight Workload Schedule | Real-time daytime biometrics vs overnight batch QLoRA/AST synthesis | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Biometric Privacy Airgap | 100% fail-closed local hardware lock for 512Hz ECG, PTT BP, GATT telemetry | M1 | ORIGINAL_REQUEST §R1 |
| 6 | Multi-Stream LoRA Harvesting | Harvest debate transcripts, AST diffs, math proofs into DPO/RLHF JSONL | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Daily >=500 Verified Pair Growth | Append verified instruction pairs to `04_data_and_memory/ai_training_game_dataset.jsonl` | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Nightly Metal GPU QLoRA Training | Autonomous MLX/MPS distillation with dynamic RAM ceiling <=21.6GB | M2 | ORIGINAL_REQUEST §R2 |
| 9 | Obsidian Loss Curve Streaming | Stream mathematical loss metrics to Obsidian Vault analytics notes | M2 | ORIGINAL_REQUEST §R2 |
| 10 | Autonomous Model Weight Merging | MergeKit DARE-TIES / SLERP model merging preserving parent weights | M2 | ORIGINAL_REQUEST §R2 |
| 11 | Tri-Vault Storage Auto-Healing | Inode verification, Index.md repair, stale Git lock cleanup, >=5GB disk headroom | M3 | ORIGINAL_REQUEST §R3 |
| 12 | 7 Core Daemons Supervision | Sub-second monitoring & auto-restart for Ports 8080-8086, 18802, 50052, 8088 | M3 | ORIGINAL_REQUEST §R3 |
| 13 | GL.iNet Router RAM Governance | Enforce Router RAM <=35MB critical threshold on GL-MT3600BE via SSH drop_caches | M3 | ORIGINAL_REQUEST §R3 |
| 14 | E2E Regression & Compliance Suite | 100% pass across Tier 1-4 tests (rate limits, dataset growth, daemons, storage) | M4 | ORIGINAL_REQUEST Acceptance Criteria |
| 15 | Adversarial Coverage Hardening | White-box stress testing, chaos injection, edge cases (Tier 5) | M4 | ORIGINAL_REQUEST Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | `free_tier_quota_governance_and_rate_limiter` | Rate limiting (Gemini/Cloudflare), offline mesh routing, biometric airgapping | None | DONE (237/237 tests passing) |
| M2 | `lora_dataset_harvesting_and_metal_training_pipeline` | DPO/RLHF harvesting (>=500 pairs/day), nightly Metal QLoRA, Obsidian loss, MergeKit | None | DONE (15/15 tests passing) |
| M3 | `tri_vault_storage_healing_and_daemon_supervision` | Tri-Vault auto-healing, 7-daemon watchdog (sub-sec failover), Router RAM <=35MB | None | IN_PROGRESS (Conv: 1959373e) |
| E2E | `e2e_testing_track` | Opaque-box E2E test suites (Tiers 1-4), TEST_INFRA.md, TEST_READY.md | None | DONE (171/171 passing) |
| M4 | `integrated_e2e_verification_and_adversarial_hardening` | Phase 1: 100% E2E test pass (Tiers 1-4); Phase 2: Adversarial Tier 5 hardening | M1, M2, M3, E2E Track | PLANNED |

## Interface Contracts
### `cloud_api_quota_manager` ↔ `free_tier_ai_continuous_cron`
- `acquire_gemini_slot() -> bool`: Returns True if under 14 RPM and 1,400 RPD, else waits or routes local.
- `acquire_cloudflare_neurons(count: int) -> bool`: Returns True if within 10k daily neuron budget.
- `is_airgapped_data(payload: dict) -> bool`: Returns True if payload contains biometrics/secrets.

### `tri_vault_sink` ↔ `lora_datasets`
- `append_verified_pair(dataset_path: str, pair: dict) -> bool`: Validates schema, zero-mock flags, writes atomically.
- `get_daily_verified_count(dataset_path: str) -> int`: Returns number of valid entries added in last 24 hours.

### `storage_sentinel` ↔ `daemon_manager`
- `verify_and_heal_tri_vault() -> dict`: Returns health status of Obsidian, PySpark Lake, and Git worktrees.
- `check_and_heal_daemons() -> dict`: Inspects ports 8080-8086, 18802, 50052, 8088, triggers restart on failure.
- `check_router_ram() -> float`: Returns GL-MT3600BE available RAM, triggers drop_caches if <= 35MB.

## Code Layout
- `00_core_infrastructure/`: Self-Healing Hub (Port 18802), SeaweedFS, Tailscale mesh.
- `04_data_and_memory/`: PySpark Lake, `ai_training_game_dataset.jsonl`, `tri_vault_sink.py`, LoRA harvesters.
- `06_scripts_and_tooling/automation/`: `free_tier_ai_continuous_cron.py`, `cloud_api_quota_manager.py`.
- `06_scripts_and_tooling/network/`: `daemon_manager.py`, `nomad_courier_self_healer.py`, `router_onboard_micro_governor.sh`.
- `06_scripts_and_tooling/training/`: `fast_train_agentworld_mac.py`, `autonomous_consensus_merger.py`.
- `obsidian_vault/`: Knowledge graph notes, `Index.md`, analytics loss curve records.
- `tests/e2e/`: Opaque-box E2E test suites (Tiers 1-4) and master test runner.
