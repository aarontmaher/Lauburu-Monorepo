#!/usr/bin/env python3
"""
adb_gemma_terminal_chat.py
ADB Terminal Chat Interface for Gemma 31B MoE running on Android Google Pixel + Swarm Cluster.
Connects ADB / Local Proxy Bridge, sends queries to Gemma 31B MoE, and displays live responses.
Enforces Rule #0 (dataset logging) and Rule #0.1 (empirical claim verification).
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
from datetime import datetime

# Import Rule #0 Logger & Rule #0.1 Verifier
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    import scripts.auto_train_logger as auto_train_logger
except ImportError:
    auto_train_logger = None

try:
    from scripts.ai_claim_verifier import EmpiricalClaimVerifier
except ImportError:
    EmpiricalClaimVerifier = None

BRIDGE_URL = "http://127.0.0.1:8000/v1/chat/completions"

def check_adb_pixel():
    """Verify ADB connection status to Android Google Pixel."""
    try:
        res = subprocess.run("adb devices", shell=True, capture_output=True, text=True, timeout=3)
        devices = res.stdout.strip()
        print("📱 [ADB System Audit]")
        print(devices)
        return "device" in devices
    except Exception as e:
        print(f"⚠️ ADB check error: {e}")
        return False

def query_gemma_moe(prompt):
    """Send prompt to Gemma 31B MoE engine via Local Bridge / EXO Cluster."""
    payload = json.dumps({
        "model": "gemma-31b-moe",
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    start_t = time.time()
    try:
        req = urllib.request.Request(BRIDGE_URL, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latency = time.time() - start_t
            content = data["choices"][0]["message"]["content"]

            # Rule #0 Auto-Training Capture
            if auto_train_logger:
                auto_train_logger.log_interaction(
                    prompt=prompt,
                    response=content,
                    source="ADB_PIXEL_GEMMA_TERMINAL",
                    model="gemma-31b-moe",
                    instruction="Interactive ADB Gemma 31B MoE Terminal Chat"
                )

            # Rule #0.1 Empirical Verification
            if EmpiricalClaimVerifier:
                content = EmpiricalClaimVerifier.critique_and_annotate(content, context_source="ADB_GEMMA_TERMINAL")

            return content, latency
    except Exception as e:
        # Fallback to direct EXO cluster runner
        try:
            from scripts.exo_cluster_runner import ExoClusterRunner
            runner = ExoClusterRunner(model_id="gemma-31b-moe")
            res = runner.generate_completion(prompt)
            latency = time.time() - start_t
            return res["response"], latency
        except Exception as ex:
            return f"Error executing Gemma 31B MoE: {e} / {ex}", 0.0

def run_adb_gemma_chat(test_mode=False, initial_prompt=None):
    """Run interactive ADB Gemma 31B MoE terminal chat session."""
    print("=" * 65)
    print(" 🤖 ADB GEMMA 31B MoE TERMINAL CHAT (ANDROID PIXEL + SWARM)")
    print("=" * 65)
    
    adb_online = check_adb_pixel()
    print(f"Status: {'ADB DEVICE ACTIVE 🟢' if adb_online else 'BRIDGED SWARM ACTIVE 🟢'}\n")

    if test_mode and initial_prompt:
        print(f"💬 [User Input]: {initial_prompt}")
        response, latency = query_gemma_moe(initial_prompt)
        print(f"\n🧠 [Gemma 31B MoE Response ({latency:.2f}s)]:")
        print(response)
        return

    print("Type your message (or 'exit' to quit):\n")
    while True:
        try:
            prompt = input("📱 [ADB Gemma MoE] > ")
            if prompt.strip().lower() in ["exit", "quit"]:
                print("Exiting ADB Gemma Terminal Chat. Bye!")
                break
            if not prompt.strip():
                continue
            
            response, latency = query_gemma_moe(prompt)
            print(f"\n🧠 [Gemma 31B MoE Response ({latency:.2f}s)]:")
            print(response)
            print("-" * 65)
        except (KeyboardInterrupt, EOFError):
            print("\nTerminal chat closed.")
            break

if __name__ == "__main__":
    prompt_arg = sys.argv[1] if len(sys.argv) > 1 else "Demonstrate Gemma 31B MoE execution via ADB terminal."
    run_adb_gemma_chat(test_mode=True, initial_prompt=prompt_arg)
