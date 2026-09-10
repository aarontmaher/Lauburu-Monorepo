---
title: "NVIDIA Agent Skills Catalog & Developer Tools Reverse Engineering Specification"
tags: [nvidia, agent_skills, developer_tools, reverse_engineering, doca, warp, nemo, cuopt, holoscan, jetson, deep_research]
date: "2026-09-07"
consensus_score: 1.00
tri_vault_layer: "obsidian_vault"
---

# 🔬 NVIDIA Agent Skills Catalog & Developer Tools Reverse Engineering Specification

## 🏛️ Executive Summary & Ground Truth Architecture

Investigation of `https://build.nvidia.com/skills` and `https://build.nvidia.com/skills?filters=domain%3Adomain_developer_tools` using the **Deep Research**, **Open-Source Software Scout**, and **Closed-Source Reverse Engineering** protocols reveals the unified foundation of NVIDIA's portable AI Agent Skills ecosystem (`github.com/NVIDIA/skills`).

NVIDIA has published a repository containing **350+ production agent skills**, designed around the open **Agent Skills Specification** (`SKILL.md` + YAML frontmatter + OpenAPI schemas + CLI invocation). These skills are portable across any compliant agent environment (including Antigravity `.gemini/config/skills/`, Claude Code `.claude-plugin/`, Cursor `.cursor-plugin/`, and OpenAI Codex).

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           NVIDIA AGENT SKILLS ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. DISCOVERY & CATALOG LAYER                                                            │
│    • Web Hub: build.nvidia.com/skills (Taxonomy Filters: 6 Domains, 25 Subdomains)      │
│    • Repository: github.com/NVIDIA/skills (350+ Verified Skills)                        │
│    • Public Directory: skills.sh / skills.sh.json                                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. DELIVERY & PACKAGING LAYER                                                           │
│    • CLI Tooling: npx skills add nvidia/skills --skill <name> --agent <agent-name>      │
│    • Lockfile Support: skills-lock.json for deterministic, reproducible team deployments │
│    • Agent Interoperability: .agents/plugins/marketplace.json, .claude-plugin/, etc.    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. SECURITY & CRYPTOGRAPHIC GOVERNANCE LAYER                                            │
│    • Static Security Scanner: SkillSpector (github.com/NVIDIA/SkillSpector)             │
│    • Cryptographic Attestation: skill.oms.sig signed by nv-agent-root-cert.pem          │
│    • Permission Sandbox: explicit allowed-tools AST filtering (Bash, Read, Grep, Glob)  │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. RUNTIME EXECUTION & MCP BRIDGING                                                     │
│    • Canonical MCP Servers: e.g. NemoClaw Docs MCP (docs.nvidia.com/nemoclaw/_mcp/server)│
│    • Machine-Readable LLM Grounding: llms.txt & Markdown-first documentation mirrors    │
│    • Session Durability: Session memory checkpoints for multi-turn agent persistence    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ 1. Complete Catalog Taxonomy & Domain Mapping

The NVIDIA catalog categorizes its 350 skills across **6 primary categories** (`classification.category.primary`):

| Primary Category Enum | build.nvidia.com Filter Parameter | Total Skills | Description |
| :--- | :--- | :--- | :--- |
| `ai_and_machine_learning` | `filters=domain%3Adomain_ai_and_machine_learning` | 169 | RAG blueprints, NeMo training/alignment, TAO, vLLM, TensorRT-LLM |
| `physical_ai` | `filters=domain%3Adomain_physical_ai` | 69 | Robotics, Isaac Sim, Jetson BSP, sensor calibration, autonomous vehicles |
| `infrastructure` | `filters=domain%3Adomain_infrastructure` | 47 | Kubernetes, Helm, Slurm, cluster telemetry, GPU operator |
| `accelerated_computing` | `filters=domain%3Adomain_accelerated_computing` | 31 | CUDA kernels, cuDF, cuPyNumeric, profiling, cuFFT, CUTLASS |
| **`developer_tools`** | **`filters=domain%3Adomain_developer_tools`** | **30** | **Compiler optimization, DPU networking, agent routing, memory, debuggers** |
| `graphics_and_media` | `filters=domain%3Adomain_graphics_and_media` | 4 | Omniverse, USD, real-time ray tracing, video transcoding |

