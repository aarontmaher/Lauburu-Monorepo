import os
import time
import json
import psutil
from huggingface_hub import snapshot_download
import mlx.core as mx
from mlx_lm import load, generate

MODELS = [
    "mlx-community/Qwen2.5-Math-1.5B-Instruct-4bit",
    "mlx-community/Qwen2.5-Math-7B-Instruct-4bit"
]
# Skipping 72B for rapid swapping on L1 to preserve 4.8GB headroom.

def get_ram_free_gb():
    return psutil.virtual_memory().available / (1024**3)

def test_model_swap(model_id):
    print(f"\n[+] Testing {model_id}...")
    start_time = time.time()
    
    # Pre-download to avoid network latency in load timing
    snapshot_download(repo_id=model_id, max_workers=8)
    download_time = time.time() - start_time
    print(f"    - Download/Cache verification: {download_time:.2f}s")
    
    ram_before = get_ram_free_gb()
    load_start = time.time()
    model, tokenizer = load(model_id)
    load_time = time.time() - load_start
    ram_after = get_ram_free_gb()
    
    print(f"    - Load Time: {load_time:.2f}s")
    print(f"    - RAM Impact: {ram_before - ram_after:.2f} GB (Free: {ram_after:.2f} GB)")
    
    # Generate test
    prompt = "What is 15 * 12? Think step by step."
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    gen_start = time.time()
    response = generate(model, tokenizer, prompt=text, max_tokens=64, verbose=False)
    gen_time = time.time() - gen_start
    
    print(f"    - Generation Time: {gen_time:.2f}s")
    print(f"    - Output snippet: {response.strip()[:60]}...")
    
    # Clear memory explicitly
    del model
    del tokenizer
    mx.metal.clear_cache()
    
    return {
        "model_id": model_id,
        "load_time_s": load_time,
        "gen_time_s": gen_time,
        "ram_impact_gb": ram_before - ram_after
    }

if __name__ == "__main__":
    print("============================================================")
    print("  MLX RAPID MODEL SWAPPER BENCHMARK (Qwen Math Series)")
    print("============================================================")
    print(f"Initial RAM Free: {get_ram_free_gb():.2f} GB\n")
    
    results = []
    for m in MODELS:
        res = test_model_swap(m)
        results.append(res)
    
    print("\n[+] Benchmark Complete.")
    with open("/Volumes/Lauburu-Monorepo/obsidian_vault/04_ANALYTICS/mlx_rapid_swap_telemetry.json", "w") as f:
        json.dump(results, f, indent=2)
