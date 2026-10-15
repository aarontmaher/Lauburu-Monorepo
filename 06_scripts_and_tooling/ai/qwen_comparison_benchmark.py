import subprocess
import time
import urllib.request
import json
import os

MODELS = {
    "27B_Abliterated": "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Huihui-Qwen3.8-27B-abliterated-UD-DW-Q4_K_M.gguf",
    "Turbo_Brilliance_2.6B": "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/models/LFM2.5-2.6B-Turbo-Brilliance/LFM2.5-2.6B-Q3.8-TBrilliance-NEO-MAX-Q6_K.gguf",
    "Qwen2.5_7B_Abliterated": "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf"
}

PROMPT_ECOMMERCE = "<|im_start|>user\nA customer wants to trade a used PS5 Slim for a brand new iPhone 16 Pro (Retail $1800, but has a cracked screen so valued at $900). A used PS5 Slim is worth $400. How much cash delta should they add to make it a fair trade? Answer concisely.<|im_end|>\n<|im_start|>assistant\n"

PROMPT_GLOBAL = "<|im_start|>user\nExplain the fundamental baseline trinity of the Lauburu project and the role of the Qwen Master Orchestrator in 3 sentences.<|im_end|>\n<|im_start|>assistant\n"

LLAMA_SERVER = "/Users/aaron/.local/bin/llama-server"

def start_server(model_path):
    cmd = [
        LLAMA_SERVER,
        "-m", model_path,
        "-c", "4096",
        "-ngl", "99",
        "--port", "8085",
        "--host", "127.0.0.1"
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ready = False
    for _ in range(30):
        try:
            req = urllib.request.Request("http://127.0.0.1:8085/health", method="GET")
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    ready = True
                    break
        except Exception:
            pass
        time.sleep(1)
    if not ready:
        process.kill()
        raise Exception("Server failed to start")
    return process

def run_inference(prompt):
    payload = json.dumps({
        "prompt": prompt,
        "n_predict": 150,
        "temperature": 0.1,
        "stop": ["<|im_end|>", "<|im_start|>"]
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "http://127.0.0.1:8085/completion", 
        data=payload, 
        headers={'Content-Type': 'application/json'}
    )
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res_body = response.read().decode('utf-8')
            data = json.loads(res_body)
    except Exception as e:
        return f"ERROR: {e}", 0, 0
        
    duration = time.time() - start
    
    text = data.get("content", "")
    tokens_eval = data.get("tokens_predicted", 0)
    tps = tokens_eval / duration if duration > 0 else 0
    return text, duration, tps

def score_ecommerce(text):
    text = text.lower()
    score = 0
    if "500" in text:
        score += 50
    if "900" in text and "400" in text:
        score += 25
    if len(text) < 300:
        score += 25 # concise
    return score

def score_global(text):
    text = text.lower()
    score = 0
    if "lauburu" in text:
        score += 20
    if "orchestrator" in text or "qwen" in text:
        score += 40
    if "trinity" in text or "baseline" in text or "mesh" in text:
        score += 40
    return score

def main():
    print("Starting Qwen 3.8 Comparison Benchmark...")
    scores = {m: {"ecom": 0, "global": 0, "tps": 0.0} for m in MODELS}
    
    for name, path in MODELS.items():
        if not os.path.exists(path):
            print(f"Skipping {name}, file not found: {path}")
            del scores[name]
            continue
            
        print(f"\nEvaluating {name}...")
        try:
            server_process = start_server(path)
            
            # E-commerce
            text_ecom, dur_ecom, tps_ecom = run_inference(PROMPT_ECOMMERCE)
            ecom_score = score_ecommerce(text_ecom)
            scores[name]["ecom"] = ecom_score
            
            # Global
            text_global, dur_global, tps_global = run_inference(PROMPT_GLOBAL)
            global_score = score_global(text_global)
            scores[name]["global"] = global_score
            
            avg_tps = (tps_ecom + tps_global) / 2
            scores[name]["tps"] = avg_tps
            
            print(f"[{name}] E-com: {ecom_score}/100, Global: {global_score}/100, Speed: {avg_tps:.2f} t/s")
            print(f"E-com sample: {text_ecom[:100]}...")
            print(f"Global sample: {text_global[:100]}...")
            
        except Exception as e:
            print(f"Failed to evaluate {name}: {e}")
        finally:
            server_process.kill()
            server_process.wait()
            time.sleep(2) # ensure port is freed

    print("\n--- FINAL RESULTS ---")
    best_name = None
    best_score = -1
    
    for name, data in scores.items():
        total = data["ecom"] + data["global"]
        print(f"{name}: Total {total} | TPS: {data['tps']:.2f}")
        if total > best_score:
            best_score = total
            best_name = name
            
    print(f"\nWINNER: {best_name} with {best_score} points!")
    
    # Identify losers
    losers = [name for name in scores.keys() if name != best_name and name in scores]
    for loser in losers:
        print(f"LOSER to be deleted: {loser} -> {MODELS[loser]}")
        try:
            os.remove(MODELS[loser])
            print(f"DELETED: {loser}")
        except Exception as e:
            print(f"Failed to delete {loser}: {e}")
            
    print(f"\nBenchmark Complete. WINNER: {best_name}")

if __name__ == "__main__":
    main()
