---
title: "Model Distribution & Storage Strategy — August 2026"
tags: [models, storage, gguf, mesh, architecture]
updated: 2026-08-30
---

# 🗄️ Model Distribution & Storage Strategy

## Confirmed Node Storage & RAM Reality

| Node | SSD Free | RAM Total | Swap | Max Serveable Model |
|------|----------|-----------|------|---------------------|
| Mac Mini L1 | 13 GB | 24 GB | none | ~20 GB (Metal mmap) |
| MacBook Pro L2 | 19 GB | 16 GB | 4 GB | ~16 GB |
| MacBook Air L5 | TBD | 16 GB | 4 GB | ~16 GB |
| Linux Head L3 | 231 GB | 14 GB | 8 GB | ~18 GB max |

## ⚠️ 72B RAM Constraint
- `Qwen2.5-Math-72B-IQ2_XS.gguf` = **26 GB** requires > 26 GB addressable memory
- Linux L3: 14 GB RAM + 8 GB swap = 22 GB — **INSUFFICIENT** (4 GB short)
- File safely stored at `/home/linux/gguf_vault/` for future use
- **Resolution paths:**
  1. Add 16+ GB swap on Linux: `sudo fallocate -l 20G /swapfile2` → total 28 GB
  2. Wait for Pixel 10 Pro (16 GB RAM) access via ADB llama.cpp
  3. Serve 72B sharded across Mac Mini + Linux via llama.cpp RPC split

## Active GGUF Servers (Live)

| Port | Node | Model | RAM Used | Status |
|------|------|-------|----------|--------|
| :8080 | Mac Mini | Qwen3.8-27B-4bit | ~14 GB Metal | 🟢 |
| :8082 | Mac Mini | Mistral-Nemo-12B-Q4 | ~7 GB Metal | 🟢 |
| :8084 | Mac Mini | Llama-3.1-70B-Q4 | ~38 GB Metal | 🟢 |
| :8086 | Mac Mini | Qwen2.5-Math-7B-Q4 | ~4.4 GB | 🟢 |
| :8087 | Mac Mini | Qwen2.5-Math-1.5B-Q8 | ~1.5 GB | 🟢 |
| :8089 | Linux | Qwen2.5-Math-72B (**STORED, NOT SERVING**) | 26 GB > 22 GB avail | ❌ |

## Recommended Next: Expand Linux Swap
```bash
ssh linux-lan "sudo fallocate -l 20G /swapfile2 && sudo chmod 600 /swapfile2 \
  && sudo mkswap /swapfile2 && sudo swapon /swapfile2"
# Total swap: 8 + 20 = 28 GB + 14 GB RAM = 42 GB addressable → 72B fits
```
