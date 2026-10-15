# Legacy Deprecated Tools & MLX Scripts
=======================================
Archived: October 2026
Governed by: Rule 8 (Universal GGUF & Dual-Plane Invariant), Rule 3 (Host Sanctuary), Consensus Showdown

## Rationale for MLX Deprecation
1. **Heterogeneous Hardware Incompatibility**: MLX and `mlx_lm` are restricted exclusively to Apple Silicon Unified Memory. They cannot execute on L2 (Intel MacBook Pro Core i7 / AMD Radeon GPU), L3 (AMD Ryzen Linux Mini), L4 (Linux Tablet), or L7 (Exynos Android edge).
2. **Distributed DMA Bottleneck**: MLX lacks sub-millisecond tensor-parallel or pipeline-parallel remote procedure call (RPC) support over Thunderbolt DMA bridges or multi-IP subnets. In contrast, `prima.cpp` and `llama.cpp` provide zero-copy PRP sharding and native `ggml-rpc-server` across all 7 layers of the mesh.
3. **Universal GGUF Format**: The Lauburu mesh has standardized on universal GGUF (`Q4_K_M`, `UD-Q4_K_XL`, `IQ2_XXS`), enabling interchangeable loading across Metal, CUDA, ROCm, Vulkan, and ARM NEON.

## Archived Components
- `mlx_lens_qlora_trainer.py`: Legacy QLoRA training harness bound to Apple Silicon Metal. Replaced by `unified_local_ai_training_daemon.py` and `02_ai_models_and_inference/training_pipeline/unified_22_method_frontier_training_engine.py`.
- `distributed_mlx_mesh_bridge.py`: Experimental socket bridge for MLX. Replaced by `decentralized_prima_daemon.py` and `mesh_multiport_bridge.py`.
- `mlx_qlora_trainer.py`: Standalone trainer replaced by the canonical 22-protocol training engine.
- `prep_mlx_lora.py`: Dataset prepper for MLX.
- `remote_mlx_trainer.py`: Remote invocation script for MLX.
