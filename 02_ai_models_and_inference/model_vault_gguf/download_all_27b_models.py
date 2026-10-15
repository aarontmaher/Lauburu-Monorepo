import os
import sys
import subprocess

MODELS = [
    {
        "repo": "huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF",
        "file": "Huihui-Qwen3.8-27B-abliterated-UD-DW-Q4_K_M.gguf"
    },
    {
        "repo": "unsloth/Qwen3.8-27B-GGUF",
        "file": "Qwen3.8-27B-UD-Q4_K_M.gguf"
    },
    {
        "repo": "DavidAU/Qwen3.8-27B-TWIN-TURBO-Fable-Cold-Fusion-709-L-Uncensored-NM-DAU-NEO-MTP-GGUF",
        "file": "Qwen3.8-27B-TTURBO-Fable-C-Fusion-709-L-Uncen-NM-DAU-NEO-MTP-Q4_K_M.gguf"
    }
]

DEST_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"

def download_model(repo, filename):
    url = f"https://huggingface.co/{repo}/resolve/main/{filename}?download=true"
    print(f"\n--- Downloading {filename} with aria2c ---")
    cmd = [
        "aria2c",
        "--check-certificate=false",
        "-x", "16",
        "-s", "16",
        "-k", "1M",
        "--allow-overwrite=true",
        "--auto-file-renaming=false",
        "-d", DEST_DIR,
        "-o", filename,
        url
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    os.makedirs(DEST_DIR, exist_ok=True)
    for model in MODELS:
        download_model(model["repo"], model["file"])
