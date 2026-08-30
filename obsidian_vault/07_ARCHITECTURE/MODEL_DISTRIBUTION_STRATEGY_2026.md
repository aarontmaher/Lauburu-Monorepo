---
title: "Model Distribution & Storage Strategy — August 2026"
tags: [models, storage, gguf, mesh, architecture]
updated: 2026-08-30T13:00
---

# 🗄️ Active Model Distribution (LIVE)

## Confirmed Node Storage & RAM

| Node | SSD Free | RAM | Swap | Max Serveable |
|------|----------|-----|------|--------------|
| Mac Mini L1 | 13 GB | 24 GB | — | ~20 GB Metal |
| MacBook Pro L2 | 19 GB | 16 GB | 4 GB | ~16 GB |
| Linux Head L3 | 211 GB | 14 GB | **27 GB** | ~36 GB ✅ |

## ✅ Live GGUF Servers

| Port | Node | Model | Status |
|------|------|-------|--------|
| :8080 | Mac Mini | Qwen3.8-27B-4bit | 🟢 HTTP 200 |
| :8082 | Mac Mini | Mistral-Nemo-12B-Q4 | 🟢 HTTP 200 |
| :8084 | Mac Mini | Llama-3.1-70B-Q4 | 🟢 HTTP 200 |
| :8086 | Mac Mini | Qwen2.5-Math-7B-Q4 | 🟢 HTTP 200 |
| :8087 | Mac Mini | Qwen2.5-Math-1.5B-Q8 | 🟢 HTTP 200 |
| **:8089** | **Linux L3** | **Qwen2.5-Math-72B-IQ2_XS** | **🟢 HTTP 200 ✅** |

## How 72B fits on 14 GB RAM Linux
- Model size: 26 GB (IQ2_XXS quantization)
- Solution: +20 GB swapfile2 → 14 GB RAM + 27 GB swap = **41 GB addressable**
- mmap mode: OS pages hot layers into RAM, cold layers on NVMe via swap
- Speed: ~8-12 tok/s (NVMe-backed, Ryzen 7 5700U, 14 threads)

## MBP AI_Models_Vault (Stored, Not Yet Served)
- DeepSeek-R1-Distill-Llama-70B-IQ2_XXS (18 GB)
- Meta-Llama-3.1-70B-Instruct-IQ2_M (21 GB)
- Qwen2.5-VL-32B-Instruct-Q4_K_M (18 GB)
- gpt-oss-20b-MXFP4 (11 GB)
