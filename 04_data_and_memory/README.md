# 04_data_and_memory — 24/7 LoRA Datasets, Google Drive Sync & Vector Memory

## Scope & Continuous Learning Loop
Houses persistent training data, vector embeddings, and cloud backup systems.

## Memory Architecture
1. **Local NVMe Fast Sync (`/data/active_lora_sync/`):** Zero-latency high-speed dataset generation for active 24/7 fine-tuning.
2. **DFS NAS Archive (`04_data_and_memory/`):** 1.70 TB centralized storage pool holding full training corpuses and raw telemetry logs.
3. **Google Drive Cloud Ledger (`/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/`):** Master cloud mirror updated hourly via `sync_mesh_to_gdrive.py` and `rsync_lora_to_nas.sh`.
4. **Qdrant Vector Database:** High-dimensional semantic embeddings for local RAG retrieval across monorepo documentation, system state, and athlete biometrics.
5. **Nomad & Genetic AI Storage Optimizer (`06_scripts_and_tooling/storage/nomad_genetic_storage_optimizer.py`):** Multi-tier empirical storage balancer and evolutionary file routing engine with continuous ledger tracking (`session_logs/genetic_storage_evolution_ledger.jsonl`).
6. **Immortal Self-Improving Cron (`scripts/nomad_genetic_storage_self_improving_cron.py`):** 24/7 background evolutionary optimization daemon continuously maintaining 80% disk headroom thresholds.
7. **Delta Engine (`delta_engine/`):** Rust-native `delta-rs` ACID Delta Lake writer (`writer.py`), bin-packing compactor (`compactor.py`), zero-copy HuggingFace `datasets` memory-mapped loader (`mmap_loader.py`), and JSONL migrator (`migrator.py`) with cryptographic SHA-256 parity verification over the 10Gbps Thunderbolt 4 bridge (`169.254.187.138`).

---
## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-04-data-memory-sync`
- **Assigned Model Tier:** `Hermes 3 8B / Qwen 2.5 Coder 32B`
- **Skill Definition:** `05_agents_and_swarms/antigravity_skills/spec-04-data-memory-sync/SKILL.md`
- **Governance Mandate:** Continuous recursive optimization of this subsystem's documentation, contracts, and test integrity.
