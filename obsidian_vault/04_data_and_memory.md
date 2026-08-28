---
title: "04_data_and_memory — 24/7 LoRA Datasets, Google Drive Sync & Vector Memory"
updated: "2026-08-27"
tags: [data, memory, lora_datasets, qdrant, pyspark, google_drive, spec-04]
---

# 04_data_and_memory — 24/7 LoRA Datasets, Google Drive Sync & Vector Memory

## 📋 Scope & Continuous Learning Loop
Houses the persistent big data lake, semantic vector embeddings, continuous fine-tuning datasets, and multi-tier cloud backup synchronization.

## 💾 Storage Architecture & Data Layers
1. **PySpark Big Data Lake:**
   - AST crawlers and monorepo indexing engines indexing 3,100+ code files and 435K+ LOC into Delta Lake / Parquet formats.
2. **24/7 Continuous LoRA Datasets (`lora_datasets/`):**
   - Validated JSONL instruction pairs harvesting agent debate transcripts, validated code diffs, and telemetry for continuous model distillation.
3. **Qdrant Vector Database (Local SQLite Engine):**
   - Embedded semantic vector store (`qdrant_data/collection/rag_documents/storage.sqlite` and `edge_health_runbooks/storage.sqlite`) providing sub-10ms RAG retrieval for agents.
4. **Google Drive Cloud Sync:**
   - Automated cloud replication (`/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/`) ensuring geographic disaster recovery.

## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-04-data-memory-sync`
- **Focus Areas:** PySpark AST parsing, Qdrant vector retrieval, JSONL schema validation, Google Drive rsync.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Storage Rule:** [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- **Scans & Index:** [[PYSPARK_MONOREPO_CRAWL_AUG26]], [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- **Connected Modules:** [[05_agents_and_swarms]], [[12_continuous_lora_evolution]]
