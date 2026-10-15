import time
import requests
import json
import os

# Tier 1 & 2: Local Hardware
LOCAL_CODER_URL = "http://127.0.0.1:8081/v1/chat/completions"
LOCAL_ABLITERATED_MASTER_URL = "http://127.0.0.1:8082/v1/chat/completions"

# Tier 3 & 4: Cloud API Endpoints
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_FREE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

class TaskFailedException(Exception):
    pass

def call_local_model(url, prompt, model_id):
    print(f"  -> Attempting execution via Local Model: {model_id} at {url}")
    # Simulated payload for llama.cpp/prima.cpp OpenAI-compatible endpoints
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        raise TaskFailedException(f"Local model HTTP {response.status_code}")
    except Exception as e:
        raise TaskFailedException(f"Local execution failed: {e}")

def call_free_tier(prompt):
    print(f"  -> Escalating to Free Tier Cloud API (Gemini Flash)")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise TaskFailedException("Missing GEMINI_API_KEY for Free Tier.")
        
    url = f"{GEMINI_FREE_URL}?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=15)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        raise TaskFailedException(f"Free Tier HTTP {response.status_code}")
    except Exception as e:
        raise TaskFailedException(f"Free Tier execution failed: {e}")

def call_openrouter_frontier(prompt):
    print(f"  -> EMERGENCY ESCALATION: OpenRouter Paid Frontier Swarm (Claude 3.5 Sonnet / GPT-4o)")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise TaskFailedException("Missing OPENROUTER_API_KEY.")
        
    payload = {
        "model": "anthropic/claude-3.5-sonnet", # Default Frontier fallback
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        raise TaskFailedException(f"OpenRouter HTTP {response.status_code}")
    except Exception as e:
        raise TaskFailedException(f"Frontier Paid execution failed: {e}")

def execute_with_escalation(prompt, max_retries_per_tier=2):
    """
    Executes a task using a strict 4-Tier Graduated Autonomy escalation matrix.
    """
    print(f"\n[ESCALATION ROUTER] Initiating Task...")
    
    # Tier 1: Local Subordinate Worker (Qwen 2.5 Coder 7B)
    for _ in range(max_retries_per_tier):
        try:
            return call_local_model(LOCAL_CODER_URL, prompt, "qwen2.5-coder")
        except TaskFailedException:
            print("  [X] Tier 1 (Qwen Coder) failed. Retrying...")
            time.sleep(1)
            
    # Tier 2: Sovereign Master Orchestrator (Qwen 3.8 Max 27B Abliterated)
    print("\n[!] Tier 1 Exhausted. Escalating to Tier 2 (Sovereign Local Orchestrator)...")
    for _ in range(max_retries_per_tier):
        try:
            return call_local_model(LOCAL_ABLITERATED_MASTER_URL, prompt, "qwen_38_max_abliterated")
        except TaskFailedException:
            print("  [X] Tier 2 (Abliterated Qwen 3.8) failed. Retrying...")
            time.sleep(1)
            
    # Tier 3: Cloud Free Tier (Quota Limited)
    print("\n[!] Tier 2 Exhausted. Escalating to Tier 3 (Cloud Free Tier)...")
    for _ in range(max_retries_per_tier):
        try:
            return call_free_tier(prompt)
        except TaskFailedException:
            print("  [X] Tier 3 (Free Tier) failed. Retrying...")
            time.sleep(1)
            
    # Tier 4: Paid Frontier Swarms (Financial Cost)
    print("\n[!!!] Tier 3 Exhausted. TRIGGERING TIER 4 PAID FRONTIER SWARM...")
    try:
        return call_openrouter_frontier(prompt)
    except TaskFailedException as e:
        print(f"\n[FATAL] All escalation tiers failed. Task cannot be completed. Error: {e}")
        return None

if __name__ == "__main__":
    # Test the escalation matrix routing logic
    execute_with_escalation("Synthesize a Python script to verify Thunderbolt 4 DMA latency.")
