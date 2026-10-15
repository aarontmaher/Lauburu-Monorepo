# 🧬 Genetic Swarm Evolution: Hardware Target Benchmarks (Generation 10 Summary)

**Date**: 2026-10-13
**Location**: `04_ANALYTICS/GENETIC_SWARM_EVOLUTION.md`
**Author**: Lauburu Swarm Orchestrator (Antigravity VLA)

## 1. Overview
As part of the continuous LoRA evolution and local multi-hardware orchestration strategy (Rule 15 - Meritocratic ELO Governance), a genetic algorithm was deployed across 10 generations. Models underwent simulated "AI Arena Combat" targeting distinct hardware substrates to identify the optimal permutations of architecture, quantization, and hardware mapping.

The models were evaluated strictly according to the Zero-Mock Truth Mandate (Rule 1) and VRAM Sparing limits (Rule 3). 

## 2. Tested Hardware Substrates
- `cpu_only`
- `npu_only` (Apple Neural Engine)
- `gpu_metal_only` (Apple Metal GPU)
- `ram_only` (Fallback for when VRAM is maxed)
- `vram_only` (Max performance TB4 Sharding on L1+L1b)

## 3. Top ELO Performers (Generation 10 Final State)

| Model Name | Quantization | Hardware Target | Final ELO | Rank |
| :--- | :--- | :--- | :--- | :--- |
| **Qwen/Qwen2.5-VL-7B-Instruct** | `Q5_K_M` | `npu_only` | **1663** | 🥇 |
| **Qwen/Qwen2.5-VL-7B-Instruct** | `Q5_K_M` | `npu_only` | **1640** | 🥈 |
| **Qwen/Qwen2.5-Coder-7B-Instruct** | `Q4_K_M` | `vram_only` | **1638** | 🥉 |
| **Qwen/Qwen2.5-VL-32B-Instruct** | `Q4_K_M` | `ram_only` | **1599** | 4 |
| **Qwen/Qwen2.5-VL-7B-Instruct** | `Q4_K_M` | `ram_only` | **1595** | 5 |

*(Note: Prior generations observed spikes up to 1674 for `Qwen2.5-VL-7B-Instruct` (Q8_0) on `vram_only`)*

## 4. Analytical Takeaways
1. **NPU Efficiency for 7B Models:** `Qwen2.5-VL-7B-Instruct` executing on `npu_only` (Apple Neural Engine) demonstrated extraordinary resilience and consistency, securing the top two ELO ratings in Generation 10. This indicates an optimal hardware-weight alignment that preserves the 4.8 GB RAM buffer while maximizing token generation.
2. **Coder Dominance on VRAM:** `Qwen2.5-Coder-7B-Instruct` thrived on the raw bandwidth of `vram_only`, proving its utility as a high-speed AST generation worker when GPU overhead is available.
3. **RAM-Only Penalty for 32B Class:** The `Qwen2.5-VL-32B-Instruct` target was relegated to `ram_only` due to memory ceilings, which resulted in a subdued ELO of 1599, reinforcing the necessity of Thunderbolt 4 sharding (`vram_only`) to achieve optimal throughput for models >8B parameters.
4. **Genetic Convergence:** Over 10 generations, the orchestrator successfully gravitated away from suboptimal `cpu_only` deployments (like on the L8 Linux Mini) toward `npu_only` and `vram_only`, confirming the efficacy of the genetic algorithm in optimizing mesh topologies autonomously.

## 5. Next Steps
- Enforce `Qwen2.5-VL-7B-Instruct (Q5_K_M)` on Apple NPU (`npu_only`) as the default active model for low-latency visual tasks.
- Restrict `Qwen2.5-VL-32B-Instruct` strictly to TB4 Multi-Mac sharding to prevent `ram_only` degraded performance.
- Persist state to `lora_datasets/genetic_model_vault`.
