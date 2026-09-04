# Project: Lauburu Monorepo Canonical Architecture & Tri-Vault Synchronization (Gen 24)

## Architecture
The Lauburu Mesh Ecosystem pools 108.0 GB RAM (82.8 GB usable AI VRAM) across 7 physical hardware layers, synchronized via a Tri-Vault storage architecture (Obsidian Knowledge Core, PySpark Data Lake, GitHub Monorepo), governed by dynamic RAM boundaries and Rule 0.1 Zero-Mock empirical truth verification.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1: Master Architecture & 7-Layer Topology | 108.0 GB RAM / 82.8 GB VRAM, RAM governor, Tri-Vault storage, Zero-Mock | M1 | survey |
| 2 | R1: Tri-Vault & Index Sync | Sync CANONICAL_PROJECT_OVERVIEW.md to 07_docs and obsidian_vault with [[Index]] | M1 | survey |
| 3 | R2: 01_apps Ecosystem Specification | Port 4000, Movesense 512Hz ECG DSP, Zone 2, 3D Spatial, Screen Lens, Port 4004, Voice IDE, Termux | M2 | survey |
| 4 | R2: Tri-Vault & Index Sync | Sync CANONICAL_APPS_OVERVIEW.md to 07_docs and obsidian_vault with [[Index]] | M2 | survey |
| 5 | R3: Commercialization & Unit Economics | Shopify GraphQL, subscription tiers, BLE hardware bundles, $0 cloud infra, CAC/LTV | M3 | survey |
| 6 | R3: Tri-Vault & Index Sync | Sync CANONICAL_BUSINESS_PLAN_OVERVIEW.md to 07_docs and obsidian_vault with [[Index]] | M3 | survey |
| 7 | R4: Lens AI VLA Subsystem | Port 4003 MJPEG stream, Mach RAM auditor, Gemini Flash teacher, DPO LoRA harvesting | M4 | survey |
| 8 | R4: Tri-Vault & Index Sync | Sync LENS_AI_CANONICAL_OVERVIEW.md to 07_docs and obsidian_vault with [[Index]] | M4 | survey |
| 9 | Omnichannel Knowledge Hub Indexing | Upgrade lens_omnichannel_knowledge_hub.py to index all 4 overviews on Port 4004 | M5 | survey |
| 10 | Omnichannel Sub-ms Search Verification | Verify sub-millisecond retrieval via /api/knowledge/search for all 4 overviews | M5 | survey |
| 11 | 24/7 DPO LoRA Trajectory Generation | Generate authentic DPO pairs for all 4 domains with valid SHA256 checksums | M6 | survey |
| 12 | Host RAM Sanctuary Verification | Mac Mini M4 Pro preserves >= 9.6 GB available memory (Mach kernel audit) | M6 | survey |
| 13 | Multi-tier Review & Challenger Verification | Verify empirical truth, wikilinks, exit codes, latency benchmarks | M7 | survey |
| 14 | Forensic Integrity Audit Gate | Zero-Mock compliance, zero simulated data, authentic artifacts | M7 | survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Canonical Project Overview | Author & sync CANONICAL_PROJECT_OVERVIEW.md across 07_docs and obsidian_vault | Survey | DONE |
| M2 | Canonical Apps Overview | Author & sync CANONICAL_APPS_OVERVIEW.md across 07_docs and obsidian_vault | Survey | DONE |
| M3 | Canonical Business Plan Overview | Author & sync CANONICAL_BUSINESS_PLAN_OVERVIEW.md across 07_docs and obsidian_vault | Survey | DONE |
| M4 | Lens AI Canonical Overview | Author & sync LENS_AI_CANONICAL_OVERVIEW.md across 07_docs and obsidian_vault | Survey | DONE |
| M5 | Omnichannel Hub Indexing & Search | Upgrade lens_omnichannel_knowledge_hub.py and verify /api/knowledge/search | M1, M2, M3, M4 | DONE |
| M6 | LoRA Harvesting & Host RAM Sanctuary | Generate DPO pairs with SHA256 in continuous_lora_dataset.jsonl & audit RAM | M1, M2, M3, M4 | DONE |
| M7 | Multi-tier Review & Forensic Audit Gate | Reviewers, Challengers, and Forensic Auditor verification | M1-M6 | DONE |

## Code Layout & Write Boundaries
- Worker 1 (M1 & M4): Owns `07_docs_and_architecture/CANONICAL_PROJECT_OVERVIEW.md`, `obsidian_vault/CANONICAL_PROJECT_OVERVIEW.md`, `07_docs_and_architecture/LENS_AI_CANONICAL_OVERVIEW.md`, `obsidian_vault/LENS_AI_CANONICAL_OVERVIEW.md`.
- Worker 2 (M2 & M3): Owns `07_docs_and_architecture/CANONICAL_APPS_OVERVIEW.md`, `obsidian_vault/CANONICAL_APPS_OVERVIEW.md`, `07_docs_and_architecture/CANONICAL_BUSINESS_PLAN_OVERVIEW.md`, `obsidian_vault/CANONICAL_BUSINESS_PLAN_OVERVIEW.md`.
- Worker 3 (M5 & M6): Owns `01_apps/screen_lens/src/lens_omnichannel_knowledge_hub.py`, `obsidian_vault/Index.md`, and `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`.
