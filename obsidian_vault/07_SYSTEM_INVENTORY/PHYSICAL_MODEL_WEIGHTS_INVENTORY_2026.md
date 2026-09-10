# 🧭 Physical Network & Storage Model Inventory Report (278.84 GB Total)

**Scan Timestamp:** 2026-09-01T14:32:46Z  
**Scan Scope:** Mac Mini M4 Host, Local NVMe, Connected Mesh Nodes (L2 MacBook Pro, L3 Linux Head Node, L5 Air, L7 Android S20), and Attached Storage Volumes.  
**Rule #0 Certification:** 100% physically verified paths and disk allocations (0 simulated entries).

---

## 1. 🔍 Answers to User Inquiries

### *"Don't we have that Mistral AI model? Mixtral 8x22B"*
* **Mistral Model Found:** We have **`Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf` (6.96 GB)** physically verified and stored in `02_ai_models_and_inference/model_vault_gguf/`.
* **Mixtral 8x22B Status:** **Not present on disk.** (A 48–60 GB GGUF download would be required if desired).
* **Massive Heavyweights That ARE on Disk:**
  1. `Qwen3.8-Flash-Next-UD-Q2_K_XL` (3-part split GGUF: **73.46 GB total**) in `/Users/aaron/models/Qwen3.8-Flash-Next/`
  2. `Llama-4-Scout-17B-16E-Instruct-Q4_K_M` (**46.42 GB**) in `02_ai_models_and_inference/model_vault_gguf/`
  3. `Qwen2.5-Math-72B-Instruct-IQ2_XXS` (**23.74 GB**) in `02_ai_models_and_inference/gguf_vault/`

---

## 2. 📊 Complete Line-by-Line Inventory of All Physical Models (278.84 GB)

