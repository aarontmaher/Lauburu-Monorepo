---
title: "Unified Engineering Benchmarks (SWE-bench + HuskyBench + CodeClash)"
date: "2026-08-31 16:02:00"
tags: [unified_benchmarks, swe_bench, huskybench, codeclash, engineering_anchor, 2026]
subsystem: "02_ai_models_and_inference/benchmarks"
---

# ⚓ Foundational Software Engineering Benchmarks

Integration of the dual software engineering anchors and competitive game arenas to evaluate AI coding models on:
1. **SWE-bench (`sb-cli`):** Real-world multi-file AST refactoring, bug fixes, and regression test suites.
2. **HuskyBench:** Multi-turn goal-oriented architecture, strategy optimization, and strict latency budgets.
3. **Adversarial Arenas (CodeClash):** CoreWar (memory safety), CybORG (threat mitigation), Ants (swarm), SCML (negotiation).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   COMPLEMENTARY BENCHMARK ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Unified Harness:     02_ai_models_and_inference/benchmarks/unified_engineering_benchmark.py
│ 2. SWE-bench Adapter:   02_ai_models_and_inference/benchmarks/sb_cli_adapter.py
│ 3. CodeClash Suite:     02_ai_models_and_inference/benchmarks/codeclash/   │
│ 4. LoRA Harvesting:     /Users/aaron/DFS_UNIFIED/lora_datasets/engineering_benchmark_solutions.jsonl
│ 5. Reports Directory:   obsidian_vault/04_ANALYTICS/UNIFIED_ENGINEERING_BENCHMARK_2026.md
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📊 Evaluation Metrics

| Benchmark Anchor | Primary Focus | Metric Evaluated |
| :--- | :--- | :--- |
| **SWE-bench** | Real GitHub Issues | Resolved / Total Tasks, Golden PyTest Assertions, Token Efficiency |
| **HuskyBench** | Goal-Oriented Development | Multi-turn Bot Optimization, Bankroll ROI, ≤10s Execution Budget |
| **CoreWar / CybORG** | Adversarial Boundaries | Low-level Pointer Safety, Network Threat Mitigation, Win/Tie Rates |

---
[[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]] | [[SWEBENCH_CLI_INTEGRATION]] | [[Index]]
