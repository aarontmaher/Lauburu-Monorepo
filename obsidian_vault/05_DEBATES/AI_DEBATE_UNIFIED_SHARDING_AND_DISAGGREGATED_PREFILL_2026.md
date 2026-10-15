---
title: "AI Debate Consensus: Unified Sharding, RAM-vs-VRAM Optimization & Non-Overloading Telemetry (2026)"
tags: [ai_debate, unified_sharding, disaggregated_prefill, ram_vs_vram, netmon, glances, mesh]
date: "2026-10-15"
consensus_threshold: 0.999
devil_advocate_verdict: "RAM_VS_VRAM_AWARE_ROUTING_VERIFIED"
---

# 🏛️ Tri-Orchestrator AI Debate Consensus Whitepaper (v2.0)
*Topic: RAM-vs-VRAM Heterogeneous Sharding & Non-Overloading Glances/NetMon Telemetry.*

## 1. Normal System RAM (0 GB VRAM) vs Unified Metal VRAM vs Discrete GPU VRAM
- **Class 1 — Apple Silicon Unified Metal VRAM (`L1` 24GB @ 273 GB/s, `L5` 16GB @ 120 GB/s, `L1b` 16GB @ 200 GB/s):** Zero-copy GPU/ANE access (`-ngl 99 -fa`). Primary host for dense prefill and attention decode layers.
- **Class 2 — Discrete GDDR6 VRAM + DDR4 Normal RAM (`L2` 4GB Radeon Pro 5300M + 16GB DDR4):** Capped at `<= 3.2 GB` (`-ngl 14`) on GPU; remaining capacity used via AVX2 CPU (`-t 6`).
- **Class 3 — Normal System RAM ONLY — `0 GB` Dedicated VRAM (`L3` Ryzen 7 5700U 16GB DDR4 @ 25.6 GB/s, `L8` Intel i7-8700B 32GB DDR4 @ 34.1 GB/s, `L4` 8GB, `L7` 12GB LPDDR5):** Must run `-ngl 0` with `physical_cores - 1` thread cap (`L3: -t 7`, `L8: -t 10`), quantized KV cache (`-ctk q8_0 -ctv q8_0`), and `--no-mlock`. Assigned to **Neo4j 5.26.32 (`L3`), Disaggregated KV-Cache Storage (`L8`), Sparse MoE Experts, and Speculative Draft Heads** rather than bandwidth-bound dense decode.
- **Class 4 — Edge NPU Unified LPDDR5X (`L6` Pixel 10 Pro XL 16GB Tensor G5):** Assigned LiteRT/MediaPipe EmbeddingGemma 2 MRL (`256d/512d`) and mobile courier inference.

## 2. Non-Overloading Telemetry Governance (`netmon` + Glances API)
- **Forbidden Endpoints:** `/api/3/all` and `/api/4/all` are strictly banned (`6.91s` blocking and `449.3 MB` RAM on `L3`).
- **Allowed Modular Endpoints:** `/quicklook`, `/mem`, `/load`, `/network` (plus `/fs` on a 60s TTL cache).
- **Server-Side Pruning:** `glances -w -B 0.0.0.0 -p 61208 -t 5 --disable-plugin docker,containers,ports,folders,raid,cloud,amps,processlist` (`43.7 MB` RAM, `73 ms` response on `L3`).
