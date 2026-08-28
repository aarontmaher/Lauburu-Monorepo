---
title: "Sub-Project: /swarm (7-Device Hardware Mesh & Autonomous Lineage)"
updated: "2026-08-24T10:44:04Z"
tags: [sub_project, swarm, mesh, rpc_sharding, lora, lineage]
---

# 🐝 Sub-Project: `/swarm`

The **Master Swarm Engine** pools compute across 7 physical devices into a unified 82.8 GB Usable AI VRAM runtime (100+ GB System RAM), executing 24/7 autonomous self-healing and continuous LoRA memory distillation.

## 🖥️ 7-Layer Physical Topology
| Layer | Node | Network IP / Interconnect | Safe AI VRAM Cap | Priority Fill Rank |
| :--- | :--- | :--- | :--- | :--- |
| **Layer 1** | `Mac_Node` (Apple M4 Pro Mac Mini Host, 24GB) | `100.119.199.76` / `127.0.0.1` (Host Orchestrator & Memory Governor) | **21.6 GB** | Rank 4 (Fills Fourth) |
| **Layer 2** | `MacBook_Pro` (Intel i7 / M1 Max Vault, 16GB) | `100.103.212.21` (TB4 10Gbps Direct Link / Tailscale) | **14.0 GB** | Rank 2 (Fills Second) |
| **Layer 3** | `Linux_Head_Node` (AMD Ryzen 7 5700U, 16GB) | `100.101.39.98` (Ray Head Ingress Gateway & NVMe) | **13.8 GB** | Rank 1 (Fills First) |
| **Layer 4** | `Linux_Tablet` (Debian Linux Tablet, 8GB) | `100.81.92.125` (Bedside Mobile Linux HUD) | **6.5 GB** | Rank 1 (Fills First) |
| **Layer 5** | `MacBook_Air` (Headless Apple M4 MacBook Air, 16GB) | `100.93.158.96` (Secondary High-Speed Metal GPU Node) | **13.5 GB** | Rank 3 (Fills Third) |
| **Layer 6** | `Pixel_10_Pro_XL` (Google Pixel 10 Pro XL, 16GB) | `100.73.38.87` (Tensor G5 Edge TPU) | **12.5 GB** | Rank 6 (Battery Regulated) |
| **Layer 7** | `Samsung_S20` (Samsung Galaxy S20+, 12GB) | `100.84.40.95` / `R3CN40CJJ1R` (Router USB ADB / 24/7 Power) | **9.0 GB** | Rank 5 (Fills Fifth) |

## 🧬 24/7 LoRA Fine-Tuning Sink
All verified code diffs, debate outcomes, and audit corrections are continuously serialized to `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets/`.

## 🔗 Related Notes
- [[ai-debate]] — Deliberation engine governing swarm decisions.
- [[teamwork-preview]] — Multi-agent dispatch interface for complex projects.
- [[multi-wan-accelerator]] — Interconnect fabric providing high-throughput sharding.
