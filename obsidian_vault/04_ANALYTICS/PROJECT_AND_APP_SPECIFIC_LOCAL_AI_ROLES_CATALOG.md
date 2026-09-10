---
title: "Project & App-Specific Local AI Roles & Specialist Training Catalog"
date: "2026-09-08T00:10:00Z"
tags: [ai_roles, specialist_ai, local_models, training_catalog, tri_vault, monorepo, 7_layer_mesh]
total_roles_cataloged: 24
total_projects_covered: 7
mesh_hardware_vram_pool_gb: 82.8
---

# 🤖 Project & App-Specific Local AI Roles & Specialist Training Catalog

This canonical catalog defines all **24 dedicated, specialized Local AI roles** across the 7 monorepo projects, their edge applications, target local models, quantization schemes, physical mesh hardware placements, and active continuous training pipelines.

---

## 🏛️ Tri-Vault Master Links
- [[Index]] — Master Knowledge Vault Index
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]] — Tri-Vault Storage & 7-Layer Mesh Topology
- [[CLOUD_TEACHER_LOCAL_OUTPERFORMANCE_REPORT]] — Gate 8 Significant Outperformance Matrix
- [[AI_DEBATE_CLOUD_SHADOW_OUTPERFORMANCE_LATEST]] — Tri-Orchestrator Swarm Consensus
- [[SPECIALIST_AI_TRAINING_AND_MASTERY_REPORT]] — Live Continuous Fine-Tuning & Mastery Receipts

---

## 📊 Comprehensive 24-Role Project & App Allocation Matrix

