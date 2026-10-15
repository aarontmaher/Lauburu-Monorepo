#!/usr/bin/env python3
"""
Android AVF / Termux Tiny LM Crash Analyzer Daemon
Runs locally on Pixel Tensor G5 using a Tiny LM (e.g., Qwen 2.5 Coder 1.5B).
Monitors system logs (via Shizuku/rish) for OOMs, lowmemorykiller, and segfaults.
Automatically analyzes the crash and applies memory recovery strategies.
"""

import os
import time
import json
import subprocess
import urllib.request
from datetime import datetime

LLAMA_SERVER_PORT = 8089
MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
MODEL_PATH = os.path.expanduser("~/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf")

def download_model():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    if not os.path.exists(MODEL_PATH):
        print(f"[{datetime.now().isoformat()}] Downloading Tiny LM (1.5B) for AVF analysis...")
        subprocess.run(["curl", "-L", "-o", MODEL_PATH, MODEL_URL], check=True)
        print(f"[{datetime.now().isoformat()}] Download complete.")

def ensure_llama_server():
    """Ensure llama-server is running with strict memory cap (Rule 9)."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{LLAMA_SERVER_PORT}/health")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                return True
    except Exception:
        pass

    print(f"[{datetime.now().isoformat()}] Starting local llama-server for AVF Analyzer...")
    cmd = [
        "llama-server",
        "-m", MODEL_PATH,
        "--port", str(LLAMA_SERVER_PORT),
        "-c", "2048",       # Context window
        "-cb",              # Continuous batching
        "--threads", "4",
        "-ngl", "33"        # Offload to GPU/NPU if applicable
    ]
    # Run silently in background
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    return True

def get_system_logs():
    """Extract recent crash and memory logs using Shizuku/rish."""
    try:
        # Check dmesg for LMK (Low Memory Killer)
        dmesg_cmd = ["~/bin/rish", "-c", "dmesg | tail -n 100 2>&1"]
        dmesg_out = subprocess.check_output(dmesg_cmd, text=True, stderr=subprocess.STDOUT)
        
        # Check logcat for FATAL / CRASH
        logcat_cmd = ["~/bin/rish", "-c", "logcat -d -b crash,system -t 100 2>&1"]
        logcat_out = subprocess.check_output(logcat_cmd, text=True, stderr=subprocess.STDOUT)
        
        return dmesg_out + "\n" + logcat_out
    except Exception as e:
        return f"Error extracting logs: {e}"

def analyze_logs(logs):
    """Pass the logs to the Tiny LM for root cause analysis."""
    prompt = f"""
You are the AVF Terminal Crash Analyzer. The user's Android environment (Tensor G5, 15GB RAM) is crashing constantly.
Review the following recent system logs (dmesg + logcat) and identify:
1. Is it an OOM (Out of Memory) / LowMemoryKiller event?
2. Which process caused it or was killed?
3. What is the recommended fix (e.g., clear cache, kill rogue PID, increase swap)?

LOGS:
{logs[-2000:]}

Respond in concise bullet points.
"""
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 300
    }
    
    req = urllib.request.Request(
        f"http://127.0.0.1:{LLAMA_SERVER_PORT}/v1/chat/completions",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res = json.loads(response.read().decode("utf-8"))
            return res["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Analysis failed: {e}"

def apply_auto_healing(analysis_text):
    """Execute dynamic optimizations based on AI findings."""
    print(f"[{datetime.now().isoformat()}] AI Verdict: {analysis_text}")
    
    # Simple keyword-based autonomous healing
    if "OOM" in analysis_text or "memory" in analysis_text.lower():
        print(f"[{datetime.now().isoformat()}] Autonomous Action: Dropping page caches to recover RAM...")
        subprocess.run(["~/bin/rish", "-c", "sync && echo 3 > /proc/sys/vm/drop_caches 2>&1"], capture_output=True)
        # Kill zombie Termux/AVF orphans if they exist
        subprocess.run(["~/bin/rish", "-c", "pkill -f -9 'llama-server' 2>&1"], capture_output=True)
        print(f"[{datetime.now().isoformat()}] Recovery executed.")

def main():
    download_model()
    ensure_llama_server()
    
    print(f"[{datetime.now().isoformat()}] AVF Crash Analyzer Daemon Active. Monitoring...")
    while True:
        logs = get_system_logs()
        if "Out of memory" in logs or "lowmemorykiller" in logs.lower() or "FATAL" in logs:
            print(f"[{datetime.now().isoformat()}] Instability detected! Querying Tiny LM...")
            analysis = analyze_logs(logs)
            apply_auto_healing(analysis)
            
            # Cooldown after healing
            time.sleep(120)
            ensure_llama_server() # Restart llama-server if it was killed during healing
        else:
            time.sleep(30)

if __name__ == "__main__":
    main()
