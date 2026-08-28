# Lauburu Monorepo — Canonical Distributed NAS Architecture (1.70 TB)

## Overview
This is the master unified monorepo for the **Lauburu Ecosystem**, pooled and distributed across the 7-device hardware mesh via **SeaweedFS Distributed File System (1.701 TB Logical FUSE Capacity)** and exported via SMB3 / Tailscale.

## Global 7-Device Mesh Topology (100+ GB RAM / 82.8 GB Total Pooled AI VRAM)
1. **Layer 1 (Mac_Node / Apple M4 Pro Mac Mini Host):** Primary memory governor, ADB controller, prompt ingestion (24GB RAM / 21.6 GB AI Cap, `127.0.0.1` / `100.119.199.76` / `192.168.8.230`).
2. **Layer 2 (MacBook_Pro / Storage Vault):** Metal GPU RPC & 285 GB SSD Model Vault over 10Gbps Thunderbolt 4 (`100.103.212.21` / `169.254.187.138`).
3. **Layer 3 (Linux_Head_Node / Gateway & Compute Hub):** AMD Ryzen 7 5700U, Docker supervisor, SeaweedFS Master & Filer, Apache Ray Head (`100.101.39.98`).
4. **Layer 4 (Linux_Tablet / Mobile Compute & Touch):** Debian Linux Tablet, secondary Petals worker, lightweight biometrics (`100.81.92.125`).
5. **Layer 5 (MacBook_Air / High-Speed Metal Worker):** Apple M4 MacBook Air, Secondary Metal Performance Shaders, LoRA fine-tuning (16GB RAM / 13.5 GB AI Cap, `100.93.158.96` / `192.168.8.222`).
6. **Layer 6 (Pixel_10_Pro_XL / Edge TPU & Vision Stream):** Google Tensor G5, 8K Digital PTZ, UWB Spatial Anchor (`100.73.38.87`).
7. **Layer 7 (Samsung_S20 / Dedicated Automated UI Tester):** Samsung Exynos 990, Router USB ADB target for automated OpenClaw UI audits (`100.84.40.95`).

## Core Canonical Subsystems (00_ through 12_)
- `00_core_infrastructure/`: Master SeaweedFS, Docker Compose, Tailscale overlay, multi-WAN failover, systemd & launchd units.
- `01_apps/`: Production client apps (Port 4000 Hub, Movesense Hub, Zone 2 Endurance, Grappling Map Web, Obsidian Web Quartz, Chat App, OpenClaw UI Automator, Voice Coder).
- `02_ai_models_and_inference/`: llama.cpp RPC sharding (Ports 8081–8084), Petals DHT cluster, Exo mesh, quantized GGUF weights.
- `03_biometrics_and_telemetry/`: Movesense 512Hz ECG, Pan-Tompkins QRS, PTT Blood Pressure, DFA-alpha1 thresholds, Whoop intelligence.
- `04_data_and_memory/`: PySpark Big Data lake, 24/7 LoRA datasets, Google Drive synchronization, Qdrant vector memory.
- `05_agents_and_swarms/`: Antigravity skill registry, Tri-Orchestrator Soul, Genetic MoE optimization engine, Swarm Truth Audit.
- `06_scripts_and_tooling/`: Autonomous network self-healing scripts, global NAS mounting automations, ADB controllers, expect scripts.
- `07_docs_and_architecture/`: Canonical whitepapers, API contracts, hardware topologies, and audit ledgers.
- `08_business_and_commerce/`: Shopify Storefront GraphQL, membership tiers, subscription billing, CAC/LTV modeling, profitability research.
- `09_app_store_and_release/`: Google Play & Apple App Store release workflows, APK/AAB keystore signing, memory leak audits, OTA manifests.
- `10_spatial_grappling_kinematics/`: 955-node OPML spatial trees, 3D tatami world models, joint torque, biomechanical kinematics.
- `11_security_and_governance/`: Hardware isolation, SSH/RPC socket encryption, Cloudflare HMAC auth, zero source-code leakage.
- `12_continuous_lora_evolution/`: Continuous LoRA distillation, TRL/PEFT/DPO pipelines, Genetic MoE weight merging, $0 cloud spend failover.

## Compliance & Governance
- **Mandatory Insignia Rule:** Canonical geometric Lauburu symbol (white hourglass loop on black) located at `/assets/branding/canonical_lauburu_symbol.svg`.
- **Zero-Mock Telemetry Rule:** Strictly NO simulated or fake data. Metrics originate exclusively from live hardware.
- **Persistent .md Manifest Rule:** Every subfolder contains a self-documenting `.md` manifest detailing inputs, outputs, endpoints, and verification tests.


---
## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `global-project-architect-specialist`
- **Assigned Model Tier:** `DeepSeek-R1-70B (IQ4_XS) / Qwen 3.8 Max (Q4_K_M) on 82.8 GB Mesh`
- **Skill Definition:** `05_agents_and_swarms/antigravity_skills/global-project-architect-specialist/SKILL.md`
- **Governance Mandate:** Continuous recursive optimization of this subsystem's documentation, contracts, and test integrity.
