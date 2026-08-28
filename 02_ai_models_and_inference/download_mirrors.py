import os
from huggingface_hub import hf_hub_download

vault_dir = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"

models = [
    {"repo": "mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated-GGUF", "filename": "meta-llama-3.1-8b-instruct-abliterated.Q4_K_M.gguf"},
    {"repo": "QuantFactory/Mistral-Nemo-Instruct-2407-abliterated-GGUF", "filename": "Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf"}
]

print("Starting non-gated mirror downloads...")
for m in models:
    try:
        print(f"Downloading {m['filename']}...")
        hf_hub_download(repo_id=m['repo'], filename=m['filename'], local_dir=vault_dir, local_dir_use_symlinks=False)
        print(f"Successfully downloaded {m['filename']}.")
    except Exception as e:
        print(f"Failed to download {m['filename']}: {e}")
