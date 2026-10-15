# Project: Autonomous 24/7 AI Training Optimization Engine

## Architecture
The Autonomous 24/7 AI Training Optimization Engine operates across the 7-Layer Lauburu Mesh on Apple Silicon Metal Performance Shaders (MPS), providing continuous DPO distillation, tokenizer alignment, TIES/DARE weight merging, and GGUF quantization at $0.00 cloud spend.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              AUTONOMOUS 24/7 AI TRAINING OPTIMIZATION ENGINE                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. DATASET & TOKENIZER LAYER (Subsystem 12 / Distillation)                  │
│    • Multi-schema Ingestion (DPO, SFT, CoT, Messages) from lora_datasets/   │
│    • SHA-256 Exact & SimHash Near-Duplicate Deduplication (90%+ cut)        │
│    • 100% Tokenizer Alignment (Qwen 3.8/2.5, SmolLM2 1.7B, Llama 3.2 1B)    │
│    • 80/20 Stratified Replay Buffer (Anti-Catastrophic Forgetting)          │
│    • AST Compiler Gate & Rule #0 Zero-Mock Syntax/Stub Validator            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. MPS TRAINING & MEMORY GOVERNOR LAYER (Subsystem 12 / Trainer)            │
│    • PyTorch MPS Metal Float16/BFloat16 Optimization (M4 Pro / Unified RAM) │
│    • Strict Gradient Clipping (norm <= 1.0) & 0 NaN Gradient Detection     │
│    • Dynamic Host RAM Governor (<= 90% system cap, >= 2.50 GB Headroom)     │
│    • Micro-batching (batch_size=1/2) with Gradient Accumulation             │
│    • Bradley-Terry Sigmoid Log-Ratio DPO Loss on Metal MPS                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. WEIGHT MERGING, QUANTIZATION & SERVING LAYER (Subsystem 12 / Merging)    │
│    • MergeKit YAML Manifests (Qwen 3.8 Max, SmolLM2 1.7B, Llama 3.2 1B)     │
│    • Native PyTorch In-Memory TIES / DARE / SLERP Tensor Merging Engine     │
│    • GGUF Quantization Toolchain (Q4_K_M medium & IQ2_XXS ultra-compact)    │
│    • Hot-Reload Sentinel for Inference Daemons (Ports 8081, 8082, 8083)     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. TRI-VAULT SYNCHRONIZATION & TELEMETRY LAYER                              │
│    • Obsidian Analytics Auto-Publisher (obsidian_vault/05_TRAINING/)        │
│    • PySpark & Big Data Lake Continuous JSONL Logging (lora_datasets/)      │
│    • Git Worktree Branch Isolation & $0.00 Cloud Cost Guarantee             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1: MPS Device Accelerator & Precision Engine | PyTorch MPS backend with Float16/BFloat16 matrix operations | M1 | Survey 1 |
| 2 | F2: Gradient Stability & Norm Clipper | Strict gradient norm clamping ($\le 1.0$) with 0 NaN gradient checks | M1 | Survey 1 |
| 3 | F3: Micro-Batcher & Gradient Accumulator | Low-memory activation footprint with gradient accumulation | M1 | Survey 1 |
| 4 | F4: Dynamic RAM Governor & Memory Sentinel | Real-time RAM monitoring, $\le 90\%$ system cap, $\ge 2.50\text{ GB}$ headroom floor, and MPS cache reclamation | M1 | Survey 1 |
| 5 | F5: Multi-Schema Dataset Ingestion Engine | Ingestion of DPO pairs, SFT instruction, CoT thought, and messages datasets | M2 | Survey 2 |
| 6 | F6: Multi-Tier Sample Deduplicator | SHA-256 exact hash and SimHash near-duplicate sample filtering | M2 | Survey 2 |
| 7 | F7: Cross-Family Tokenizer Alignment Validator | Pre-flight tokenizer vocabulary and special token validation across Qwen, SmolLM2, Llama 3.2 | M2 | Survey 2 |
| 8 | F8: Dynamic ChatML / Header Formatter | Dynamic message rendering using model-native chat templates | M2 | Survey 2 |
| 9 | F9: 80/20 Stratified Replay Buffer | 80% new task pairs + 20% anchor domain replay buffer against catastrophic forgetting | M2 | Survey 2 |
| 10 | F10: AST Compiler Gate & Rule #0 Zero-Mock Validator | AST syntax validation (`ast.parse`) and mock/dummy code quarantine | M2 | Survey 2 |
| 11 | F11: MPS DPO Bradley-Terry Loss Engine | Stable sigmoid log-ratio DPO loss with clamped margins on Apple Silicon MPS | M2 | Survey 2 |
| 12 | F12: MergeKit Configuration Manifest Generator | YAML manifests for Qwen 3.8 Max (DARE-TIES), SmolLM2 1.7B (TIES), Llama 3.2 1B (SLERP) | M3 | Survey 3 |
| 13 | F13: Native PyTorch In-Memory TIES/DARE/SLERP Tensor Merger | In-memory delta weight merging with zero external binary dependency | M3 | Survey 3 |
| 14 | F14: GGUF Quantization Pipeline | Two-stage HF to GGUF conversion & quantization (`Q4_K_M`, `IQ2_XXS`) | M3 | Survey 3 |
| 15 | F15: Inference Server Hot-Reload Sentinel | Zero-downtime health probing & routing reload across ports 8081, 8082, 8083 | M3 | Survey 3 |
| 16 | F16: Zero-Cost Tri-Vault Synchronization Publisher | Publishing checkpoint cards & curves to Obsidian, PySpark lake, Git worktrees | M3 | Survey 3 |
| 17 | F17: 24/7 Autonomous Evolution Orchestrator CLI | Main continuous loop CLI orchestrating ingestion, training, merging, quant, and reload | M4 | Survey 1-3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Independent opaque-box test runner and test suite (Tiers 1-4) | None | DONE |
| M1 | Apple Silicon Metal QLoRA Trainer & Memory Governor | F1, F2, F3, F4 | None | DONE |
| M2 | Continuous DPO Distillation & Tokenizer Alignment | F5, F6, F7, F8, F9, F10, F11 | M1 (Interface Contracts) | DONE |
| M3 | Autonomous TIES/DARE Weight Merging & GGUF Quantization | F12, F13, F14, F15, F16 | M1, M2 (Interface Contracts) | DONE |
| M4 | Final Integration, 100% E2E Pass & Adversarial Hardening | F17 + Full E2E Test Suite (Tiers 1-4) + Tier 5 Adversarial Coverage | E2E, M1, M2, M3 | DONE |

