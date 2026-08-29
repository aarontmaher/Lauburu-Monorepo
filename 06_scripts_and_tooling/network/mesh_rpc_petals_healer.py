#!/usr/bin/env python3
"""
Lauburu Mesh — llama.cpp RPC + Petals + Continuous AI Debate Self-Healing Governor
Runs across all 7 physical nodes.
Periodic self-healer daemon replacement for launchd (100% Python 3.9+ compatible).
"""

import os
import sys
import time
import json
import socket
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LOG_FILE = REPO / "logs/mesh_rpc_petals.log"
LORA_LOG = REPO / "data/lora_datasets/nomad_autonomous_actions.jsonl"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
LORA_LOG.parent.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def log_lora(action: str, result: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        record = {
            "timestamp_utc": ts,
            "action": action,
            "result": result,
            "nomad_agent": "mesh_rpc_petals_healer_py v2.0"
        }
        with open(LORA_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

# Node metadata
NODES = {
    "macbook_pro": {
        "user": "aaronmaher",
        "host": "192.168.8.127",
        "port": 22,
        "jump": "root@192.168.8.1",
        "rpc_bin": "/Users/aaronmaher/llama.cpp/build/bin/ggml-rpc-server",
        "petals_model": None
    },
    "linux_head": {
        "user": "linux",
        "host": "100.101.39.98",
        "port": 22,
        "jump": None,
        "rpc_bin": "/home/linux/llama.cpp/build/bin/ggml-rpc-server",
        "petals_model": "Qwen/Qwen2-7B-Instruct"
    },
    "pixel": {
        "user": "u0_a363",
        "host": "100.73.38.87",
        "port": 8022,
        "jump": None,
        "rpc_bin": "/data/data/com.termux/files/home/llama.cpp/build/bin/ggml-rpc-server",
        "petals_model": "Qwen/Qwen2-7B-Instruct"
    }
}

def tcp_probe(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False

def http_health(url: str, timeout: float = 2.0) -> bool:
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        data = json.loads(r.read())
        return data.get("status") == "ok"
    except Exception:
        return False

def ssh_exec(node_key: str, remote_cmd: str) -> str:
    cfg = NODES[node_key]
    ssh_args = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        "-o", "BatchMode=yes",
        "-p", str(cfg["port"])
    ]
    if cfg["jump"]:
        ssh_args.extend(["-o", f"ProxyJump={cfg['jump']}"])
    ssh_args.extend([f"{cfg['user']}@{cfg['host']}", remote_cmd])
    try:
        res = subprocess.run(ssh_args, capture_output=True, text=True, timeout=15)
        return res.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def heal_local_models():
    # 1. Proxy (:8080)
    if http_health("http://127.0.0.1:8080/health"):
        log("✅ Local proxy :8080 HEALTHY")
    else:
        log("⚠️ Local proxy :8080 DOWN — restarting LaunchAgent")
        subprocess.run(["launchctl", "unload", "/Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist"], capture_output=True)
        time.sleep(1)
        subprocess.run(["launchctl", "load", "/Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist"], capture_output=True)
        log_lora("RESTART_PROXY_8080", "RELOADED")

    # 2. Qwen Abliterated (:8085)
    if http_health("http://127.0.0.1:8085/health"):
        log("✅ Qwen-Abliterated :8085 HEALTHY")
    else:
        log("⚠️ Qwen-Abliterated :8085 DOWN — restarting")
        subprocess.run(["pkill", "-f", "Qwen2.5-7B-Instruct-abliterated"], capture_output=True)
        time.sleep(1)
        cmd = [
            "/Users/aaron/.local/bin/llama-server",
            "-m", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf",
            "--port", "8085",
            "--host", "0.0.0.0",
            "-ngl", "99",
            "-c", "2048",
            "-b", "512",
            "-t", "8"
        ]
        with open(REPO / "logs/qwen7b_abliterated_8085.log", "a") as out:
            subprocess.Popen(cmd, stdout=out, stderr=out)
        log("✅ Qwen-Abliterated :8085 restarted")
        log_lora("RESTART_QWEN_8085", "RESTARTED")

    # 3. Qwen Coder 7B (:8083)
    if http_health("http://127.0.0.1:8083/health"):
        log("✅ Qwen-Coder-7B :8083 HEALTHY")
    else:
        log("⚠️ Qwen-Coder-7B :8083 DOWN — restarting")
        cmd = [
            "/Users/aaron/.local/bin/llama-server",
            "-m", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
            "--port", "8083",
            "--host", "0.0.0.0",
            "-ngl", "99",
            "-c", "4096"
        ]
        with open(REPO / "logs/qwen_coder_8083.log", "a") as out:
            subprocess.Popen(cmd, stdout=out, stderr=out)
        log("✅ Qwen-Coder-7B :8083 restarted")
        log_lora("RESTART_QWEN_8083", "RESTARTED")

def heal_rpc(node_key: str):
    cfg = NODES[node_key]
    host = cfg["host"]
    if tcp_probe(host, 50052):
        log(f"✅ RPC {node_key} ({host}:50052) HEALTHY")
    else:
        log(f"⚠️ RPC {node_key} OFFLINE — restarting")
        cmd = f"nohup {cfg['rpc_bin']} -H 0.0.0.0 -p 50052 > /tmp/llama_rpc_{node_key}.log 2>&1 & echo started"
        res = ssh_exec(node_key, cmd)
        log(f"  Result: {res}")
        log_lora(f"HEAL_RPC_{node_key.upper()}", res)

def heal_petals(node_key: str):
    cfg = NODES[node_key]
    if not cfg["petals_model"]:
        return
    res = ssh_exec(node_key, "pgrep -f petals | wc -l")
    if res.isdigit() and int(res) > 0:
        log(f"✅ Petals {node_key} RUNNING ({res} procs)")
    else:
        log(f"⚠️ Petals {node_key} OFFLINE — launching server")
        cmd = (
            f"nohup python3 -m petals.cli.run_server {cfg['petals_model']} "
            f"--device cpu --num_blocks 4 --throughput 1 --port 31337 "
            f"> /tmp/petals_{node_key}.log 2>&1 & echo started"
        )
        out = ssh_exec(node_key, cmd)
        log(f"  Result: {out}")
        log_lora(f"HEAL_PETALS_{node_key.upper()}", out)

def run_ai_debate():
    log("🗣️ Executing Continuous Free AI Debate Cycle...")
    try:
        script = REPO / "05_agents_and_swarms/ai_debate/continuous_free_ai_debate_cycle.py"
        res = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            log("✅ AI Debate Cycle completed successfully and recorded to Obsidian + JSONL")
        else:
            log(f"⚠️ AI Debate Cycle returned code {res.returncode}: {res.stderr[:200]}")
    except Exception as e:
        log(f"❌ AI Debate Cycle error: {e}")

def run_agentworld_refresh():
    log("🤖 Refreshing AgentWorld dataset conversion...")
    try:
        script = REPO / "04_data_and_memory/agentworld_train.py"
        res = subprocess.run([sys.executable, str(script), "--stage", "1", "--dry-run"], capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            log("✅ AgentWorld dataset sync complete")
    except Exception as e:
        log(f"⚠️ AgentWorld sync error: {e}")

def main():
    log("════════ Mesh Self-Healing & AI Debate Governor Cycle ════════")
    heal_local_models()
    for n in ["macbook_pro", "linux_head", "pixel"]:
        heal_rpc(n)
    heal_petals("linux_head")
    run_ai_debate()
    run_agentworld_refresh()
    log("════════ Governor Cycle Complete ════════")

if __name__ == "__main__":
    main()
