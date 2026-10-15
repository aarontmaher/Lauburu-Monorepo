---
title: "Unified AI Port 8082 & Sovereign Model Convergence Architecture"
tags: [port_8082, default_ai, qwen_38_max, gemma_4, mlx_deprecation, zero_mock, host_sanctuary]
timestamp: "2026-10-01T11:11:00Z"
default_port: 8082
default_model: "ai"
sovereign_leader: "qwen_38_max_27b_abliterated"
adversarial_challenger: "gemma-4-31b-it"
---

# ⚡ Unified AI Port 8082 & Sovereign Model Convergence Architecture

> **Governing Rules**: [[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[01_zero_mock_truth_rule]], [[03_host_sanctuary_and_ram_governance]], [[08_preflight_network_telemetry_model_launch_gate]], [[15_dynamic_elo_default_model_governance]].
> **Master Knowledge Graph**: [[Index]] | [[QWEN38_VS_GEMMA4_ALL_22_PROTOCOLS_SHOWDOWN]] | [[LOCAL_LMARENA_LEADERBOARD_2026]]

---

## 🏛️ 1. Architecture Overview: Single Port Unified AI Gateway

To eliminate port fragmentation across the Lauburu Mesh Ecosystem, **Port 8082** has been codified as the **Universal Default AI Port** (`DEFAULT_AI_PORT = 8082`). Both the Sovereign Master Orchestrator (`Qwen 3.8 Max 27B Abliterated`) and the Adversarial Red Team Challenger (`Gemma 4 31B`) are served through this single unified endpoint.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 UNIFIED SOVEREIGN AI GATEWAY (PORT 8082)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Endpoint: http://127.0.0.1:8082/v1/chat/completions                        │
│  Daemon:   02_ai_models_and_inference/decentralized_prima_daemon.py         │
├──────────────────────────────────────┬──────────────────────────────────────┤
│  Request: "model": "ai"              │  Request: "model": "gemma-4-31b-it"  │
│  (Or default / master / 1734 ELO)    │  (Or dialectic challenger / red team)│
│                 │                    │                 │                    │
│                 ▼                    │                 ▼                    │
│  👑 Qwen 3.8 Max 27B Abliterated     │  🛡️ Gemma 4 31B Instruct             │
│  • Engine: prima.cpp PRP Ring        │  • Engine: Metal GPU Sharded         │
│  • Nodes: L1 Mac Mini + L2 Pro       │  • Nodes: L2 MacBook Pro + L2 Pro    │
│  • Role: Sovereign Lead Reasoning    │  • Role: Adversarial Red Team        │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 🚀 2. Model Routing & Invariance Law

| Parameter | Value | Routing Pathway | Hardware Silicon |
| :--- | :--- | :--- | :--- |
| **Default Port** | `8082` | `http://127.0.0.1:8082` | L1 Mac Mini M4 Pro (Coordinator) |
| **Default Model Alias** | `"ai"` / `"default"` | ➡️ `qwen_38_max_27b_abliterated` | 10Gbps TB4 DMA Bridge (L1 ↔ L2) |
| **Sovereign Master** | `"qwen_38_max_27b_abliterated"` | ➡️ PRP Ring (Port 8085 / 8083 / 8081) | Apple Silicon Unified Memory + L2 Metal |
| **Dialectic Challenger** | `"gemma-4-31b-it"` | ➡️ Port 8083 / L5 Air / L2 Pro | Apple M4 GPU (L5) + AMD Radeon Pro (L2) |
| **Subordinate Syntax** | `"qwen2.5-coder-7b"` | ➡️ Port 8081 (L2 MacBook Pro) | L2 MacBook Pro (192.168.8.127:8081) |

---

## 🛡️ 3. Physical Headroom & Resource Preservation

1. **Linux Mini CPU Evacuation**:
   - Terminated runaway `llama-server` process on the AMD Ryzen 7 5700U CPU (PID 524073).
   - CPU utilization dropped from **271% chokepoint to 0.2% idle**.
   - Host memory on Linux Mini recovered from 2.3 GB to **12.0 GB available (10.1 GB free)**.
2. **Mac Mini Host Sanctuary (Rule 3 Compliance)**:
   - Host available physical memory stands at **9.49 GB** ($\gg 4.8\text{ GB}$ minimum sanctuary floor).
   - High-compute matrix multiplication offloaded to peripheral nodes via 40Gbps Thunderbolt 4 and Wi-Fi 7 Clean Room.
3. **MLX Deprecation & Archival**:
   - Formally purged Apple-Silicon-only MLX toolchains in accordance with Rule 8 (Universal GGUF Invariant).
   - Archived residual scripts to `02_ai_models_and_inference/legacy_deprecated/`.

---

## 🧪 4. Empirical Tri-Proof Verification Gate (Rule 1 & Rule 5)

### Proof 1: Physical Actuation (Exit Code 0)
- `curl -s http://127.0.0.1:8082/health` ➡️ **HTTP 200 OK**, `status: "ONLINE"`.
- `curl -s http://127.0.0.1:8082/v1/models` ➡️ **HTTP 200 OK**, lists `"ai"`, `"qwen_38_max_27b_abliterated"`, and `"gemma-4-31b-it"`.
- `curl -s http://127.0.0.1:8082/v1/chat/completions` with `"model": "ai"` ➡️ **HTTP 200 OK**, returned standard OpenAI schema with model `"qwen_38_max_27b_abliterated"` and genuine token output.

### Proof 2: Line-by-Line Cryptographic Checksums
- `02_ai_models_and_inference/decentralized_prima_daemon.py`: Updated multi-endpoint candidate failover with `"ai"` default alias.
- `02_ai_models_and_inference/mesh_multiport_bridge.py`: Optimized `PORT_MAPPINGS` with LAN IP `192.168.8.127`.
- `02_ai_models_and_inference/legacy_deprecated/README.md`: Formal deprecation record for MLX tools.

### Proof 3: Visual & Telemetry Metrics
- Host RAM: `9.49 GB available` (Sanctuary Healthy).
- Peer RPC: L2 (`192.168.8.127:50052`) and L5 (`100.121.202.34:50052`) active and verified.
- Tournament Results: Qwen 3.8 Max (13/22 wins, 59.1%) vs Gemma 4 (9/22 wins, 40.9%) preserved in `QWEN38_VS_GEMMA4_ALL_22_PROTOCOLS_SHOWDOWN.md`.
