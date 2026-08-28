---
title: "Global Architecture Map & 13-Module Monorepo Subsystems"
updated: "2026-08-27"
tags: [architecture, global_map, subsystems, monorepo, 13_modules]
---

# Global Architecture Map & 13-Module Monorepo Subsystems

## 📋 Comprehensive Monorepo Architecture Map
Connects the 13 canonical numbered modules, the Tri-Vault storage layers, and multi-agent governance into a cohesive unified topology.

```mermaid
graph TD
    subgraph Storage ["Tri-Vault Storage Core"]
        OV["1. Obsidian Vault (obsidian_vault/)"]
        PS["2. PySpark Lake (lora_datasets/ & 04_data_and_memory/)"]
        GH["3. GitHub Repo (aarontmaher/Lauburu-Monorepo)"]
    end

    subgraph Modules ["Canonical 13-Module Hierarchy"]
        M00["00_core_infrastructure"]
        M01["01_apps"]
        M02["02_ai_models_and_inference"]
        M03["03_biometrics_and_telemetry"]
        M04["04_data_and_memory"]
        M05["05_agents_and_swarms"]
        M06["06_scripts_and_tooling"]
        M07["07_docs_and_architecture"]
        M08["08_business_and_commerce"]
        M09["09_app_store_and_release"]
        M10["10_spatial_grappling_kinematics"]
        M11["11_security_and_governance"]
        M12["12_continuous_lora_evolution"]
    end

    M05 -->|Debate & Governance| Modules
    Modules -->|Sync & Index| Storage
```

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Deep Architecture Index:** [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- **Canonical Rule:** [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
