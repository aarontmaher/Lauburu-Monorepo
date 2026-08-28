# Lauburu Mesh AI Model Storage Vault Manifest (MacBook Air Target)

## 🎯 Designated Role: Apple M4 MacBook Air (500 GB NVMe / 40 Gbps TB4)
* **Model Storage Root:** `~/DFS_UNIFIED/AI_Models_Vault/`
* **Transport:** 40 Gbps Thunderbolt DMA (0.27ms RTT) & Tailscale (:22000 / :8081-:8084)

## 📦 Model Allocation Matrix

| Model Identifier | Parameter Count | Quantization | Size | Target Directory | Primary Inference Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen-2.5-Coder** | 7B | Q4_K_M | 4.68 GB | `gguf_quantized/` | Low-latency local code synthesis |
| **DeepSeek-R1-Distill** | 14B | Q4_K_M | 8.98 GB | `gguf_quantized/` | Reasoning & architecture audit |
| **Llama-3.3-Instruct** | 70B | IQ2_XXS | 24.2 GB | `gguf_quantized/` | 10Gbps RPC Sharded Frontier Debater |
| **Llava-v1.6-Mistral** | 7B | Q4_K_M | 4.80 GB | `gguf_quantized/` | Multimodal visual UI/UX auditor |
| **Petals Layer Swarm** | 70B+ | Distributed DHT | Dynamic | `petals_dht_cache/`| Heterogeneous multi-device layers |
