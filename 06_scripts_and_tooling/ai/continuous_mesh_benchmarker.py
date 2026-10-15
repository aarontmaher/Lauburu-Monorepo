import subprocess, time, urllib.request, json, os, glob

MODEL_DIR = "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference"
LEADERBOARD_FILE = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_local_ai_leaderboard.json"
LLAMA_SERVER = "llama-server"

PROMPTS = {
    "ecommerce": "<|im_start|>user\nWhat is the maximum wholesale tier price for 50+ B2B rashguards based on standard Lauburu economics?<|im_end|>\n<|im_start|>assistant\n",
    "technical": "<|im_start|>user\nExplain why pipeline parallelism (llama.cpp) is preferred over tensor parallelism (prima.cpp) on 10ms+ latency links.<|im_end|>\n<|im_start|>assistant\n"
}

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, 'r') as f:
            return json.load(f)
    return {"rankings": {}, "benchmarked_models": []}

def save_leaderboard(data):
    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def start_server(model_path):
    cmd = [LLAMA_SERVER, "-m", model_path, "-c", "2048", "-ngl", "99", "--port", "9092", "--host", "127.0.0.1"]
    print(f"Starting server for {os.path.basename(model_path)}...")
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(45):
        try:
            req = urllib.request.Request("http://127.0.0.1:9092/health", method="GET")
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200: return process
        except Exception: time.sleep(1)
    process.kill()
    return None

def run_inference(prompt):
    payload = json.dumps({"prompt": prompt, "n_predict": 100, "temperature": 0.1, "stop": ["<|im_end|>", "<|im_start|>"]}).encode('utf-8')
    req = urllib.request.Request("http://127.0.0.1:9092/completion", data=payload, headers={'Content-Type': 'application/json'})
    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=120) as response:
            t1 = time.time()
            res = json.loads(response.read().decode())
            tokens = res.get("tokens_predicted", 0)
            return {"text": res.get("content", "").strip(), "tok_sec": tokens / (t1 - t0) if t1 > t0 else 0, "tokens": tokens}
    except Exception as e:
        return {"error": str(e)}

models = glob.glob(f"{MODEL_DIR}/**/*.gguf", recursive=True)
leaderboard = load_leaderboard()

print(f"Found {len(models)} models to benchmark.")
for model_path in models:
    name = os.path.basename(model_path)
    if "vocab" in name.lower() or name in leaderboard["benchmarked_models"]: continue
    
    server = start_server(model_path)
    if not server:
        print(f"Failed to load {name}. Skipping.")
        continue
        
    print(f"Benchmarking {name}...")
    scores = []
    responses = {}
    for cat, prompt in PROMPTS.items():
        res = run_inference(prompt)
        if "error" not in res and res.get("tok_sec") > 0:
            scores.append(res["tok_sec"])
            responses[cat] = res["text"]
            
    server.kill()
    time.sleep(2)
    
    if scores:
        avg_speed = sum(scores) / len(scores)
        leaderboard["rankings"][name] = {
            "avg_tok_sec": round(avg_speed, 2),
            "responses": responses
        }
        leaderboard["benchmarked_models"].append(name)
        save_leaderboard(leaderboard)
        print(f"{name} clocked at {round(avg_speed, 2)} tok/s.")

# Rank them
ranked = sorted(leaderboard["rankings"].items(), key=lambda x: x[1]["avg_tok_sec"], reverse=True)
print("\n=== CURRENT ELO / SPEED RANKINGS ===")
for i, (m, data) in enumerate(ranked):
    print(f"{i+1}. {m} - {data['avg_tok_sec']} tok/s")
