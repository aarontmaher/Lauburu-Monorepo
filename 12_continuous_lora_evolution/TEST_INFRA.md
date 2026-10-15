# E2E Test Infra: Autonomous 24/7 AI Training Optimization Engine

## Test Philosophy
- **Opaque-box & Requirement-Driven**: Tests derive directly from `ORIGINAL_REQUEST.md` and user requirements, not implementation internals.
- **Rule #0 Zero-Mock & Zero-Fake**: Real datasets, genuine PyTorch/MPS tensors, authentic tokenizer models, and live filesystem structures.
- **Zero Cloud Spend**: 100% of tests execute locally on Apple Silicon / macOS.
- **Methodology**: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.

## Feature Inventory & Test Coverage Goals
| # | Feature | Scope | Tier 1 (Features) | Tier 2 (Boundaries) | Tier 3 (Interactions) |
|---|---------|-------|:-----------------:|:-------------------:|:---------------------:|
| 1 | F1: MPS Device Accelerator & Precision Engine | PyTorch MPS Float16/BFloat16 ops | $\ge 5$ | $\ge 5$ | ✓ |
| 2 | F2: Gradient Stability & Norm Clipper | Max norm $\le 1.0$, 0 NaN/Inf checks | $\ge 5$ | $\ge 5$ | ✓ |
| 3 | F3: Micro-Batcher & Gradient Accumulator | Memory-efficient accumulation | $\ge 5$ | $\ge 5$ | ✓ |
| 4 | F4: Dynamic RAM Governor & Memory Sentinel | $\le 90\%$ cap, $\ge 2.5\text{ GB}$ headroom | $\ge 5$ | $\ge 5$ | ✓ |
| 5 | F5: Multi-Schema Dataset Ingestion | DPO, SFT, CoT, Messages formats | $\ge 5$ | $\ge 5$ | ✓ |
| 6 | F6: Multi-Tier Sample Deduplicator | SHA-256 exact & SimHash LSH | $\ge 5$ | $\ge 5$ | ✓ |
| 7 | F7: Tokenizer Alignment Validator | Vocab size, special tokens, BOS/EOS | $\ge 5$ | $\ge 5$ | ✓ |
| 8 | F8: Dynamic ChatML / Header Formatter | Role template rendering | $\ge 5$ | $\ge 5$ | ✓ |
| 9 | F9: 80/20 Stratified Replay Buffer | Domain preservation reservoirs | $\ge 5$ | $\ge 5$ | ✓ |
| 10 | F10: AST Compiler Gate & Zero-Mock Check | Syntax checking & mock filtering | $\ge 5$ | $\ge 5$ | ✓ |
| 11 | F11: MPS DPO Bradley-Terry Loss Engine | Sigmoid log-ratio loss on MPS | $\ge 5$ | $\ge 5$ | ✓ |
| 12 | F12: MergeKit Configuration Manifests | Qwen 3.8, SmolLM2, Llama 3.2 YAMLs | $\ge 5$ | $\ge 5$ | ✓ |
| 13 | F13: Native In-Memory Tensor Merger | TIES, DARE-TIES, SLERP tensor math | $\ge 5$ | $\ge 5$ | ✓ |
| 14 | F14: GGUF Quantization Pipeline | FP16 conversion & Q4_K_M/IQ2_XXS | $\ge 5$ | $\ge 5$ | ✓ |
| 15 | F15: Inference Server Hot-Reload Sentinel | Ports 8081/8082/8083 health & reload | $\ge 5$ | $\ge 5$ | ✓ |
| 16 | F16: Zero-Cost Tri-Vault Auto-Publisher | Obsidian note, PySpark lake, Git | $\ge 5$ | $\ge 5$ | ✓ |
| 17 | F17: 24/7 Autonomous Evolution Loop | End-to-end continuous cycle | $\ge 5$ | $\ge 5$ | ✓ |

## Test Architecture
- **Runner**: `tests/e2e/run_e2e_tests.py` executable via Python (`/Users/aaron/DFS_UNIFIED/lora_datasets/.venv/bin/python3`).
- **Pass/Fail Semantics**: Exit code 0 on 100% pass; non-zero on any failure.
- **Reporting**: Structured JSON and markdown summary output.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Continuous DPO Distillation Cycle | F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11 | High |
| 2 | Tri-Model TIES/DARE Weight Merge & Quantization | F12, F13, F14, F15, F16 | High |
| 3 | Sudden RAM Pressure & Headroom Self-Healing | F3, F4, F1, F15 | High |
| 4 | Poisoned Data Ingestion & AST/Mock Quarantine | F5, F6, F10, F9 | Medium |
| 5 | Cross-Family Tokenizer Mismatch Pre-Flight Rejection | F7, F8, F5, F11 | Medium |
| 6 | 24/7 Multi-Cycle Adapter Evolution & Server Reload | F1, F4, F9, F11, F13, F14, F15, F16, F17 | High |
| 7 | Zero-Cost Obsidian & PySpark Ledger Synchronization | F16, F17 | Low |
| 8 | Multi-Turn CoT Thought Stream Fine-Tuning | F5, F8, F1, F2, F10 | Medium |
| 9 | High-Density Telemetry Stream Deduplication (90%+ cut) | F5, F6, F9 | Medium |

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: $\ge 85$ test cases ($\ge 5$ per feature across 17 features)
- **Tier 2 (Boundary & Corner)**: $\ge 85$ test cases ($\ge 5$ per feature across 17 features)
- **Tier 3 (Cross-Feature Combinations)**: $\ge 17$ test cases (pairwise coverage)
- **Tier 4 (Real-World Scenarios)**: $\ge 9$ test cases ($\max(5, 17/2)$)
- **Total Minimum**: $\ge 196$ test cases
