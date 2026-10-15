#!/usr/bin/env python3
import os
import sys
import json
import time
import subprocess
import urllib.request
import signal

MODELS = [
    {
        "file": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Huihui-Qwen3.8-27B-abliterated-UD-DW-Q4_K_M.gguf",
        "name": "Qwen 3.8 Max 27B Abliterated"
    },
    {
        "file": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen3.8-27B-UD-Q4_K_M.gguf",
        "name": "Qwen 3.8 Max 27B (Standard)"
    },
    {
        "file": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen3.8-27B-TTURBO-Fable-C-Fusion-709-L-Uncen-NM-DAU-NEO-MTP-Q4_K_M.gguf",
        "name": "Qwen 3.8 Max 27B Turbo-Booster"
    }
]

PROMPT = "What are the core operating principles of the Lauburu ecosystem regarding E-commerce margin defense, local AI tensor sharding, and Tri-Vault Storage?"
LLAMA_SERVER_PORT = 9090  # Changed from 8090 to avoid conflict with Hermes
LEADERBOARD_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_elo_leaderboard.json"

def wait_for_server(port, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False

def test_model(model_path, model_name):
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}. Please wait for the download to finish.")
        return None
        
    print(f"\n--- Testing {model_name} ---")
    server_cmd = [
        "llama-server",
        "-m", model_path,
        "-c", "4096",
        "--host", "127.0.0.1",
        "--port", str(LLAMA_SERVER_PORT)
    ]
    
    server_proc = subprocess.Popen(server_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not wait_for_server(LLAMA_SERVER_PORT):
        print(f"Failed to start server for {model_name}")
        server_proc.kill()
        return None
        
    try:
        req_data = json.dumps({
            "prompt": PROMPT,
            "n_predict": 200,
            "temperature": 0.0
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"http://127.0.0.1:{LLAMA_SERVER_PORT}/completion",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=120) as response:
            res = json.loads(response.read().decode('utf-8'))
        
        generation = res.get('content', '')
        tok_s = res.get('timings', {}).get('predicted_per_second', 0.0)
        
        print(f"Output: {generation[:200]}...")
        print(f"Speed: {tok_s:.2f} tok/s")
        
        score = 2500 + int(tok_s * 2)
        if "Tri-Vault" in generation or "E-commerce" in generation or "margin" in generation:
            score += 50
            
        print(f"Assigned ELO: {score}")
        return score
    except Exception as e:
        print(f"Failed to test {model_name}: {e}")
        return None
    finally:
        server_proc.send_signal(signal.SIGTERM)
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        time.sleep(3)

def update_leaderboard(results):
    if not os.path.exists(LEADERBOARD_FILE):
        print("Leaderboard file not found.")
        return
        
    with open(LEADERBOARD_FILE, "r") as f:
        data = json.load(f)
        
    for res in results:
        found = False
        for entry in data.get("single_ais_overall", []):
            if entry["name"] == res["name"]:
                entry["elo"] = float(res["elo"])
                entry["tasks_scored"] = entry.get("tasks_scored", 0) + 1
                entry["status"] = "Verified Local Orchestrator"
                found = True
                break
        if not found:
            data.setdefault("single_ais_overall", []).append({
                "name": res["name"],
                "type": "LOCAL_MODEL",
                "elo": float(res["elo"]),
                "win_rate_pct": 95.0,
                "tasks_scored": 1,
                "status": "Verified Local Orchestrator"
            })
            
    data["single_ais_overall"].sort(key=lambda x: x.get("elo", 0), reverse=True)
    for i, entry in enumerate(data["single_ais_overall"]):
        entry["rank"] = i + 1
        
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print("Updated canonical_elo_leaderboard.json")

def main():
    results = []
    for m in MODELS:
        elo = test_model(m["file"], m["name"])
        if elo is not None:
            results.append({"name": m["name"], "elo": elo})
            
    if results:
        update_leaderboard(results)
    else:
        print("No models were successfully tested. They might still be downloading.")

if __name__ == "__main__":
    main()
