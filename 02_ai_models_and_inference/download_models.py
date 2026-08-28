import os
from huggingface_hub import hf_hub_download

vault_dir = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"
os.makedirs(vault_dir, exist_ok=True)

models = [
    ("mradermacher/Meta-Llama-3.1-70B-Instruct-abliterated-GGUF", "Meta-Llama-3.1-70B-Instruct-abliterated.Q4_K_M.gguf"),
    ("pmysl/c4ai-command-r-plus-GGUF", "command-r-plus-Q3_K_L-00001-of-00002.gguf")
]

for repo, filename in models:
    print(f"Downloading {filename} from {repo}...")
    try:
        path = hf_hub_download(repo_id=repo, filename=filename, local_dir=vault_dir)
        print(f"Success: {path}")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")

