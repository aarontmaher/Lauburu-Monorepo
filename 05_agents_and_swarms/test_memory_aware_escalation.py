import os
import time
import requests
import json

# 1. Project Memory Awareness (RAG)
VAULT_INDEX = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/Index.md"
try:
    with open(VAULT_INDEX, 'r') as f:
        project_memory = f.read()
except:
    project_memory = "Memory unavailable."

def run_tier(tier_name, url, payload, headers=None, simulate_failure=False):
    print(f"\n[SWARM] Evaluating Tier: {tier_name}")
    if simulate_failure:
        print(f"  [X] Simulated Failure (Timeout/Offline) for {tier_name}")
        return None
        
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"  [SUCCESS] {tier_name} completed the task.")
            return response.json()
        else:
            print(f"  [X] {tier_name} Failed. HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"  [X] {tier_name} Offline or Unreachable: {e}")
        return None

def main():
    print("🚀 Initiating Project-Memory Aware Swarm Escalation Test...")
    
    prompt = f"Analyze our project index and output the core swarm topology. Context: {project_memory[:500]}"
    payload_openai = {"model": "default", "messages": [{"role": "user", "content": prompt}]}
    
    # Tier 1: Local Qwen Coder
    result = run_tier("Tier 1: Qwen Coder (Port 8081)", "http://127.0.0.1:8081/v1/chat/completions", payload_openai, simulate_failure=True)
    if result: return
    
    # Tier 2: Local Master (Qwen 3.8 Max Abliterated)
    result = run_tier("Tier 2: Sovereign Qwen (Port 8082)", "http://127.0.0.1:8082/v1/chat/completions", payload_openai, simulate_failure=True)
    if result: return
    
    # Tier 3: Free Tier Cloud (Gemini)
    payload_gemini = {"contents": [{"parts": [{"text": prompt}]}]}
    # Without an API key, this will naturally fail, triggering Tier 4
    result = run_tier("Tier 3: Free Cloud API (Gemini)", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent", payload_gemini)
    if result: return
    
    # Tier 4: OpenRouter MCP Handoff
    print("\n[!!!] ALL NATIVE TIERS EXHAUSTED. ESCALATING TO OPENROUTER MCP...")
    print("Requesting Antigravity Agent to execute via MCP tool.")

if __name__ == "__main__":
    main()
