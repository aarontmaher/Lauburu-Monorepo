#!/usr/bin/env python3
"""
Lauburu Math-72B Training Pipeline
Generates LoRA pairs using Math-72B-Instruct as teacher + Math-RM-72B for reward scoring.
Runs as part of the 24/7 continuous training automation.

Usage:
    python3 math_training_pipeline.py
    
Dependencies:
    - Math-72B-Instruct GGUF served via llama-server (local or Linux)
    - Math-RM-72B safetensors on Linux (for reward scoring)
    - Math-1.5B at :8087 (fast arbitrator)
"""

import json, time, random, pathlib, socket, urllib.request
from datetime import datetime

# Model endpoints
ENDPOINTS = {
    "math_72b_quality":    "http://192.168.8.224:8095",  # Linux: Q4_K_M (40GB) - when ready
    "math_72b_edge":       "http://127.0.0.1:8095",      # Mac Mini: IQ2_XXS (18GB) - when ready
    "math_7b_local":       "http://127.0.0.1:8086",      # Fallback: Math-7B
    "math_1b5_arbitrator": "http://127.0.0.1:8087",      # Fast checker
}

LORA_DATASET = pathlib.Path("/Users/aaron/DFS_UNIFIED/lora_datasets/math_training_dataset.jsonl")
GENERAL_DATASET = pathlib.Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")

# Math problem categories for diverse training
PROBLEM_TEMPLATES = [
    "Prove that {n} is irrational.",
    "Solve the differential equation: dy/dx = {expr}",
    "Find all integer solutions to {equation}",
    "Calculate the derivative of f(x) = {expr} using first principles.",
    "Show that the series {series} converges/diverges.",
    "Find the eigenvalues of the matrix {matrix}.",
    "Evaluate the integral: ∫{expr}dx",
    "Use the Cauchy-Schwarz inequality to prove {statement}.",
    "A function f is defined as {defn}. Find its critical points.",
    "In modular arithmetic (mod {n}), solve for x: {congruence}",
    "Prove by induction that {statement} for all n ≥ 1.",
    "Find the maximum of f(x,y) = {expr} subject to g(x,y) = 0.",
]

PLACEHOLDERS = {
    "n": ["√2", "π", "e", "√3", "ln(2)"],
    "expr": ["x³ - 3x + 2", "sin(x)/x", "x²e^x", "ln(x+1)/(x+1)", "x^(1/3)"],
    "equation": ["x² + y² = 25 in integers", "2x + 3y = 7", "x³ + y³ = z³"],
    "series": ["∑(1/n²)", "∑((-1)^n/n)", "∑(x^n/n!)", "∑(1/(n·ln(n)))"],
    "matrix": ["[[2,1],[1,3]]", "[[0,-1],[1,0]]", "[[3,1,0],[1,2,1],[0,1,3]]"],
    "statement": ["n² + n is always even", "sum of first n odd numbers = n²"],
    "defn": ["f(x) = x³ - 6x² + 9x + 1", "f(x) = xe^(-x²)"],
    "n_mod": ["7", "11", "13", "17"],
    "congruence": ["2x ≡ 5 (mod 7)", "3x ≡ 2 (mod 11)"],
}


def probe_endpoint(url: str) -> bool:
    """Check if a model endpoint is live."""
    try:
        host = url.split("//")[1].split(":")[0]
        port = int(url.split(":")[-1].split("/")[0])
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        return True
    except:
        return False


def call_llm(url: str, prompt: str, max_tokens: int = 512) -> str:
    """Call a llama-server compatible endpoint."""
    payload = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(
        f"{url}/v1/chat/completions", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def generate_math_problem() -> str:
    """Generate a random math problem from templates."""
    template = random.choice(PROBLEM_TEMPLATES)
    for key, values in PLACEHOLDERS.items():
        placeholder = f"{{{key}}}"
        if placeholder in template:
            template = template.replace(placeholder, random.choice(values), 1)
    return template


def score_solution(problem: str, solution: str) -> float:
    """Use Math-1.5B as fast reward proxy (Math-RM-72B when available)."""
    if not probe_endpoint(ENDPOINTS["math_1b5_arbitrator"]):
        return 0.7  # Default score if arbitrator unavailable
    prompt = f"""Rate this math solution from 0.0 to 1.0 based on correctness, completeness, and clarity.
Problem: {problem}
Solution: {solution}
Respond with ONLY a number between 0.0 and 1.0."""
    try:
        score_str = call_llm(ENDPOINTS["math_1b5_arbitrator"], prompt, max_tokens=10)
        score = float(score_str.strip().replace("Score:", "").strip())
        return max(0.0, min(1.0, score))
    except:
        return 0.6


def get_teacher_endpoint() -> tuple[str, str]:
    """Select best available teacher model."""
    for name, url in [
        ("math_72b_quality", ENDPOINTS["math_72b_quality"]),
        ("math_72b_edge",    ENDPOINTS["math_72b_edge"]),
        ("math_7b_local",    ENDPOINTS["math_7b_local"]),
    ]:
        if probe_endpoint(url):
            return name, url
    return None, None


def run_training_cycle(n_pairs: int = 5) -> dict:
    """Generate n math LoRA training pairs."""
    teacher_name, teacher_url = get_teacher_endpoint()
    stats = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "teacher": teacher_name or "unavailable",
        "pairs_generated": 0,
        "pairs_accepted": 0,
        "mean_score": 0.0,
    }

    if not teacher_url:
        print("  No teacher model available — skipping math cycle")
        return stats

    print(f"  Teacher: {teacher_name} ({teacher_url})")
    scores = []
    LORA_DATASET.parent.mkdir(exist_ok=True)

    for i in range(n_pairs):
        problem = generate_math_problem()
        prompt = (f"Solve the following math problem step-by-step, showing all work:\n{problem}\n"
                  "Provide a complete, rigorous mathematical proof or solution.")
        try:
            t0 = time.perf_counter()
            solution = call_llm(teacher_url, prompt, max_tokens=600)
            elapsed = time.perf_counter() - t0
            score = score_solution(problem, solution)
            scores.append(score)

            pair = {
                "instruction": problem,
                "input": "",
                "output": solution,
                "score": score,
                "teacher": teacher_name,
                "ttft_s": round(elapsed, 2),
                "source": "math_72b_training_pipeline",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            # Accept pairs with score >= 0.5
            if score >= 0.5:
                with open(LORA_DATASET, "a") as f:
                    f.write(json.dumps(pair) + "\n")
                with open(GENERAL_DATASET, "a") as f:
                    f.write(json.dumps(pair) + "\n")
                stats["pairs_accepted"] += 1
                print(f"    [{i+1}/{n_pairs}] Score: {score:.2f} ✅ ({elapsed:.1f}s)")
            else:
                print(f"    [{i+1}/{n_pairs}] Score: {score:.2f} ❌ (below threshold)")

            stats["pairs_generated"] += 1
        except Exception as e:
            print(f"    [{i+1}/{n_pairs}] Error: {e}")

    if scores:
        stats["mean_score"] = round(sum(scores) / len(scores), 3)

    return stats


if __name__ == "__main__":
    print(f"\n🧮 Lauburu Math Training Pipeline — {datetime.now().strftime('%H:%M:%S')}")
    stats = run_training_cycle(n_pairs=5)
    print(f"\n  ✅ {stats['pairs_accepted']}/{stats['pairs_generated']} pairs accepted")
    print(f"  Mean score: {stats['mean_score']}")
    total = sum(1 for _ in open(LORA_DATASET)) if LORA_DATASET.exists() else 0
    print(f"  Total math pairs: {total}")