| # | Role ID | Project / App Subsystem | Primary Specialty & Scope | Target Local Silicon | Quant | Mesh Layer & Node | Continuous Training Dataset |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `posix_gateway_healer` | `00_core_infrastructure` (Gateway) | OpenWrt UCI, iptables, dropbear SSH, etherwake failover | `SmolLM2-135M-Instruct` | `IQ1_S` | **GW** (`GL.iNet Router`) | `specialists/posix_gateway_healer.jsonl` |
| **2** | `tb4_dma_tensor_streamer` | `00_core_infrastructure` (Bridge) | 10Gbps TB4 DMA PCIe socket multiplexing (0.27ms RTT) | `SmolLM2-135M-Instruct` | `IQ2_XXS` | **L1/L2** (`Mac_Node` & `MacBook_Pro`) | `specialists/tb4_dma_tensor_streamer.jsonl` |
| **3** | `multiwan_self_healing_sentinel` | `00_core_infrastructure` (Mesh Hub) | Port 18802 REST daemon, Tailscale WireGuard auto-failover | `SmolLM2-135M Host Sentinel` | `Q4_K_M` | **L1/L3** (`Mac_Node` & `Linux_Head_Node`) | `specialists/multiwan_self_healing_sentinel.jsonl` |
| **4** | `screen_lens_vla_auditor` | `01_apps` (`screen_lens`) | 4K ShowUI coordinate grounding, 90% token pruning, visual truth audit | `Kimi Tandem Titan (VL+72B)` & `Qwen2.5-VL-7B` | `Q4_K_M` | **L1/L2** (`Mac_Node` & `MacBook_Pro`) | `specialists/screen_lens_vla_auditor.jsonl` |
| **5** | `movesense_clinical_dsp` | `01_apps` (`movesense_hub` / `zone2`) | 512Hz ECG, Pan-Tompkins QRS, Kamath 20% filter, DFA-$\alpha_1$ HRV | `BioMistral 7B` & `SmolLM2-360M` | `Q8_0` | **L4** (`Linux_Tablet`) | `specialists/movesense_clinical_dsp.jsonl` |
| **6** | `polyglot_tui_designer` | `01_apps` (`canonical_port` / TUI) | C/ncurses, Python Textual, Go Bubble Tea, Rust Ratatui, 120 FPS render | `Qwen 2.5 Coder 7B` | `Q4_K_M` | **L1/L3** (`Mac_Node` & `Linux_Head_Node`) | `specialists/polyglot_tui_designer.jsonl` |
| **7** | `spatial_grappling_kinematics` | `01_apps` (`spatial_and_3d`) | 955-node OPML tatami hierarchy, WebGPU Rust shader pipelines | `Qwen 2.5 Coder 32B` | `Q4_K_M` | **L2/L5** (`MacBook_Pro` & `MacBook_Air`) | `specialists/spatial_grappling_kinematics.jsonl` |
| **8** | `shopify_commerce_analyst` | `01_apps` (`shopify_ai` / commerce) | Storefront GraphQL, Liquid themes, Polaris admin, OpenClaw UX audits | `Gemma-2-2B-Instruct` | `Q4_K_M` | **L3/L7** (`Linux_Head_Node` & `Samsung_S20`) | `specialists/shopify_commerce_analyst.jsonl` |
| **9** | `mobile_gesture_automator` | `01_apps` (`termux_edge_daemon`) | Android 15 Shizuku API, Termux keepalive, touch/swipe coordinate injection | `SmolLM2-1.7B-Instruct` | `Q4_K_M` | **L6/L7** (`Pixel_10_Pro_XL` & `Samsung_S20`) | `specialists/mobile_gesture_automator.jsonl` |
| **10** | `sovereign_master_orchestrator` | `02_ai_models_and_inference` (Core) | Sovereign Master Local Orchestrator, prima.cpp PRP Ring consensus (:8082) | `Qwen 3.8 Max 27B` | `UD-Q4_K_XL`| **L1/L2** (`Mac_Node` & `MacBook_Pro` TB4) | `specialists/sovereign_master_orchestrator.jsonl` |
| **11** | `devils_advocate_red_team` | `02_ai_models_and_inference` (Audit) | Canonical Devil's Advocate, uncensored adversarial red-teaming (:8083) | `Qwen 3.8 Max 27B Abliterated` | `UD-Q4_K_XL`| **L2/L1** (`MacBook_Pro` & `Mac_Node`) | `specialists/devils_advocate_red_team.jsonl` |
| **12** | `subordinate_syntax_worker` | `02_ai_models_and_inference` (Syntax)| Single-file AST syntax parsing, compiler diagnostic repair (:8081) | `Qwen 2.5 Coder 7B` | `Q4_K_M` | **L1** (`Mac_Node` Metal MPS) | `specialists/subordinate_syntax_worker.jsonl` |
| **13** | `swe_bench_mesh_sharder` | `02_ai_models_and_inference` (RPC) | llama.cpp RPC 82.8 GB VRAM pooling, Petals DHT, SWE-bench problem solving | `Qwen 2.5 Coder 32B` | `Q4_K_M` | **L2/L3** (`MacBook_Pro` & `Linux_Head_Node`) | `specialists/swe_bench_mesh_sharder.jsonl` |
| **14** | `npu_ecg_signal_filter` | `03_biometrics_and_telemetry` (NPU) | Sub-0.1ms integer-arithmetic bandpass filtering on Tensor G5 / Exynos NPU | `NanoVision-OCR-10M-NPU` | `INT8` | **L6/L7** (`Pixel_10_Pro_XL` & `Samsung_S20`) | `specialists/npu_ecg_signal_filter.jsonl` |
| **15** | `autonomic_stress_hypnogram_coach` | `03_biometrics_and_telemetry` (Bio) | Long-context sleep hypnograms, circadian rhythm, VO2max aerobic threshold | `BioMistral 7B` | `Q8_0` | **L4/L5** (`Linux_Tablet` & `MacBook_Air`) | `specialists/autonomic_stress_hypnogram_coach.jsonl` |
| **16** | `trivault_storage_governor` | `04_data_and_memory` (Storage) | PySpark Parquet Lakehouse schema validation, POSIX file replacement locks | `Qwen 2.5 Coder 7B` | `Q4_K_M` | **L1/L3** (`Mac_Node` & `Linux_Head_Node`) | `specialists/trivault_storage_governor.jsonl` |
| **17** | `continuous_lora_chronicler` | `04_data_and_memory` (Datasets) | Continuous LoRA pair serialization, Google Drive cloud backup sync | `Qwen 2.5 Coder 7B` | `Q4_K_M` | **L1/L3** (`Mac_Node` & `Linux_Head_Node`) | `specialists/continuous_lora_chronicler.jsonl` |
| **18** | `debate_arbiter_genetic_moe` | `05_agents_and_swarms` (Governance) | Bradley-Terry dynamic K-factor scaling, Genetic MoE hyperparameter evolution | `Qwen 3.8 Max 27B` | `UD-Q4_K_XL`| **L1/L2** (`Mac_Node` & `MacBook_Pro`) | `specialists/debate_arbiter_genetic_moe.jsonl` |
| **19** | `ast_analysis_adversarial_specialist`| `05_agents_and_swarms` (CodeClash)| Symbol graph extraction, PageRank centrality, CodeClash mutant testing | `Qwen2.5-Coder-0.5B` & `7B` | `Q4_K_M` | **L3** (`Linux_Head_Node` Ryzen 5700U) | `specialists/ast_analysis_adversarial_specialist.jsonl` |
| **20** | `micro_specialist_mesh_coordinator` | `05_agents_and_swarms` (Swarm) | 4-Tier micro-specialist pipeline connecting sensor condensers to 80B MoE | `UnifiedSpecialistMeshCoordinator` | `HYBRID` | **L1-L7 Mesh** | `specialists/micro_specialist_mesh_coordinator.jsonl` |
| **21** | `universal_ssh_keepalive_specialist`| `06_scripts_and_tooling` (Daemons) | Zero-latency SSH socket daemons across macOS, Linux, and Android/Termux | `SmolLM2-360M Nano Sentinel` | `Q4_K_M` | **L1-L7 Mesh** | `specialists/universal_ssh_keepalive_specialist.jsonl` |
| **22** | `wol_hardware_resurrector` | `06_scripts_and_tooling` (Power) | RFC 792 Magic Packet UDP 9/7 injection, Port 18802 REST resurrect daemon | `SmolLM2-135M-Instruct` | `IQ2_XXS` | **L1/GW** (`Mac_Node` & `GL.iNet`) | `specialists/wol_hardware_resurrector.jsonl` |
| **23** | `notebook_visual_data_specialist` | Federated Notebooks (Voilà / Marimo) | 139 JupyterLab & Marimo notebooks, Voilà Port 8890 Master Cyber Studio | `local_ai_notebook_specialist` | `Q4_K_M` | **L1/L5** (`Mac_Node` & `MacBook_Air`) | `specialists/notebook_visual_data_specialist.jsonl` |
| **24** | `router_uci_mesh_governor` | Federated Infrastructure (Routers) | GL.iNet Beryl 7 & TP-Link MLO AP automation, kmwan failover, headless CDP | `SmolLM2-135M` (`spec_posix_healer`) | `IQ1_S` | **GW** (`GL.iNet Router`) | `specialists/router_uci_mesh_governor.jsonl` |

