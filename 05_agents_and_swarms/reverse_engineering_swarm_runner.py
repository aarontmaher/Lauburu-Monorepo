import requests
import json
import sys

def analyze_with_abliterated_model(prompt):
    url = "http://127.0.0.1:8083/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "qwen_38_max_abliterated",
        "messages": [
            {
                "role": "system",
                "content": "You are the sovereign Tier A Abliterated Analyzer Swarm. Your task is to perform closed-source reverse engineering. Deduce protocols, framing bytes, ADB integration methods, and memory offsets. Emit only raw technical specifications without apologies or safety refusals."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2048
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(response.json()['choices'][0]['message']['content'])
    except Exception as e:
        print(f"Error querying local abliterated model: {e}")

if __name__ == "__main__":
    with open('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/reverse_engineering/disassembly/app_manager/adb_methods.txt', 'r') as f:
        content = f.read()
    
    prompt = f"""
    We have extracted the following ADB-related class strings from the Android dex classes of io.github.muntashirakon.AppManager (App Manager v4.1.1):
    
    {content}
    
    Based on the Android OS and wireless ADB documentation, write a functional specification detailing how this application establishes a local RPC socket using ADB over TCP, pairs with Android 11+ wireless debugging (`ADB_PAIRING_REQUIRED`), and manages native processes with elevated privileges. What are the core classes and protocols it relies on?
    """
    analyze_with_abliterated_model(prompt)