---

## 🛠️ 2. Comprehensive Deep Dive: The 30 Developer Tools Skills

The URL `https://build.nvidia.com/skills?filters=domain%3Adomain_developer_tools` exposes 30 specialized skills focused on kernel acceleration, BlueField DPU networking, differentiable computing, edge systems, and agent orchestration:

### A. Meta-Agent Orchestration & Governance (5 Skills)
1. **`nvidia-skill-finder`** (`product: Learning`, `subdomain: agentic-ai`):
   - **Function:** Intent classifier and router that listens for arbitrary developer queries (CUDA, NIM, NeMo, Jetson, RAPIDS, etc.) and routes them to the appropriate NVIDIA skill.
2. **`nemoclaw-user-guide`** (`product: NemoClaw`, `subdomain: agentic-ai`):
   - **Function:** Guides AI coding agents through NemoClaw installation, setup, and MCP integration via `https://docs.nvidia.com/nemoclaw/_mcp/server` and `llms.txt`.
3. **`skill-card-generator`** (`product: Trustworthy AI`, `subdomain: agentic-ai`):
   - **Function:** Automatically generates governance and compliance cards (`skill-card.md`) documenting capability boundaries, tool permissions, and vulnerability audits.
4. **`nemo-relay-instrument-context-isolation`** (`product: NeMo`, `subdomain: agentic-ai`):
   - **Function:** Implements asynchronous scope stacks and context propagation for concurrent agent requests, threads, and background workers.
5. **`nemo-rl-session-memory`** (`product: NeMo RL`, `subdomain: training-ai`):
   - **Function:** Manages durable, persistent session memory under `./session/<timestamp>/` to preserve agent state across disconnects, IDE restarts, and multi-hour tasks.

### B. High-Performance BlueField DPU & DOCA Networking (13 Skills)
6. **`doca-common`**: Core context lifecycle (`doca_ctx`), device discovery (`doca_dev`), and progress engines (`doca_pe`).
7. **`doca-programming-guide`**: Library-agnostic C11 DOCA app development, Meson/pkg-config build pipelines, and Rust/Go/Python FFI bindings.
8. **`doca-setup`**: Environment validation (Hugepages, devlink, `LD_LIBRARY_PATH`, network representors).
9. **`doca-version`**: 4-way version parity verification across `pkg-config doca-common`, `applications/VERSION`, `doca_caps --version`, and BlueField OS release.
10. **`doca-argp`**: Hands-on command-line argument parser CLI construction and parameter validation.
11. **`doca-bench`**: Microsecond-precision benchmarking for RDMA, DMA, AES-GCM, SHA, Comch, and GPUNetIO.
12. **`doca-bench-extension`**: Development of custom C dynamic shared libraries (`.so`) for synthetic workload profiling.
13. **`doca-comm-channel-admin`**: Enumeration and inspection of host↔DPU communication channels (comch) and connection tables.
14. **`doca-debug`**: Systematic debug ladder for compiler link errors, `DOCA_ERROR_*` runtime exceptions, Valgrind memory leaks, and core dumps.
15. **`doca-devemu`**: Hands-on PCIe device emulation on BlueField DPUs (exposing emulated NVMe/virtio-net hardware to host OS).
16. **`doca-dpa-hl-tracer`**: Hardware-level trace capture and decoding on the Data Path Accelerator (DPA) RISC-V cores.
17. **`doca-public-knowledge-map`**: Authoritative documentation mapping across NVIDIA BlueField knowledge bases.
18. **`doca-structured-tools-contract`**: Unified JSON/structured diagnostic CLI outputs for automated agent parsing.