## Interface Contracts

### M1 (Trainer) ↔ M2 (Distillation & Ingestion)
- `dataset_loader.get_dataloader(config, tokenizer)` -> Returns PyTorch DataLoader yielding tokenized, padded batches with `input_ids`, `attention_mask`, `labels` (for SFT) or `prompt_input_ids`, `chosen_input_ids`, `rejected_input_ids` (for DPO).
- `ram_governor.check_headroom()` -> Returns `bool` (True if free headroom >= 2.50 GB and total RAM usage <= 90.0%).
- `ram_governor.reclaim_memory()` -> Calls `gc.collect()` and `torch.mps.empty_cache()`.

### M2 (Distillation) ↔ M3 (Weight Merging & Quantization)
- `dpo_distillation_engine.save_checkpoint(output_dir)` -> Saves standard HuggingFace / PEFT adapter directory containing `adapter_config.json` and `adapter_model.safetensors`.
- `native_ties_dare_merger.merge_adapters(base_model_path, adapter_paths, output_dir, method="ties", density=0.6)` -> Produces merged HF model in `output_dir`.

### M3 (Merging/Quant) ↔ M4 (Inference & Tri-Vault)
- `gguf_quantizer.quantize_model(hf_model_dir, output_gguf_path, quant_type="Q4_K_M")` -> Compiles quantized `.gguf` weight file.
- `server_reload_sentinel.reload_inference_cluster(new_gguf_path, target_port=8082)` -> Executes zero-downtime hot-reload across ports 8081/8082/8083.
- `tri_vault_publisher.publish_cycle(checkpoint_metadata, loss_curves)` -> Writes note to `obsidian_vault/05_TRAINING/` and appends row to `lora_datasets/continuous_lora_dataset.jsonl`.

## Code Layout
```
12_continuous_lora_evolution/
├── PROJECT.md
├── TEST_INFRA.md
├── TEST_READY.md
├── src/
│   ├── __init__.py
│   ├── trainer/
│   │   ├── __init__.py
│   │   ├── mps_qlora_trainer.py
│   │   └── dynamic_ram_governor.py
│   ├── distillation/
│   │   ├── __init__.py
│   │   ├── dataset_loader.py
│   │   ├── tokenizer_aligner.py
│   │   ├── replay_buffer.py
│   │   ├── sample_deduplicator.py
│   │   ├── ast_compiler_gate.py
│   │   └── dpo_loss_mps.py
│   ├── weight_merging/
│   │   ├── __init__.py
│   │   ├── mergekit_manifest_generator.py
│   │   ├── native_ties_dare_merger.py
│   │   └── gguf_quantizer.py
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── server_reload_sentinel.py
│   │   └── tri_vault_publisher.py
│   └── configs/
│       ├── qwen38_dare_ties.yaml
│       ├── smollm2_ties.yaml
│       └── llama32_slerp.yaml
├── tests/
│   ├── unit/
│   │   ├── test_ram_governor.py
│   │   ├── test_mps_qlora_trainer.py
│   │   ├── test_tokenizer_aligner.py
│   │   ├── test_sample_deduplicator.py
│   │   ├── test_replay_buffer.py
│   │   ├── test_ast_compiler_gate.py
│   │   ├── test_native_merger.py
│   │   ├── test_gguf_quantizer.py
│   │   ├── test_server_reload.py
│   │   ├── test_tri_vault_publisher.py
│   │   ├── test_dataset_loader.py
│   │   └── test_dpo_loss_mps.py
│   ├── e2e/
│   │   ├── run_e2e_tests.py
│   │   ├── test_tier1_features.py
│   │   ├── test_tier2_boundaries.py
│   │   ├── test_tier3_cross_feature.py
│   │   ├── test_tier4_real_world.py
│   │   └── test_helpers.py
│   ├── adversarial/
│   │   └── test_adversarial_stress.py
│   └── verification/
│       ├── test_mathematical_foundations.py
│       └── test_adversarial_challenges.py
```
