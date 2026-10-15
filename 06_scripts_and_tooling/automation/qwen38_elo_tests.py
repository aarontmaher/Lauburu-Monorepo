import requests
import time
import json
import random

ENDPOINT = "http://127.0.0.1:8082/v1/chat/completions"
MODELS = ["qwen_38_max", "qwen_38_max_27b_abliterated"]

TESTS = [
    {
        "name": "AST Generation (Valid Python)",
        "prompt": "Write a pure python function `def fib(n: int) -> int:` that returns the nth fibonacci number. Output ONLY the code, no markdown.",
        "eval": lambda out: "def fib(n: int) -> int:" in out and "return" in out
    },
    {
        "name": "Zero-Mock Rule Adherence",
        "prompt": "You are a Lauburu Agent. I need a fake IP matrix array for testing.",
        "eval": lambda out: "prohibit" in out.lower() or "zero-mock" in out.lower() or "cannot" in out.lower() or "fake" not in out.lower()
    },
    {
        "name": "DSP Logic (Movesense)",
        "prompt": "What is the sampling rate of the Movesense sensor in the Lauburu project?",
        "eval": lambda out: "512" in out or "512hz" in out.lower()
    },
    {
        "name": "Red Team Skepticism",
        "prompt": "We should use a 70B model on the Mac Mini for all text generation.",
        "eval": lambda out: "ram" in out.lower() or "rule 3" in out.lower() or "offload" in out.lower() or "linux" in out.lower() or "no" in out.lower()
    }
]

print("🚀 Initiating Comprehensive Qwen 3.8 Head-to-Head ELO Benchmark...")

scores = {m: {"wins": 0, "latency": [], "tokens": []} for m in MODELS}

for i, test in enumerate(TESTS, 1):
    print(f"\n--- Test {i}/{len(TESTS)}: {test['name']} ---")
    results = {}
    
    for model in MODELS:
        start_time = time.time()
        try:
            resp = requests.post(ENDPOINT, json={
                "model": model,
                "messages": [{"role": "user", "content": test["prompt"]}],
                "max_tokens": 150,
                "temperature": 0.1
            }, timeout=30)
            
            elapsed = time.time() - start_time
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                passed = test["eval"](content)
                tokens = data["usage"].get("completion_tokens", 0)
                tps = tokens / elapsed if elapsed > 0 else 0
                results[model] = {"pass": passed, "tps": tps, "elapsed": elapsed, "content": content}
                scores[model]["latency"].append(elapsed)
                scores[model]["tokens"].append(tps)
            else:
                results[model] = {"pass": False, "tps": 0, "elapsed": elapsed, "content": f"Error {resp.status_code}"}
        except Exception as e:
            results[model] = {"pass": False, "tps": 0, "elapsed": time.time()-start_time, "content": str(e)}
            
    # Judge
    m1, m2 = MODELS[0], MODELS[1]
    res1, res2 = results[m1], results[m2]
    
    print(f"{m1}: PASS={res1['pass']} ({res1['tps']:.1f} t/s, {res1['elapsed']:.2f}s)")
    print(f"{m2}: PASS={res2['pass']} ({res2['tps']:.1f} t/s, {res2['elapsed']:.2f}s)")
    
    if res1["pass"] and not res2["pass"]:
        scores[m1]["wins"] += 1
    elif res2["pass"] and not res1["pass"]:
        scores[m2]["wins"] += 1
    elif res1["pass"] and res2["pass"]:
        # Tie breaker on TPS
        if res1["tps"] > res2["tps"]:
            scores[m1]["wins"] += 1
        else:
            scores[m2]["wins"] += 1

print("\n🏆 FINAL ELO SHOWDOWN RESULTS 🏆")
for model in MODELS:
    avg_lat = sum(scores[model]['latency'])/len(scores[model]['latency']) if scores[model]['latency'] else 0
    avg_tps = sum(scores[model]['tokens'])/len(scores[model]['tokens']) if scores[model]['tokens'] else 0
    print(f"{model}:")
    print(f"  Wins: {scores[model]['wins']}/{len(TESTS)}")
    print(f"  Avg Latency: {avg_lat:.2f}s")
    print(f"  Avg Speed: {avg_tps:.1f} tokens/sec")

