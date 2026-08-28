# llama.cpp RPC Mesh Sharding & Kimi Tandem Architecture

Distributed tensor parallel execution spanning Apple Silicon Metal GPUs (M4 Mini, MacBook Pro Vault, MacBook Air) and Linux/Android nodes.

## Cluster Topology & Ports
- **Protocol:** GGML RPC (`ggml-rpc-server`)
- **RPC Sharding Port:** `50052`
- **Master llama-server Port:** `8081` (OpenAI API `/v1/chat/completions`)
- **Kimi-VL Vision Port:** `8085` (Multimodal Projector)
- **Edge Vision Fallback Port:** `8084` (Qwen2.5-VL-7B at 48.3 tok/s)
- **High-Speed Interconnect:** 10Gbps Thunderbolt 4 DMA Bridge (0.277ms RTT) / 1Gbps LAN

---

## Kimi Tandem Sharding Specification (80 Layers)

| Node | Physical Specs | Dynamic Cap | Usable VRAM | Kimi Shard | Layers | Footprint |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Linux Head Node** (`100.101.39.98`) | AMD Ryzen 7 (16GB RAM) | **80.0%** | **12.8 GB** | Shard 1 (CPU/Vulkan) | 28 layers (0..27) | 13.5 GB |
| **MacBook Pro TB4** (`169.254.187.138`) | M1 Max (16GB RAM) | **90.0%** | **14.4 GB** | Shard 2 (Metal MPS) | 28 layers (28..55) | 13.5 GB |
| **Host Mac Mini M4** (`127.0.0.1`) | M4 Pro (24GB RAM) | **90.0%** | **21.6 GB** | Shard 3 (Metal MPS) + Kimi-VL | 24 layers (56..79) + 9.8GB VL | 22.6 GB |
| **TOTALS** | **3 Primary Nodes** | — | **48.8 GB / 82.8 GB Pooled** | **Tandem Model** | **80 Layers (-ts 28,28,24)** | **48.8 GB** |

---

## Dynamic Memory Ceilings (Anti-Crash Guard)
- **Apple Silicon (macOS):** `90.0%` (2.4 GB OS reserve on 24GB host, 1.6 GB on 16GB)
- **Linux Head Node:** `80.0%` (3.2 GB OS buffer on 16GB)
- **Google Pixel 10 Pro XL:** `85.0%` (2.4 GB OS buffer on 16GB)
- **Samsung Galaxy S20+:** `75.0%` (3.0 GB OS buffer on 12GB)
- **Linux Tablet (Debian):** `75.0%` (2.0 GB OS buffer on 8GB)

---

## Execution Command Directives

```bash
# Master Kimi-Dev-72B Server
llama-server \
  --model /Volumes/NAS/AI_Models/kimi-dev-72b-instruct-q4_k_m.gguf \
  --rpc 100.101.39.98:50052,169.254.187.138:50052,127.0.0.1:50052 \
  -ts 28,28,24 \
  -ngl 999 \
  --ctx-size 16384 \
  --parallel 2 \
  --port 8081 \
  --host 0.0.0.0

# Dedicated Kimi-VL Thinking 2506 Server
llama-server \
  --model /Volumes/NAS/AI_Models/kimi-vl-thinking-2506-q4_k_m.gguf \
  --mmproj /Volumes/NAS/AI_Models/kimi-vl-thinking-2506-mmproj-f16.gguf \
  -ngl 999 \
  --ctx-size 32768 \
  --parallel 2 \
  --port 8085 \
  --host 0.0.0.0
```
