#!/bin/bash
set -e

VAULT_DIR="/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/gguf_vault"
mkdir -p "$VAULT_DIR"

echo "==========================================================="
echo "🧠 Lauburu Medical Swarm Model Downloader"
echo "Vault Directory: $VAULT_DIR"
echo "==========================================================="

download_model() {
    local url=$1
    local filename=$2
    
    echo -e "\n⬇️ Checking/Downloading: $filename..."
    if [ -f "$VAULT_DIR/$filename" ]; then
        echo "✅ Model $filename already exists! Skipping."
    else
        echo "⏳ Downloading ~4.5GB... (This may take a few minutes)"
        curl -L -C - "$url" -o "$VAULT_DIR/$filename"
        echo "✅ Download complete: $filename"
    fi
}

# 1. The Sovereign Synthesizer (Llama 3.1 8B Instruct Q4_K_M)
download_model "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" "llama-3.1-8b-instruct-q4_k_m.gguf"

# 2. The Quantitative Analyst (Qwen 2.5 Math 7B Q4_K_M)
download_model "https://huggingface.co/Qwen/Qwen2.5-Math-7B-Instruct-GGUF/resolve/main/qwen2.5-math-7b-instruct-q4_k_m.gguf" "qwen2.5-math-7b-instruct-q4_k_m.gguf"

# 3. The Clinical Physician (Meditron 7B Q4_K_M)
download_model "https://huggingface.co/TheBloke/meditron-7B-GGUF/resolve/main/meditron-7b.Q4_K_M.gguf" "meditron-7b-q4_k_m.gguf"

echo -e "\n🚀 All Swarm models have been successfully deposited into the GGUF Vault!"