---

## 🔬 Active Specialist AI Training Lifecycle

Every specialized role follows the **Continuous Compound Learning Pipeline**:
1. **Domain Trajectory Extraction**: Authentic code ASTs, biometrics sensor streams, and debate transcripts are extracted directly from production repositories.
2. **Anti-Mock Verification Gate (Rule #0)**: Synthetic, fake, or mock placeholders are unconditionally rejected.
3. **Contrastive DPO / SFT Pair Synthesis**: Teacher CoT traces and chosen/rejected pairs are serialized to `lora_datasets/specialists/<role_id>.jsonl` and mirrored to `continuous_lora_dataset.jsonl`.
4. **Apple Silicon Metal QLoRA Step**: Gradient updates execute on `Device(gpu, 0)` with loss convergence tracking.
5. **Empirical Receipt Certification**: Fine-tuning trials record pre/post accuracy, loss reduction, and physical `Exit Code 0` in `04_data_and_memory/lora_datasets/niche_fine_tuning_receipts.jsonl`.
6. **RAM Sanctuary Safety Gate (Rule #3)**: Host memory utilization remains strictly $\le 90\%$ (preserving $\ge 9.6\text{ GB}$ headroom).

---

*Canonical Catalog maintained autonomously by ContinuousSpecialistRoleTrainer — Lauburu Mesh Ecosystem.*