### C. Differentiable Simulation & GPU Kernel Optimization (4 Skills)
19. **`warp-compile-time-optimizer`** (`product: Warp`, `subdomain: gpu-development`):
    - **Function:** Minimizes JIT compilation latency and module startup overhead for Python-embedded Warp GPU kernels (`wp.launch`).
20. **`warp-debug-gradients`** (`product: Warp`, `subdomain: gpu-development`):
    - **Function:** Diagnoses and repairs gradient bugs in differentiable physics/robotics simulations using `wp.Tape` (remedies exploding gradients, NaNs, plateaus).
21. **`holohub-debug-build-run`** (`product: Holoscan`, `subdomain: physical-ai`):
    - **Function:** Real-time debugging and verification for Holoscan streaming sensor pipelines.
22. **`holohub-module-lifecycle`** (`product: Holoscan`, `subdomain: gpu-development`):
    - **Function:** Holoscan C++/Python module scaffolding, test runner, and packaging (DEB / Wheel).

### D. Edge Computing & Embedded Hardware (4 Skills)
23. **`jetson-quick-start`** (`product: Jetson`, `subdomain: physical-ai`): Interactive hardware questionnaire and setup guide for Jetson Orin / IGX systems.
24. **`jetson-init-source`** (`product: Jetson`, `subdomain: physical-ai`): Initializes BSP workspace, `Linux_for_Tegra` overlay tracker, and `crosstool-ng` toolchain.
25. **`jetson-build-source`** (`product: Jetson`, `subdomain: physical-ai`): Compiles Device Tree (`dtb`), out-of-tree kernel modules, and Linux kernels.
26. **`jetson-generate-kb`** (`product: Jetson`, `subdomain: infrastructure`): Generates target-specific architecture Markdown knowledge bases by walking the BSP source tree.

### E. Combinatorial Optimization, Simulation & FPGA (4 Skills)
27. **`cuopt-developer`** (`product: cuOpt`, `subdomain: decision-optimization`): Modifies, builds, and tests NVIDIA cuOpt CUDA C++ solver internals, linear programming routines, and combinatorial vehicle routing engines.
28. **`hsb-ip-create-top`** (`product: Holoscan`, `subdomain: gpu-development`): Synthesizes fixed-format SystemVerilog (`FPGA_top.sv`) wrappers for Holoscan Sensor Bridge (HSB).
29. **`earth2studio-create-datasource`** (`product: Earth2Studio`, `subdomain: simulation-modeling`): Builds high-performance streaming data source wrappers for planetary climate simulations.
30. **`nemo-rl-docs`** (`product: NeMo RL`, `subdomain: training-ai`): Enforces documentation formatting and docstring standards for reinforcement learning pipelines.

---

## 🔬 3. Clean-Room Architectural Reverse Engineering: The NVIDIA Skill Standard

By disassembling the files in `github.com/NVIDIA/skills`, we identify the 5 fundamental components of NVIDIA's skill specification:

### 1. The Anatomy of a `SKILL.md`
Every skill maintains a standardized declarative YAML frontmatter:
```yaml
---
name: <kebab-case-name>
version: "X.Y.Z"
description: "Precise intent description including trigger phrases and negative routing boundaries"
license: "Apache-2.0"
compatibility: "Operating system, hardware prerequisites, Python/C++ toolchain"
metadata:
  author: "Responsible engineering team"
  github-url: "Upstream source repository"
  tags: ["keyword1", "keyword2"]
  languages: ["python", "c", "bash"]
  frameworks: ["docker-compose", "cuda"]
  classification.category.primary: "developer_tools"
  catalog.subdomain: "networking"
allowed-tools: Bash(...) Read Grep Glob
---
```

