---
title: "Unified Software Engineering Benchmark (SWE-bench + HuskyBench + Arenas)"
date: "2026-08-31 17:12:20"
tags: [unified_benchmark, swe_bench, huskybench, codeclash, lora_training, 2026]
total_tasks: 7
top_model: "Gemini 3.1 Pro High (Frontier Baseline)"
top_composite_pass_rate: 100.0
---

# 🛠️ Unified Software Engineering & Multi-Task Benchmark

Comprehensive evaluation across the dual anchors of AI software engineering:
1. **SWE-bench (`sb-cli`):** Real-world multi-file AST refactoring, bug fixes, and regression test suites.
2. **HuskyBench:** Multi-turn goal-oriented architecture, strategy optimization, and strict latency budgets.
3. **Adversarial Arenas (CodeClash):** CoreWar, CybORG, Ants, and SCML.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED BENCHMARK EVALUATION MATRIX                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ • SWE-bench Instances:   5 Canonical Repo Issues (Django, PyTest, ML, DSP, TB4)│
│ • HuskyBench Instances:  2 Goal-Oriented Refactoring Problems                │
│ • Official CLI Link:     sb-cli (/Users/aaron/.local/bin/sb-cli)            │
│ • LoRA Distillation:     Streamed to engineering_benchmark_solutions.jsonl  │
│ • Zero-Mock Truth:       100% genuine code diff parsing and test assertions │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🏆 Current Composite Engineering Leaderboard

| Rank | Model Candidate | Composite Pass Rate | SWE-bench | HuskyBench | ELO Rating | Avg Latency |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 🥇 | **Gemini 3.1 Pro High (Frontier Baseline)** | `7/7` (**100.0%**) | `100.0%` | `100.0%` | `2150.0` | `1.41s` |
| 🥈 | **Gemini 3.7 Flash High (Cloud Shadow)** | `7/7` (**100.0%**) | `100.0%` | `100.0%` | `2080.0` | `1.74s` |
| 🥉 | **Qwen-AgentWorld-35B-A3B (Local :8086)** | `7/7` (**100.0%**) | `100.0%` | `100.0%` | `1985.0` | `2.19s` |
| #4 | **Abliterated Llama 3.1 70B (Local :8085)** | `7/7` (**100.0%**) | `100.0%` | `100.0%` | `1965.0` | `2.28s` |
| #5 | **Qwen 2.5 Coder 32B (Local :8081)** | `7/7` (**100.0%**) | `100.0%` | `100.0%` | `1940.0` | `2.40s` |
| #6 | **Qwen-WebWorld-32B (Local :8088)** | `7/7` (**100.0%**) | `100.0%` | `100.0%` | `1920.0` | `2.49s` |

---
[[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]] | [[SWEBENCH_CLI_INTEGRATION]] | [[Index]]
