---
title: "SWE-bench CLI (sb-cli) Integration & Evaluation Engine"
date: "2026-08-31 15:39:00"
tags: [swe_bench, sb_cli, benchmarking, evaluation, lora_training, 2026]
subsystem: "02_ai_models_and_inference/benchmarks"
---

# 💻 SWE-bench CLI (`sb-cli`) Integration

Integration of the official [SWE-bench CLI](https://www.swebench.com/sb-cli/) into the Lauburu Mesh Ecosystem for autonomous software engineering benchmarking, prediction payload generation, and leaderboard reporting.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SWE-BENCH CLI (sb-cli) ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. CLI Binary:          `sb-cli` (installed via uv with typing-extensions) │
│ 2. Programmatic Engine: `02_ai_models_and_inference/benchmarks/sb_cli_adapter.py`│
│ 3. Harness Adapter:     `SweBenchHarness.submit_to_official_swebench()`     │
│ 4. Supported Subsets:   `swe-bench-m`, `swe-bench_lite`, `swe-bench_verified`│
│ 5. Reports Directory:   `02_ai_models_and_inference/reports/sb_cli_reports` │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🛠️ CLI Command Reference

| Command | Purpose | Arguments / Options |
| :--- | :--- | :--- |
| `sb-cli gen-api-key` | Request new API key | `{email}` |
| `sb-cli verify-api-key` | Confirm verification code | `{verification_code}` `[--api_key]` |
| `sb-cli get-quotas` | Check authorized quota limits | `[--api_key]` |
| `sb-cli submit` | Submit predictions file | `{subset}` `{split}` `--predictions_path` `[--run_id]` `[--output_dir]` |
| `sb-cli get-report` | Fetch evaluation report for run | `{subset}` `{split}` `{run_id}` `[--output_dir]` |
| `sb-cli list-runs` | List account run IDs | `{subset}` `{split}` |
| `sb-cli delete-run` | Delete specific run | `{subset}` `{split}` `{run_id}` |

## 🧬 Monorepo Workflow

1. **Prediction Generation:** `SweBenchHarness` evaluates local models (e.g. Qwen 2.5 Coder 32B, AgentWorld 35B) and generates canonical `preds.json`.
2. **Official Submission:** `SbCliAdapter.submit_predictions()` uploads `preds.json` to the SWE-bench evaluation cluster.
3. **Continuous LoRA Ingestion:** Passing resolution trajectories are automatically harvested to `swe_bench_solutions.jsonl` for continuous fine-tuning.

---
[[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]] | [[SWEBENCH_MESH_LEADERBOARD_2026]] | [[Index]]
