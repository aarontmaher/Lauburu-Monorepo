---
title: "Tri-Gemini Architecture: Spark, Notebook, and Web Standard App Unified Protocol"
date: "2026-09-15"
tags: [tri_gemini, canonical_notebook, screen_lens, lora_training, mcp]
status: "RATIFIED_PRODUCTION_SPEC"
---

# 🌐 Tri-Gemini Architecture & Canonical Project Master Notebook Spec

## Executive Overview
This specification bridges the three operational execution surfaces of the Google Gemini ecosystem across the 7-Layer Lauburu Mesh:
1. **Gemini Spark:** Embedded in Antigravity IDE & terminal CLI, powered by local MCP servers (`lens_mcp_server.py`).
2. **Gemini Notebooks:** Stateful, reactive Marimo DAG running on L3 Linux Mini (`100.101.39.98:8890`), synced to SeaweedFS (`seaweedfs://notebooks/`).
3. **Gemini Standard App:** Web/Chrome interface utilized for deep research, automatically ingested via Screen Lens visual perception.

---

## 🏛️ 1. The Canonical Project Master Notebook (`canonical_project_master_notebook.py`)
Located at `01_apps/screen_lens/src/notebooks/canonical_project_master_notebook.py`, this engine serves as the living ground-truth state machine:
* **Hardware Matrix Truth:** Enforces physical realities (L2 is Intel/Wi-Fi 5; L3 is Realtek/Wi-Fi 5; M4 and Pixel 10 are Wi-Fi 7).
* **Storage Benchmarks:** Enforces verified empirical numbers (Memory-Mapped CSR at 5.0 bytes/edge, Checkpointed SQLite at 23.35 bytes/edge).
* **Anti-Hallucination Sentinel:** Scans incoming documents and prompts, flagging and correcting disproven claims before model reasoning begins.

---

## ⚡ 2. The Tri-Gemini Automation Bridge (`tri_gemini_automation_bridge.py`)
Located at `01_apps/screen_lens/src/integrations/tri_gemini_automation_bridge.py`:
* **Spark MCP Registration:** Exposes sub-50µs graph queries and live hardware telemetry to Antigravity agents.
* **Notebook Sync:** Automatically pushes canonical state updates to SeaweedFS S3 storage.
* **Split-Screen Web Ingestion:** Automatically ingests research findings from the side-by-side Chrome Gemini window (as captured in Screen Lens telemetry) into `obsidian_vault/APPS_AND_FEATURES/CHROME_RESEARCH_KNOWLEDGE_BASE.md`.

---

## 🔬 3. Continuous LoRA Training & Learning Protocol
Located at `05_agents_and_swarms/protocols/tri_gemini_training_and_learning_protocol.py`:
* Automatically streams verified prompt-completion pairs, architectural diffs, and benchmark logs into `lora_datasets/tri_gemini_protocol_training_runs.jsonl`.
* Ensures 24/7 background learning models continuously inherit zero-mock ground truth.
