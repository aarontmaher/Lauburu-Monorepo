import os
import httpx
from dotenv import load_dotenv
from mesh_mcts_orchestrator import mcts_reasoning_loop

load_dotenv("/Volumes/Lauburu-Monorepo/.env")
api_key = os.environ.get("OPENROUTER_API_KEY")

def call_openrouter(model_id, prompt):
    if not api_key:
        return "ERROR: OPENROUTER_API_KEY not found in .env"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/aarontmaher/Lauburu-Monorepo",
        "X-Title": "Lauburu Mesh Benchmark"
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=40.0)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR calling {model_id}: {str(e)}"

def call_local(prompt):
    url = "http://127.0.0.1:8082/v1/chat/completions"
    payload = {
        "model": "qwen_38_max",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = httpx.post(url, json=payload, timeout=30.0)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR calling Local Qwen: {str(e)}"

if __name__ == "__main__":
    prompt = "Explain in one technical paragraph how Local MCTS scaling beats standard zero-shot scaling."
    
    # Enforcing Free Tier per user rule!
    frontier_models = [
        "google/gemini-3.8-flash:free",
        "google/gemini-3.1-pro-preview:free",
        "anthropic/claude-3.5-sonnet:beta" # Fallback if free fable isn't available
    ]
    
    print("🚀 EXTENDED BENCHMARK (FREE TIER ENFORCED): FRONTIER MODELS vs LOCAL SWARM 🚀\n")
    
    for model in frontier_models:
        print("==================================================")
        print(f"☁️  Frontier: {model}")
        print(call_openrouter(model, prompt))
        print()

    print("==================================================")
    print("💻  Local Master (MCTS / Test-Time Compute): Qwen 3.8 Max")
    print(mcts_reasoning_loop(prompt))
    print("==================================================\n")
