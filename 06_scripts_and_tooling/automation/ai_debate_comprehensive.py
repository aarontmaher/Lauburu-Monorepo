import httpx
import json

def call_local_ai(port, model_name, prompt):
    try:
        r = httpx.post(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            json={"model": model_name, "messages": [{"role": "user", "content": prompt}]},
            timeout=40.0
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LOCAL AI UNAVAILABLE on {port} - Error: {str(e)}]"

cloud_architect = """
[Turn 1] Cloud Frontier Architect (Gemini 3.8 Flash):
My perspective on the whole project:
1. LoRA Pipeline: We should use a Continuous QLoRA background process (e.g. MLX) that distills the traces harvested from our Multi-Cloud Daemon during off-peak hours (or dynamically on the M4 Air).
2. Bluetooth Terminal: Needs robust auto-reconnection and buffering. If the Android host goes to sleep (Doze mode), we risk dropping BLE packets.
3. Lens/Life Companion: Continuous VLA (Vision-Language-Action) requires aggressive frame-dropping and speculative token reduction, otherwise the 128K context fills up in minutes.
"""
print(cloud_architect)

qwen_prompt = """As the Sovereign Master Local Orchestrator (Qwen 3.8 Max), provide a 3-paragraph response addressing:
1. The optimal integration method for our 24/7 LoRA training pipeline (which distills multi-cloud reasoning traces).
2. A project overview feedback focusing on our Bluetooth Terminal and the Screen Lens Life Companion app.
3. Improvements to ensure seamless VRAM pooling across the 7-layer mesh.
"""
qwen_response = call_local_ai(8082, "qwen_38_max", qwen_prompt)
print(f"[Turn 2] Sovereign Master Local Orchestrator (Qwen 3.8 Max :8082):\n{qwen_response}\n")

advocate_prompt = f"""As the Devil's Advocate / Red Team (Qwen 3.8 Max Abliterated), provide a 2-paragraph critique of this architecture: {qwen_response}. 
Expose vulnerabilities in the Bluetooth terminal (e.g. latency, packet loss), the Screen Lens companion (privacy, context bloat), and the LoRA pipeline (overfitting on synthetic cloud data)."""
advocate_response = call_local_ai(8083, "qwen_38_max_abliterated", advocate_prompt)
print(f"[Turn 3] Devil's Advocate / Red Team (Qwen 3.8 Max Abliterated :8083):\n{advocate_response}\n")
