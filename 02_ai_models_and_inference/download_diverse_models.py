import os
from huggingface_hub import hf_hub_download

vault_dir = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
os.makedirs(vault_dir, exist_ok=True)

models = [
    # 1. Abliterated Llama 3 (8B) - High reasoning, completely uncensored
    {"repo": "bartowski/Meta-Llama-3-8B-Instruct-abliterated-GGUF", "filename": "Meta-Llama-3-8B-Instruct-abliterated-Q4_K_M.gguf"},
    
    # 2. Abliterated Mistral Nemo (12B) - Excellent 128k context, strong edge model
    {"repo": "bartowski/Mistral-Nemo-Instruct-2407-abliterated-GGUF", "filename": "Mistral-Nemo-Instruct-2407-abliterated-Q4_K_M.gguf"},
    
    # 3. Abliterated Gemma 2 (9B) - Extremely dense intelligence for its size
    {"repo": "bartowski/gemma-2-9b-it-abliterated-GGUF", "filename": "gemma-2-9b-it-abliterated-Q4_K_M.gguf"},
    
    # 4. Standard Qwen 2.5 Coder (7B) - For the Master Logic correction pipeline (Healing Engine)
    {"repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", "filename": "qwen2.5-coder-7b-instruct-q4_k_m.gguf"}
]

print("Starting diverse model downloads for ELO ranking...")
for m in models:
    try:
        print(f"Downloading {m['filename']}...")
        hf_hub_download(repo_id=m['repo'], filename=m['filename'], local_dir=vault_dir, local_dir_use_symlinks=False)
        print(f"Successfully downloaded {m['filename']}.")
    except Exception as e:
        print(f"Failed to download {m['filename']}: {e}")
        
print("All model downloads completed or queued.")
