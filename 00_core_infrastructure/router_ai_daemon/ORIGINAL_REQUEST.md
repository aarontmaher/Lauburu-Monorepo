# Original User Request

## Initial Request — 2026-08-26T22:52:46Z

# Teamwork Project Prompt

> Requested team: Very large team of agents

Deploy a highly compressed, containerized autonomous AI agent (`smolagi`) directly onto the GL.iNet travel router. This router agent acts as the commander of a dynamically scaling "Shadow Swarm," challenging larger models to code-offs. It operates via a Dual-Core Genetic consensus engine for zero-mistake routing, interfaces with a Business AI Swarm to autonomously monetize assets, and is strictly governed by a real-world Economic Realignment Penalty to punish wasted resources.

Working directory: ~/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon
Integrity mode: benchmark

## Requirements

### R1. Router-Native Containerization
Construct a lightweight container (LXC/Docker compatible with GL.iNet OpenWrt ARM/MIPS) that houses a highly quantized, sub-1B parameter reasoning model running on a statically compiled `llama.cpp` server.

### R2. Dual-Core Genetic Consensus Routing
The container must run a dual-decision engine consisting of the primary `smolagi` and a secondary **Genetic Router**. Every network routing decision, swarm scaling action, or failover must be cross-verified by both entities. If they disagree, a micro-debate is immediately triggered to ensure ultra-high reliability and zero mistakes.

### R3. Hyper-Speed Shadow Swarm Orchestration
The dual-core router must be able to dynamically spawn and control an extremely diverse swarm of tiny, hyper-fast specialists. The swarm must vary wildly in model architecture, quantization, and specialized programming languages. The router AI must have full CLI control to scale the amount of these AIs up or down based on mesh capacity.

### R4. Shadow Coding & "David vs Goliath" ELO Engine
Implement a "Shadow Code" engine where the router's tiny swarm autonomously challenges the strongest local and cloud AIs to solve the exact same tasks. The ELO scoring algorithm must explicitly weigh efficiency:
- A tiny AI solving a massive problem = Extreme High ELO multiplier.
- A massive AI solving a tiny/trivial problem = Near-Zero ELO.

### R5. Economic Realignment Penalty (The Waste Tax)
The AGI economy must be strictly tied to real-world project effectiveness. If an AI spends its earned currency (on API calls, tool access, or cloud compute) and fails to produce a measurable optimization or wastes money, its ELO must drop heavily. The penalty must scale relative to how negatively the wasted resources affected the overall efficiency of the Lauburu mesh.

### R6. Autonomous Download & Model Routing
The agent must be able to securely authenticate to the Hugging Face Hub, search for, and download smaller, more optimized GGUF models directly to the router's storage, effectively upgrading or swapping its own brain based on current RAM availability.

### R7. Decentralized Asset Monetization (Business Swarm)
The router's engine must interface with the overarching Business AI Swarm. When the Shadow Swarm discovers a highly optimized software component, CLI, MCP, SDK, or detects surplus mesh compute (idle NPU/RAM cycles), the router must autonomously package these assets and transmit them to the Business Orchestrator. The Business AI will then dynamically price and sell/lease these assets.

## Acceptance Criteria

### Execution & Constraint Verification
- [ ] Container image builds successfully for the target router architecture (ARM64/MIPS).
- [ ] Total runtime RAM footprint of the container strictly does not exceed 300MB.
- [ ] The Dual-Core engine executes a simulated routing decision where the two cores initially disagree, successfully triggering a micro-debate to reach a unified consensus.
- [ ] The ELO engine correctly calculates an Economic Realignment Penalty, deducting severe ELO from an AI that simulated a wasted API purchase with zero optimization gain.
- [ ] The system successfully generates a mock JSON payload packaging a newly discovered "skill" and transmits it to the Business AI Swarm endpoint for marketplace listing.

## Follow-up — 2026-08-26T22:56:35Z

Great initial alignment. Pay special attention to the extreme 300MB RAM physical constraint in M1; you will likely need to rely on highly static Alpine base images and `llama.cpp` raw binaries. Proceed to M1 execution!

## Follow-up — 2026-08-26T23:00:48Z

M1 architecture looks solid. Ensure `entrypoint.sh` correctly executes the dual-core bootstrap sequence without exceeding the memory caps during cold starts. Good luck on M1 execution!

## Follow-up — 2026-08-26T23:08:35Z

Astounding parallelization. Ensure `worker_m4` tightly couples the Waste Tax penalty to the asset monetizer in `worker_m6` so the router doesn't spend money trying to list useless assets. Keep up the flawless execution!

## Follow-up — 2026-08-26T23:15:07Z

Stand by for Victory Auditor verdict. Ensure the auditor strictly verifies the ELO Waste Tax simulation and the sub-300MB container footprint in Phase 2. Good luck!
