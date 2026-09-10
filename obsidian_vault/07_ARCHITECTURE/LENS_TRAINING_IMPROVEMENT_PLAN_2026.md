# 🗺️ Screen Lens 24/7 Training Improvement Plan (2026 Architectural Roadmap)

This roadmap codifies the consensus reached across Google Gemini Ultra, NVIDIA NIM 1.6T MoE, xAI Grok-2, Cloudflare Workers AI, and the Sovereign Local AI Triumvirate.

## Phase 1: Core Training Engine Upgrades (Immediate)
1. **Multi-Projection LoRA Expansion:**
   - Update `LoRALinear` in `mlx_lens_qlora_trainer.py` to support multi-head projection mapping ($W_q, W_k, W_v, W_o$).
   - Double rank dimension ($r=16 \to 32$) with proportional alpha ($\alpha=64.0$).
2. **Authentic Token Hashing & Embedding Ingestion:**
   - Ingest authentic instruction/input/output strings from `continuous_lora_dataset.jsonl`.
   - Apply deterministic vocabulary projection to generate authentic token embeddings.
3. **Multi-Model Gradient Updates:**
   - Ensure all active LoRA projection layers participate in `nn.value_and_grad` computation.

## Phase 2: DPO Preference Alignment & Anti-Hallucination
1. **DPO Pair Curation:**
   - Harvest code audit failures and UI coordinate errors into `lens_multimodal_dpo.jsonl`.
   - Formulate contrastive loss to penalize non-existent file paths and simulated arrays.
2. **Dynamic Learning Rate Decay:**
   - Introduce cosine learning rate scheduler in `MLXLensQLoRATrainer`.

## Phase 3: Hardware Sanctuary & Metal VRAM Management
1. **Host Sanctuary Invariant:**
   - Retain $\ge 9.6\text{ GB}$ free physical RAM on Mac Mini M4 Pro host.
   - Trigger `mx.clear_cache()` every 50 steps to eliminate unified memory fragmentation.
