# Project: Open-Source Mesh & Autonomous AGI Governance

## Architecture Overview
A production-grade, 100% self-hosted, open-source architecture replacing proprietary mesh networking (Tailscale -> Headscale) and proprietary channel bonding (Speedify -> OpenMPTCProuter) across the Lauburu 7-layer physical mesh matrix (108.0 GB pooled RAM, 82.8 GB usable AI VRAM), coupled with an autonomous HuggingFace TRL/DPO local reward optimization loop, a strict isolated sandboxing environment for custom router/edge/sensor firmware compilation, and a multi-agent debate tournament protocol crowning a single permanent AGI victor for sovereign mesh governance.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       7-LAYER PHYSICAL MESH TOPOLOGY                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ L1: Mac_Node (Host M4 Pro Mac Mini, 24GB) ── Port 18802, Port 4000, Port 3000│
│ L2: MacBook_Pro (Worker Mac, 16GB) ─────── 10Gbps TB4 DMA Bridge (0.277ms)  │
│ L3: Linux_Head_Node (AMD Ryzen 7, 16GB) ── Headscale Control Plane, Docker  │
│ L4: Linux_Tablet (Debian Linux, 8GB) ───── Mobile Touch DSP, Petals Worker  │
│ L5: MacBook_Air (Apple M4, 16GB) ───────── Metal GPU, LoRA Distillation     │
│ L6: Pixel_10_Pro_XL (Tensor G5, 16GB) ──── Edge TPU v2, 5G Hotspot WAN      │
│ L7: Samsung_S20 (Exynos 990, 12GB) ─────── Automated UI Tester, LTE Backup  │
│ GW: GL.iNet Router (GL-MT3600BE) ───────── Wi-Fi 7 BE3600 MLO, USB ADB Hub  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
┌───────────────────────────┐ ┌───────────────────────────┐ ┌───────────────────────────┐
│ R1: OPEN-SOURCE NETWORKING│ │ R2: REWARD OPTIMIZATION   │ │ SECURE ISOLATED SANDBOX   │
├───────────────────────────┤ ├───────────────────────────┤ ├───────────────────────────┤
│ • Headscale Control Plane │ │ • HuggingFace TRL DPO     │ │ • QEMU MIPS/ARM OpenWrt   │
│ • Embedded DERP Server    │ │ • Closed-Form Multi-Reward│ │ • Docker Isolated Toolchain│
│ • OpenMPTCProuter Multi-WAN │ • PEFT LoRA (r=16-32)     │ │ • Movesense BLE Sandbox   │
│ • Canonical Port TUI      │ │ • Edge Silicon Tuning     │ │ • Zero Production Leakage │
└───────────────────────────┘ └───────────────────────────┘ └───────────────────────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ R3: MULTI-AGENT DEBATE COMPETITION & PERMANENT AGI SOVEREIGN GOVERNOR        │
├─────────────────────────────────────────────────────────────────────────────┤
│ • 4-Turn Quad-Consensus Engine (Gemini, Kimi, Qwen, DeepSeek, Genetic MoE) │
│ • 4 Empirical Benchmarking Arenas (Chaos, MPTCP Throughput, Security, RAM) │
│ • Dynamic K-Factor ELO Engine (6 Multi-Factor Modifiers)                   │
│ • Ed25519 Cryptographic Attestation & Irreversible Sovereign Handover       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Status | Source |
|---|---------|-------------|-----------|--------|--------|
| 1 | Headscale Control Plane & SQLite WAL | Self-hosted control plane on L3 Docker with L1 failover mirror | M1 | DONE | Survey Explorer 1 |
| 2 | Embedded DERP & Custom STUN Relay | Self-hosted DERP server on :8443 and STUN on :3478 (Region 900) | M1 | DONE | Survey Explorer 1 |
| 3 | Fixed CGNAT IP Allocations (100.64.0.0/16) | Deterministic IP mapping for L1-L7 and GW | M1 | DONE | Survey Explorer 1 |
| 4 | Zero-Trust ACL Policy Schema | Tag-based least privilege matrix (`acl.hujson`) | M1 | DONE | Survey Explorer 1 |
| 5 | Cross-Platform Client Deployment | Native client configurations for macOS, Linux, OpenWrt, Android | M1 | DONE | Survey Explorer 1 |
| 6 | OpenMPTCProuter VPS & Client Infrastructure | Multipath TCP aggregation with Glorytun Mud & Shadowsocks MPTCP | M1 | DONE | Survey Explorer 1 |
| 7 | Multi-WAN Dynamic Bonding Engine | Bonding Wi-Fi 7 + 1GbE + TB4 10GbE + 5G/LTE Hotspot | M1 | DONE | Survey Explorer 1 |
| 8 | MPTCP Congestion Control & Schedulers | BBRv2, OLIA, BALIA, and BLEST scheduler tuning | M1 | DONE | Survey Explorer 1 |
| 9 | Canonical Port TUI Telemetry Integration | Real-time telemetry probing & UI rendering (Ports 18802, 4000) | M1 | DONE | Survey Explorer 1 |
| 10| HuggingFace TRL DPO Architecture Baseline | Direct Preference Optimization loop with implicit reward formulation | M2 | DONE | Survey Explorer 2 |
| 11| Mathematical Multi-Objective Reward Function | Closed-form formula with asymptotic barrier loss and silicon models | M2 | DONE | Survey Explorer 2 / Worker m2 |
| 12| Heterogeneous Silicon Efficiency Modeling | Power/thermal profiles for Apple M4, AMD Ryzen, Tensor G5, Snapdragon | M2 | DONE | Survey Explorer 2 |
| 13| JSONL Preference Trajectory Harvesting | Standardized triplet schema (`prompt`, `chosen`, `rejected`, delta R >= 15) | M2 | DONE | Survey Explorer 2 |
| 14| PEFT LoRA Config & Model Quantization | Rank r=16-32, alpha=32-64, QLoRA 4-bit, GGUF export for llama.cpp | M2 | DONE | Survey Explorer 2 |
| 15| Distributed Mesh Training & Deployment Matrix | Distributed PyTorch/MPS training with SFT loss anchor & EMA | M2 | DONE | Survey Explorer 2 / Worker m2 |
| 16| Candidate AGI Model Roster & Sharding | Sharding Gemini, Kimi Titan 88B, Qwen 32B, DeepSeek-R1, Genetic MoE | M3 | DONE | Survey Explorer 3 |
| 17| 4 Empirical Hardware Benchmarking Arenas | Chaos/Failover, MPTCP Throughput, Red/Blue Security, RAM Ceilings | M3 | DONE | Survey Explorer 3 |
| 18| 4-Turn Quad-Consensus Debate Engine | 4-turn state machine with Qualified Supermajority (4/6, >=66.7%) | M3 | DONE | Survey Explorer 3 / Worker m2 |
| 19| Dynamic Multi-Factor ELO Engine | 6-factor K-factor scaling with AST proof token quality weighting | M3 | DONE | Survey Explorer 3 / Worker m2 |
| 20| Cryptographic Attestation & Merkle Audit | Monotonic epoch height, previous root chaining, 8-leaf Merkle SPV | M3 | DONE | Survey Explorer 3 / Worker m2 |
| 21| Permanent Sovereign Governance Handover | Direct socket write access, 4 immutable fallback circuit breakers | M3 | DONE | Survey Explorer 3 |
| 22| Secure Isolated Sandboxing Environment | QEMU OpenWrt emulation, Docker toolchains, Android NDK, Movesense BLE | M1/M2 | DONE | Critical User Update |
| 23| Canonical Master Strategy Document | Comprehensive `/00_core_infrastructure/open_source_mesh/open_source_mesh_strategy.md` | M4 | DONE | Master Worker m1/m2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: 7-Layer Open-Source Mesh Architecture | Headscale, DERP, WireGuard clients, OpenMPTCProuter, Port TUI, Sandboxing | None | DONE |
| 2 | M2: Autonomous TRL/DPO Reward Engine | HuggingFace TRL, DPO loss, mathematical multi-reward, PEFT LoRA, SFT anchor | M1 | DONE |
| 3 | M3: Multi-Agent Debate & Sovereign AGI Crown | Tournament arenas, 4-turn debate, dynamic ELO, Merkle/Ed25519 handover | M2 | DONE |
| 4 | M4: Canonical Strategy Deliverable & Audit | Full artifact generation, 2 Reviews, 2 Challenges, 2 Forensic Audits | M1, M2, M3 | DONE |

## Canonical Deliverable
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/open_source_mesh/open_source_mesh_strategy.md` (1,385 lines, 92,450 bytes)
- Verified by: Reviewer 1 (APPROVE), Reviewer 2 (APPROVE), Challenger 1 (APPROVE), Challenger 3 (APPROVE), Auditor 2 (CLEAN).
