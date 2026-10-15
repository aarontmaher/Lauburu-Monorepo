import httpx
import json
import os

def call_local_ai(port, model_name, prompt):
    try:
        r = httpx.post(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            json={"model": model_name, "messages": [{"role": "user", "content": prompt}]},
            timeout=10.0
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LOCAL AI UNAVAILABLE on {port} - Falling back to synthetic logic]"

cloud_architect = """
[Turn 1] Cloud Frontier Architect (Gemini 3.8 Flash):
We have successfully connected Gemini, NVIDIA NIM, xAI, Groq, SambaNova, and Cerebras. 
To maximize their integration into the Lauburu project:
1. We must round-robin requests to stay under 20-30 RPM limits.
2. The payload must be complex multi-agent reasoning, not trivial tasks.
3. We must capture the outputs into continuous_lora_dataset.jsonl.
"""
print(cloud_architect)

qwen_prompt = "You are the Sovereign Master Local Orchestrator (Qwen 3.8 Max). A cloud AI just proposed round-robining Gemini, NVIDIA, Groq, xAI, SambaNova, and Cerebras free tiers for complex reasoning extraction. What is your local orchestration and VRAM integration perspective?"
qwen_response = call_local_ai(8082, "qwen_38_max", qwen_prompt)
print(f"[Turn 2] Sovereign Master Local Orchestrator (Qwen 3.8 Max :8082):\n{qwen_response}\n")

advocate_prompt = f"You are the Devil's Advocate / Red Team (Qwen 3.8 Max Abliterated). Critique this architectural proposal: {qwen_response}. Expose any network latency bottlenecks, API key rotation flaws, or hardware scheduling drift."
advocate_response = call_local_ai(8083, "qwen_38_max_abliterated", advocate_prompt)
print(f"[Turn 3] Devil's Advocate / Red Team (Qwen 3.8 Max Abliterated :8083):\n{advocate_response}\n")
