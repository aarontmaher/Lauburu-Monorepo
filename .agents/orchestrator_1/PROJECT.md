# Project: Lauburu Monorepo Unification & Tri-Vault Storage Reconciliation

## Architecture
- **Canonical 13-Module Hierarchy**:
  - `00_core_infrastructure`: Docker, SeaweedFS, Tailscale, Supabase, Cloudflare Workers, LaunchDaemons
  - `01_apps`: Frontend applications (Movesense Hub, Zone 2, Grappling Map Web, Obsidian Web, Port 4000 Hub, Chat App, OpenClaw, Voice Coder)
  - `02_ai_models_and_inference`: llama.cpp RPC sharding, Petals DHT, Exo P2P, GGUF vault manifests
  - `03_biometrics_and_telemetry`: Pan-Tompkins QRS, Movesense 512Hz ECG, PTT Blood Pressure, DFA-alpha1, Whoop Intelligence
  - `04_data_and_memory`: PySpark indexers, Qdrant Vector DB, 24/7 LoRA datasets, Google Drive sync
  - `05_agents_and_swarms`: Tri-Orchestrator, Genetic MoE Engine, Truth Audit, ELO rankings
  - `06_scripts_and_tooling`: Universal SSH, ADB Keepalive, WoL Resurrection, expect scripts, maintenance tooling
  - `07_docs_and_architecture`: Architecture indexes, whitepapers, security RFCs, core docs
  - `08_business_and_commerce`: Shopify Storefront GraphQL, membership tiers, subscription billing
  - `09_app_store_and_release`: Play Store / App Store release workflows, APK/AAB signing, OTA manifests
  - `10_spatial_grappling_kinematics`: 955-node OPML spatial trees, 3D tatami kinematics, biomechanical models
  - `11_security_and_governance`: RPC socket encryption, Cloudflare HMAC, isolation policies, security audit suites
  - `12_continuous_lora_evolution`: Continuous LoRA distillation, TRL/PEFT/DPO pipelines, weight merging
  - `obsidian_vault`: Master knowledge graph, Wikilinks, debate transcripts
  - `teamwork_projects`: 34+ active federated project workspaces

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Monorepo Inode & File Tree Indexing | Index and verify all 133,463 files across monorepo and 63,898 teamwork files | M1 | Survey 1 |
| 2 | Root Level Hygiene & Stray File Relocation | Relocate 163 loose root files (29 exp, 46 png, 30 xml, 17 docker, 12 jsonl) into canonical modules | M1 | Survey 1 & 2 |
| 3 | Canonical Module Population & Symlinking | Map and populate empty stubs in 01_apps, 00_core_infrastructure, 06_scripts, 04_data, 10_spatial | M1 | Survey 1 |
| 4 | Symlink Integrity & Broken Link Remediation | Fix 2 broken symlinks and convert absolute internal symlinks to portable relative symlinks | M1 | Survey 1 |
| 5 | Legacy Backward Compatibility | Maintain non-breaking relative links for core/ and webapp/ paths | M1 | Survey 1 |
| 6 | Obsidian Vault Index Synchronization | Update Index.md with [[Index]], [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]], [[CANONICAL_PROJECT_AND_STORAGE_RULE]], and 13 module Wikilinks | M2 | Survey 2 |
| 7 | Obsidian Graph Link Repair | Resolve dangling Wikilinks and ensure note connectivity | M2 | Survey 2 |
| 8 | PySpark & LoRA Lake Verification | Verify 15 JSONL datasets, disk headroom (>=10GB), and Qdrant local vector store | M2 | Survey 2 |
| 9 | GitHub Monorepo Worktree Cleanliness | Verify git worktree synchronization, 0 merge conflicts, no index.lock, pristine root README.md | M2 | Survey 2 |
| 10 | Quartz Digital Garden Build (>=260 pages) | Build Quartz in 01_apps/obsidian_web using Node v22, emitting >= 260 pages to public/ | M3 | Survey 3 |
| 11 | Obsidian Desktop Vault Graph Visibility | Configure .obsidian/ (graph.json, core-plugins.json, workspace.json) for full graph/note visibility | M3 | Survey 3 |
| 12 | 01_apps Compilation & Test Verification | Verify Next.js zone2_endurance, FastAPI port_4000_hub (31 tests), and compute hub compilation | M3 | Survey 3 |
| 13 | Zero-Mock Biometrics DSP Verification | Audit Movesense 512Hz ECG, Pan-Tompkins QRS, Whoop intelligence for Rule #0 compliance | M4 | Survey 3 |
| 14 | Zero-Mock Hardware Telemetry Fallback | Ensure all telemetry pollers return null/-- states when physical sensors are disconnected | M4 | Survey 3 |
| 15 | E2E Testing Suite (Tiers 1-4) | Comprehensive opaque-box test runner validating all features | M5 | Dual Track |
| 16 | Adversarial Hardening (Tier 5) & Audit | Challenger gap analysis and Forensic Integrity Audit binary veto gate | M5 | Dual Track |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Monorepo Structuring, Root Hygiene & Symlink Integrity | Relocate 163 root files, populate canonical stubs (00_, 01_, 04_, 06_, 10_), fix broken symlinks, preserve backward-compatible links | none | PLANNED |
| M2 | Tri-Vault Storage Synchronization & Knowledge Graph Indexing | Update obsidian_vault/Index.md with master Wikilinks, verify PySpark LoRA lake and Qdrant vector store, ensure git worktree cleanliness | M1 | PLANNED |
| M3 | Apps Ecosystem & Quartz Digital Garden Build (>=260 pages) | Verify Quartz build in 01_apps/obsidian_web emitting >=260 pages, verify Desktop Obsidian graph visibility, test 01_apps builds | M1, M2 | PLANNED |
| M4 | Zero-Mock Telemetry & Hardware Biometrics DSP Verification | Audit biometrics DSP pipelines, ensure zero fake arrays, verify graceful null/-- fallback states | M1, M3 | PLANNED |
| M5 | E2E Test Suite Pass (Tiers 1-4) & Adversarial Victory Audit (Tier 5) | Run full E2E test harness, execute challenger stress tests, and obtain CLEAN Forensic Integrity Audit verdict | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### 01_apps/obsidian_web ↔ obsidian_vault
- `01_apps/obsidian_web/content` MUST be a valid relative symlink pointing to `../../obsidian_vault`.
- Quartz build MUST emit >= 260 files into `01_apps/obsidian_web/public`.

### legacy `core/` & `webapp/` ↔ canonical `00_`–`12_`
- `core/apps/grapplingmap-web` & `webapp/` mapped to `01_apps/grapplingmap_web` with non-breaking symlinks.
- `core/chat-app` mapped to `01_apps/chat_app`.
- `core/cloudflare-worker` mapped to `00_core_infrastructure/cloudflare_worker`.
- `core/supabase` mapped to `00_core_infrastructure/supabase`.
- `core/scripts` mapped to `06_scripts_and_tooling/core_scripts`.
- `core/data` mapped to `04_data_and_memory/core_data`.

## Code Layout
- `00_core_infrastructure/docker/`: Docker Compose and Dockerfiles
- `01_apps/`: Next.js, FastAPI, Quartz, and frontend app roots
- `03_biometrics_and_telemetry/dsp_algorithms/`: DSP pipelines and telemetry readers
- `04_data_and_memory/lora_datasets/`: JSONL training datasets
- `06_scripts_and_tooling/expect/`: `.exp` automation scripts
- `reports/screenshots/`: `.png` UI captures
- `reports/ui_dumps/`: `.xml` UI hierarchy dumps
- `obsidian_vault/`: Master knowledge graph and markdown notes