### 2. The Cryptographic Provenance Model (`skill.oms.sig`)
NVIDIA implements cryptographically signed skills to protect against supply-chain prompt injection.
- **Root Certificate:** `nv-agent-root-cert.pem`
- **Skill Signature:** `skill.oms.sig` (containing ECDSA SHA-256 signature of the `SKILL.md` content)
- **Static Audit:** Verified via `SkillSpector` (`github.com/NVIDIA/SkillSpector`) before inclusion in `skills.sh.json`.

### 3. Client Distribution Contract
The open CLI `npx skills add <repo> --skill <name>` operates by:
1. Cloning/querying the remote GitHub tree.
2. Resolving target client agent directories:
   - Antigravity / Gemini: `.gemini/config/skills/<name>/SKILL.md` or `.agents/skills/<name>/SKILL.md`
   - Claude Code: `.claude/skills/<name>/`
   - Cursor: `.cursor/skills/<name>/`
3. Writing a cryptographic lockfile (`skills-lock.json`).

---

## 🌐 4. Cross-System Synthesis with the Lauburu Mesh

The Lauburu Mesh Ecosystem (`/Users/aaron/DFS_UNIFIED`) already implements an equivalent, sovereign multi-agent architecture:

| Capability | NVIDIA Architecture | Lauburu Sovereign Architecture |
| :--- | :--- | :--- |
| **Catalog Repository** | `github.com/NVIDIA/skills` (350 skills) | `/Users/aaron/DFS_UNIFIED/.agents/skills/` (55+ skills) |
| **Meta Router** | `nvidia-skill-finder` | `loop` (Omnipresent Skill Router & Generational Optimizer) |
| **Durable Session Memory** | `nemo-rl-session-memory` (`./session/`) | Tri-Vault Storage (`obsidian_vault/`, `lora_datasets/`, Git) |
| **Context Isolation** | `nemo-relay-instrument-context-isolation` | Antigravity Subagent Isolation & Task Management |
| **MCP Integration** | NemoClaw Docs MCP (`docs.nvidia.com/...`) | Antigravity Native MCP Fleet (41 Obsidian tools, Docker, etc.) |
| **Zero-Spend Inference** | NIM Free Tier APIs (`build.nvidia.com`) | Sovereign Local AI (`Qwen 3.8 Max` Port 8082 + NIM Free Tier) |

---

## 🏛️ 5. Deployment Verification & Installed Manifest

On 2026-09-07, the top 6 high-ROI skills were installed into the monorepo via `npx skills add` and validated:

1. **`nemoclaw-user-guide`** (`.agents/skills/nemoclaw-user-guide`): Full guidance on OpenClaw/NemoClaw sandbox configuration and MCP integration.
2. **`nemo-rl-session-memory`** (`.agents/skills/nemo-rl-session-memory`): Structured checkpointing under `./session/<timestamp>/` (`session_state.md`, `open_questions.md`).
3. **`nemo-relay-instrument-context-isolation`** (`.agents/skills/nemo-relay-instrument-context-isolation`): Async scope stack isolation across concurrent swarms.
4. **`skill-card-generator`** (`.agents/skills/skill-card-generator`): Automated governance card generation (`skill-card.md`) for all 55+ monorepo skills.
5. **`warp-compile-time-optimizer`** (`.agents/skills/warp-compile-time-optimizer`): JIT startup latency reduction for 3D physics kernels.
6. **`warp-debug-gradients`** (`.agents/skills/warp-debug-gradients`): Reverse-mode autodiff debugging (`wp.Tape`) for 3D spatial grappling joint torque.

### NemoClaw Docs MCP Server Registration
- **Server Name:** `nemoclaw-docs`
- **Config File:** `/Users/aaron/.gemini/config/mcp_config.json`
- **Transport:** Streamable HTTP / Server-Sent Events (`https://docs.nvidia.com/nemoclaw/_mcp/server`)
- **Exposed Tool:** `searchDocs(query: string, topK: integer)`

---

## 🔗 Related Knowledge Links
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[AI_DEBATE_LOOP_EFFECTIVENESS_TOOL_ROI_AND_NPU_LENS_SHARDING]]
- [[Index]]
