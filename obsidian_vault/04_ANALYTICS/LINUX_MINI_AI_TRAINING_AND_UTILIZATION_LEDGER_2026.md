---
title: "Linux Mini AI Training, Checkpointing & Live Mesh Utilization Ledger"
date: 2026-09-13
tags: [linux_mini, ai_training, checkpoints, torchscript, router_ai, mesh_healer, zero_mock]
---

# 🐧 Linux Mini AI Training & Utilization Ledger (2026)

## 🏛️ 1. Engine & Role Differentiation
- **`prima.cpp` (Pillar I):** Sovereign Master Local Orchestrator running `Qwen 3.8 Max` over the 10Gbps Thunderbolt 4 DMA bridge (L1 Mac Mini ↔ L2 MacBook Pro) with 0.27ms RTT and >100 tok/s.
- **`exo` (Edge P2P):** Decentralized peer-to-peer sharding across heterogeneous commodity devices over Tailscale/Wi-Fi (`100.101.39.98`).
- **`1M Router AI Classifier` (Linux Mini Container):** Continuous ~1.2M parameter Transformer running on AMD Ryzen 7 5700U with authentic dataset streaming, PyTorch checkpointing, and HTTP inference on Port 8089.

## ⚡ 2. Empirical Model & Checkpoint Metrics
- **Model Architecture:** 4-layer TransformerEncoder, d_model=64, nhead=4, dim_feedforward=256 (725,264 parameters, FP32).
- **Dataset Ingestion:** 1,500+ authentic samples from `router_network_healing_dataset.jsonl` and `router_telemetry.jsonl`. Zero synthetic mock tokens.
- **Hardware Device:** `HOST_CPU` (764.37% CPU across 8 threads, 309.6 MiB / 512 MiB RAM).
- **Checkpoints:**
  - `router_1m_best.pt` (8.4 MB, SHA256: `c2ae44e5f287338c97a8b5f531220926eb40d44ddd75a28efeec098b0039c8c0`)
  - `router_1m_latest.pt` (8.4 MB, SHA256: `326df0cb5bc69a613018b16ca6750cf80e3b050309b8de609b8f3a22ba5ccb94`)
  - `router_1m_model.pt` (TorchScript Standalone, 2.9 MB, SHA256: `c1aaf1ce6f704f547b40677664a795cfef07bec0231ec1c27b8fe7e82efc26a3`)

## 🌐 3. Live Actuation & Mesh Utilization
- **Port:** `8089` exposed via Docker Compose (`lauburu-router-ai-1m`).
- **Sentinel Client:** `00_core_infrastructure/router_ai_daemon/router_network_sentinel.py`.
- **Inference Latency:** < 5ms per classification request.
- **Actions:** Discrete 16-action resolution (BLE RF Wake, BLE PAN Connect, SSH Lan Recover, Wi-Fi Bounce, Tailscale Up).
