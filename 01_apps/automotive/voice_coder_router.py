#!/usr/bin/env python3
"""
Specialized Voice AI Code Router
=================================
Routes transcribed voice intents and coding instructions to the optimal AI tier:
  1. Local Mesh Coder (Qwen 2.5 Coder 32B on :8081/:8082) -> Fast AST completions, $0 spend
  2. Antigravity Cloud Frontier (Gemini 3.7 Flash / Pro) -> Deep architectural refactors
  3. Bilateral Swarm Crucible (:8083) -> High-stakes debates & trade-offs

Supports hands-free execution and direct cell injection into JupyterLab & VS Code.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

import httpx

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LENS_DB = Path(os.path.expanduser("~/.lauburu/screen_lens.sqlite"))


def query_local_coder(prompt: str, context: str = "") -> Dict[str, Any]:
    url = "http://127.0.0.1:8081/v1/chat/completions"
    sys_prompt = (
        "You are the Specialized Voice Coder AI for the Lauburu Mesh ecosystem. "
        "Generate clean, robust, production-grade Python/Rust/TypeScript code matching the spoken prompt. "
        "Output ONLY the executable code block with concise docstrings. No filler conversational prose."
    )
    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"VOICE PROMPT: {prompt}\n\nCONTEXT: {context}"}
        ],
        "max_tokens": 1024,
        "temperature": 0.2
    }
    t0 = time.time()
    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            code = data["choices"][0]["message"]["content"]
            elapsed = round(time.time() - t0, 2)
            return {"tier": "Local Qwen 2.5 Coder 32B (Port 8081)", "code": code, "latency_s": elapsed}
    except Exception:
        # Fallback to Port 8083
        url_fb = "http://127.0.0.1:8083/v1/chat/completions"
        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(url_fb, json=payload)
                resp.raise_for_status()
                data = resp.json()
                code = data["choices"][0]["message"]["content"]
                elapsed = round(time.time() - t0, 2)
                return {"tier": "Local Fallback Coder (Port 8083)", "code": code, "latency_s": elapsed}
        except Exception as e:
            return {"tier": "Error", "code": f"# Error querying local coder: {e}", "latency_s": 0}



def inject_via_kdeconnect(text_payload: str, device_name: str = "MacBook_Pro"):
    print(f"📡 \033[1;35mInjecting payload via KDE Connect to {device_name}...\033[0m")
    import subprocess
    try:
        # Use kdeconnect-cli to share text directly to the target device's clipboard
        subprocess.run(
            ["kdeconnect-cli", "-n", device_name, "--share-text", text_payload],
            check=True,
            capture_output=True
        )
        print("✅ KDE Connect injection successful.")
    except FileNotFoundError:
        print("❌ kdeconnect-cli not found. Is KDE Connect installed and in PATH?")
    except subprocess.CalledProcessError as e:
        print(f"❌ KDE Connect failed: {e.stderr.decode()}")

def classify_and_route(voice_prompt: str) -> Dict[str, Any]:
    prompt_lower = voice_prompt.lower()
    
    # 1. Check for Debate / Architecture Comparison intent
    if any(k in prompt_lower for k in ["debate", "should we", "versus", "vs", "compare"]):
        print("⚖️ \033[1;33mClassified as Architecture Debate -> Routing to Bilateral Swarm...\033[0m")
        cmd = [sys.executable, str(REPO_ROOT / "05_agents_and_swarms/ai_debate/bilateral_swarm_debater.py"), "--topic", voice_prompt]
        import subprocess
        subprocess.run(cmd)
        return {"tier": "Bilateral Swarm Crucible", "action": "Debate completed"}

    # 2. Check for Test / Verification intent
    elif any(k in prompt_lower for k in ["run test", "run tests", "pytest", "verify code"]):
        print("🧪 \033[1;32mClassified as Test Verification -> Routing to Pytest Runner...\033[0m")
        import subprocess
        subprocess.run([sys.executable, "-m", "pytest", "02_ai_models_and_inference/tests/test_halda_scheduler.py"], cwd=str(REPO_ROOT))
        return {"tier": "Local Test Runner", "action": "Tests executed"}

    # 3. Check for Code Generation intent
    else:
        print(f"🎙️ \033[1;36mRouting Spoken Coding Prompt to Local AI Coder (Port 8081)...\033[0m")
        res = query_local_coder(voice_prompt)
        print(f"\n✅ Synthesized by \033[1;34m{res['tier']}\033[0m in {res['latency_s']}s:\n")
        print("```python")
        print(res["code"])
        print("```\n")
        
        # KDE Connect Integration
        if os.environ.get("ENABLE_KDE_CONNECT_INJECT") == "1":
            target_device = os.environ.get("KDE_TARGET_DEVICE", "MacBook_Pro")
            inject_via_kdeconnect(res["code"], target_device)
            
        return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Specialized Voice AI Code Router")
    parser.add_argument("prompt", type=str, nargs="*", help="Spoken intent or transcribed coding instruction")
    args = parser.parse_args()

    full_prompt = " ".join(args.prompt).strip() if args.prompt else "Write a function to plot heart rate variability from Movesense data"
    classify_and_route(full_prompt)
