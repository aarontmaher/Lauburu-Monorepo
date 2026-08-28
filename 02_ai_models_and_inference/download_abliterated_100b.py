import sys
import subprocess

models = [
    # 70B Abliterated
    ("mradermacher/Meta-Llama-3.1-70B-Instruct-abliterated-GGUF", "Meta-Llama-3.1-70B-Instruct-abliterated.Q4_K_M.gguf"),
    # 100B+ Model
    ("pmysl/c4ai-command-r-plus-GGUF", "command-r-plus.Q3_K_L.gguf")
]

# We use uv run huggingface-cli
for repo, filename in models:
    print(f"Downloading {filename} from {repo}...")
    try:
        subprocess.run([
            "uv", "run", "huggingface-cli", "download", repo, filename,
            "--local-dir", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf",
            "--local-dir-use-symlinks", "False"
        ], check=True)
        print(f"Success: {filename}")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")

print("Download script finished.")
