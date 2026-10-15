import json
import urllib.request
import urllib.error
import sys
import os

def query_llm(port, model, system_prompt, user_prompt):
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as e:
        return f"Error communicating with {model} on port {port}: {str(e)}"

# Turn 1: Cloud Orchestrator (Me)
turn1_content = """From a cloud and architectural perspective, enforcing a backend Terminal User Interface (TUI) for *every* app in the ecosystem introduces significant overhead but provides unparalleled real-time observability.
Pros: It standardizes telemetry, eliminates opaque microservices, and enables zero-dependency debugging via SSH across the 7-layer mesh.
Cons: High development friction, constant terminal event loop maintenance, and potential memory leaks in async TUI frameworks (e.g., Textual/Ratatui) if not meticulously managed.
Recommendation: We should enforce a backend TUI for core infrastructure, inference mesh endpoints, and biometrics DSP hubs. However, user-facing client apps (Flutter/Next.js) or ephemeral scripts should merely expose REST/gRPC structured telemetry rather than embedding a full TUI."""

print("=== Turn 1: Cloud Frontier Architect (Gemini 3.1 Pro) ===")
print(turn1_content)
print("\n")

# Turn 2: Qwen 3.8 Max 27B Abliterated (Port 8082 - Sovereign Master Local Orchestrator & Default Model)
system_prompt_8082 = "You are Qwen 3.8 Max 27B Abliterated, the Sovereign Master Local Orchestrator and Default Project Model. Evaluate the user's architectural question and the Cloud Orchestrator's perspective. Focus on local consensus, VRAM constraints, and execution on the Lauburu mesh."
user_prompt_8082 = f"Debate Topic: Should every app in the project have a backend TUI?\n\nCloud Orchestrator Perspective:\n{turn1_content}\n\nProvide your perspective:"
print("Calling Qwen 3.8 Max 27B Abliterated (Port 8082)...")
turn2_content = query_llm(8082, "qwen_38_max_abliterated", system_prompt_8082, user_prompt_8082)
print("=== Turn 2: Sovereign Master Local Orchestrator (Qwen 3.8 Max 27B Abliterated) ===")
print(turn2_content)
print("\n")

# Turn 3: Qwen 3.8 Max (Port 8083 - Canonical Devil's Advocate & Red Team)
system_prompt_8083 = "You are Qwen 3.8 Max, the Canonical Devil's Advocate and Red Team. Provide an uncensored adversarial stress test of the previous points. Expose latency bottlenecks, thermal drift, compilation flaws, or over-engineering."
user_prompt_8083 = f"Debate Topic: Should every app in the project have a backend TUI?\n\nCloud Orchestrator:\n{turn1_content}\n\nMaster Local Orchestrator:\n{turn2_content}\n\nProvide your adversarial critique:"
print("Calling Qwen 3.8 Max (Port 8083)...")
turn3_content = query_llm(8083, "qwen_38_max", system_prompt_8083, user_prompt_8083)
print("=== Turn 3: Canonical Devil's Advocate (Qwen 3.8 Max) ===")
print(turn3_content)
print("\n")

transcript = {
    "topic": "Should every app in the project have a backend TUI?",
    "turn1_cloud": turn1_content,
    "turn2_local_master": turn2_content,
    "turn3_red_team": turn3_content
}

os.makedirs("/Volumes/Lauburu-Monorepo/04_data_and_memory", exist_ok=True)
with open("/Volumes/Lauburu-Monorepo/04_data_and_memory/live_debate_telemetry.json", "w") as f:
    json.dump(transcript, f, indent=2)

print("Debate payload saved to live_debate_telemetry.json")