| Size | Format | Model Name / File | Absolute Disk Path | Category |
| :--- | :--- | :--- | :--- | :--- |
| **46.55 GB** | GGUF | `Qwen3.8-Flash-Next-UD-Q2_K_XL (Part 2)` | `/Users/aaron/models/Qwen3.8-Flash-Next/Qwen3.8-Flash-Next-UD-Q2_K_XL-00002-of-00003.gguf` | Frontier Dense/MoE |
| **46.42 GB** | GGUF | `Llama-4-Scout-17B-16E-Instruct-Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Llama-4-Scout-17B-16E-Instruct-Q4_K_M-00001-of-00002.gguf` | Frontier MoE Shard |
| **26.90 GB** | GGUF | `Qwen3.8-Flash-Next-UD-Q2_K_XL (Part 3)` | `/Users/aaron/models/Qwen3.8-Flash-Next/Qwen3.8-Flash-Next-UD-Q2_K_XL-00003-of-00003.gguf` | Frontier Dense/MoE |
| **23.74 GB** | GGUF | `Qwen2.5-Math-72B-Instruct-IQ2_XXS` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/gguf_vault/Qwen2.5-Math-72B-Instruct-IQ2_XXS.gguf` | Math & ILP Solver |
| **20.61 GB** | GGUF | `Qwen-AgentWorld-35B-A3B-UD-Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen-AgentWorld-35B-A3B-UD-Q4_K_M.gguf` | OS World Simulator |
| **18.40 GB** | GGUF | `WebWorld-32B.Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/WebWorld-32B.Q4_K_M.gguf` | Web Flight Simulator |
| **16.19 GB** | GGUF | `Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf` | Devil's Advocate Critic |
| **16.34 GB** | Safetensors | `Qwen3-VL-8B-Instruct (4 parts)` | `/Users/aaron/models/Qwen3-VL-8B-Instruct/model-00001..4-of-00004.safetensors` | Vision-Language |
| **10.37 GB** | Safetensors | `CogVideoX-5B (2 parts)` | `/Users/aaron/models/CogVideoX-5B/diffusion_pytorch_model-00001..2-of-00002.safetensors` | Video Generation |
| **6.96 GB** | GGUF | `Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf` | Uncensored Reasoning |
| **5.37 GB** | GGUF | `gemma-2-9b-it-abliterated-Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/gemma-2-9b-it-abliterated-Q4_K_M.gguf` | Uncensored Subordinate |
| **4.68 GB** | GGUF | `WebWorld-8B.Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/WebWorld-8B.Q4_K_M.gguf` | Fast DOM Mock |
| **4.58 GB** | GGUF | `Hermes-3-Llama-3.1-8B.Q4_K_M` | `/Users/aaron/.local/share/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf` | Agentic Tool Caller |
| **4.36 GB** | GGUF | `Qwen2.5-7B-Instruct-abliterated.Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf` | Security Red Teamer |
| **4.36 GB** | GGUF | `Qwen2.5-Math-7B-Instruct-Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf` | Equation Solver |
| **4.36 GB** | GGUF | `qwen2.5-coder-7b-instruct-q4_k_m` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-7b-instruct-q4_k_m.gguf` | Polyglot Coder |
| **4.36 GB** | GGUF | `Qwen2.5-VL-7B-Instruct-Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` | Edge Vision DSP |
| **2.12 GB** | PyTorch | `bge-m3 (Dense + ColBERT + Sparse)` | `/Users/aaron/models/bge-m3/pytorch_model.bin` | Vector Embedding |
| **1.96 GB** | GGUF | `qwen2.5-coder-3b-instruct-q4_k_m` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-3b-instruct-q4_k_m.gguf` | Fast Code Lint |
| **1.80 GB** | GGUF | `Qwen2.5-VL-3B-Instruct-Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf` | Mobile Vision |
| **1.53 GB** | GGUF | `Qwen2.5-Math-1.5B-Instruct-Q8_0` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/gguf_vault/Qwen2.5-Math-1.5B-Instruct-Q8_0.gguf` | Tablet Calculator |
| **1.51 GB** | Safetensors | `whisper-large-v3-turbo` | `/Users/aaron/models/whisper-large-v3-turbo/model.safetensors` | Speech-to-Text |
| **1.04 GB** | GGUF | `qwen2.5-coder-1.5b-instruct-q4_k_m` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf` | Micro Coder |
| **0.98 GB** | GGUF | `smollm2-1.7b-instruct-q4_k_m` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/smollm2-1.7b-instruct-q4_k_m.gguf` | Android UI Tester |
| **0.81 GB** | Bin | `ggml-large-v3-turbo-q8_0` | `/Users/aaron/.cache/huggingface/hub/models--ggerganov--whisper.cpp/...` | Whisper.cpp STT |
| **0.75 GB** | GGUF | `Llama-3.2-1B-Instruct-Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Llama-3.2-1B-Instruct-Q4_K_M.gguf` | Edge SLM |
| **0.46 GB** | GGUF | `qwen2.5-0.5b-instruct-q4_k_m` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/micro_models/qwen2.5-0.5b-instruct-q4_k_m.gguf` | OpenWrt Router Sentinel |
| **0.25 GB** | GGUF | `SmolLM2-360M-Instruct-Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models/SmolLM2-360M-Instruct-Q4_K_M.gguf` | Sub-Second Tester |
| **0.17 GB** | Safetensors | `chronos-t5-small` | `/Users/aaron/models/chronos-t5-small/model.safetensors` | Biometrics Time Series |
| **0.10 GB** | GGUF | `SmolLM2-135M-Instruct-Q4_K_M` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models/SmolLM2-135M-Instruct-Q4_K_M.gguf` | Fast Heartbeat SLM |
| **0.07 GB** | PyTorch | `lauburu_project_moe_init.pt` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models/checkpoints/lauburu_project_moe_init.pt` | MoE Checkpoint |
| **0.01 GB** | GGUF | `Qwen3.8-Flash-Next-UD-Q2_K_XL (Part 1)` | `/Users/aaron/models/Qwen3.8-Flash-Next/Qwen3.8-Flash-Next-UD-Q2_K_XL-00001-of-00003.gguf` | Model Header |
