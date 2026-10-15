---
title: "PyCharm Cloud Storage & Structure Setup for Screen Lens & All Models"
date: "2026-10-13"
tags: [pycharm, gcloud, storage, screen_lens, models, tri_vault, bigquery]
---

# 🛠️ PyCharm Cloud Storage & Structure Setup for Screen Lens & All Models

## 1. Google Cloud Storage & BigQuery Data Source (PyCharm Integration)

### Canonical Credential Paths
To complete the PyCharm **Data Sources and Drivers** (`Clouds` -> `MyGCloud` or `Google Cloud Storage` / `BigQuery`) dialog:

| Configuration Field | Recommended Value | Description |
| :--- | :--- | :--- |
| **Authentication Type** | `Credential File` | Service Account JSON Key authentication |
| **Path: Credential JSON file** | `/Users/aaron/.config/gcloud/lauburu-net-cloud-sa.json` | Generated key for `openclaw-analyzer@lauburu-net-cloud.iam.gserviceaccount.com` |
| **Alternative Service Account** | `/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/service_account.json` | Project: `gen-lang-client-0982729216` (`gdrive-mesh-agent`) |
| **User ADC Path** | `/Users/aaron/.config/gcloud/application_default_credentials.json` | Standard Application Default Credentials (`aaron.t.maher@gmail.com`) |

### Active IAM Privileges Attached
The `openclaw-analyzer@lauburu-net-cloud.iam.gserviceaccount.com` identity holds:
- `roles/storage.admin` (Full Cloud Storage bucket read/write/management)
- `roles/bigquery.admin` (Full BigQuery dataset and query access)
- `roles/firebase.admin` (Firebase RTDB and Firestore administration)

---

## 2. Integrated Database Sources (Configured in `.idea/dataSources.xml`)

PyCharm's **Database** tool window is pre-configured with direct introspection into the three core local telemetry databases:

1. **Screen Lens Timeline (`04_data_and_memory/screen_lens_timeline.db`)**
   - Tables: `timeline`
   - Fields: `id`, `event_type`, `timestamp`, `device_id`, `window_title`, `element_text`, `audio_transcript`, `metadata`
   - Direct SQL querying and live event monitoring for Screen Lens actions.
2. **Screen Life Companion (`04_data_and_memory/screen_life_companion.sqlite`)**
   - Local multimodal companion memory and OCR state cache.
3. **Single Chat Nexus (`04_data_and_memory/single_chat_nexus.db`)**
   - Cross-agent and model conversation persistence.

---

## 3. Project Structure & Source Roots (`.idea/lauburu-monorepo.iml`)

To ensure IDE code completion, module resolution, and instant symbol indexing across Screen Lens and the model daemons without unresolved import warnings:

### Registered Source Roots (`isTestSource="false"`)
- `00_core_infrastructure`
- `01_apps/screen_lens/src`
- `02_ai_models_and_inference`
- `03_biometrics_and_dsp`
- `05_agents_and_swarms`
- `06_scripts_and_tooling`

### Excluded Directories
- `04_data_and_memory/test_artifacts`
- Root and nested `.venv` environments

---

## 4. Python Environment & Daemon Dependencies

The project's active `uv` environment (`.venv [3.14.7]`) and `pyproject.toml` have been synchronized with:
- `flask` (Fixed `ModuleNotFoundError: No module named 'flask'` in `BT Serial Terminal Daemon`)
- `pyserial` (Fixed `serial` module imports)
- `duckdb` (Local SQL engine for `.parquet` and `.jsonl` timeseries)
- `qdrant-client` (Vector memory search)
- `google-cloud-storage` & `google-cloud-bigquery` (Direct GCP Python SDKs)
