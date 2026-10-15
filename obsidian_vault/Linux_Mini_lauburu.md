---
title: "Linux_Mini (lauburu) Live Mesh Telemetry"
node_id: "lauburu"
layer: "L8"
status: "ONLINE"
last_synced: "2026-10-14T22:15:00Z"
tags: [lauburu, mesh_node, telemetry, live_sync, thunderbolt, model_vault]
---
# 📡 [[Linux_Mini (lauburu)]] Telemetry Status

- **Master Index**: [[Index]]
- **Deep Architecture Index**: [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- **Thunderbolt IP**: `10.0.0.8` (`bridge0` PCIe DMA, 40 Gb/s)
- **Local LAN IP**: `192.168.8.242`
- **Tailscale IP**: `100.121.247.8`
- **Hardware**: Intel Core i7-8700B (12 cores), 32 GB RAM
- **Operating System**: Ubuntu 24.04 LTS (Linux 6.8 x86_64)
- **Primary Roles**: High-RAM Compute Hub, 40 Gbps TB4 DMA Bridge, GGUF Model Vault Hub (`/home/linuxmini/model_vault_gguf/`), Glances v4 (:61208), KDE Connect

## 📊 Live Resource Metrics
| Metric | Value | Cap / Limit |
| :--- | :--- | :--- |
| CPU Load | 15.2% | 100.0% |
| RAM Ingest | 14.80 GB | 32.00 GB |
| AI VRAM Usage | 12.00 GB | 25.60 GB (80% Cap) |
| TB4 DMA Latency RTT | 0.140 ms avg (0.136–0.144 ms) | <0.50 ms |
| Tailscale Latency RTT | 3.5 ms | <10.0 ms |
| Packet Drop Rate | 0.0% | 0.0% |
