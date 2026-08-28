#!/usr/bin/env python3
"""
Nomad Courier Self-Healer
Lauburu 7-Layer Mesh Governor — 6-Tier Autonomous Self-Healing

Tiers:
  1. Service Port Health  (AI proxy, models, WoL API)
  2. RPC Mesh Probe       (Tailscale node connectivity)
  3. AI Model Status      (llama-server health + loading check)
  4. Git & Storage Health (locks, vault, disk headroom)
  5. Skills Guardian      (Antigravity skill sync)
  6. LoRA Serialization   (action log → training pairs)

Usage:
  python3 nomad_courier_self_healer.py --once
  python3 nomad_courier_self_healer.py --daemon
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA = REPO / "data/network"
LORA = REPO / "data/lora_datasets"
STATUS_FILE = DATA / "nomad_self_healer_status.json"
LORA_LOG    = LORA / "nomad_autonomous_actions.jsonl"
LOGS        = REPO / "logs"

DATA.mkdir(parents=True, exist_ok=True)
LORA.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

# ── Model launch configs ───────────────────────────────────────────────────────
LLAMA_BIN = "/Users/aaron/.local/bin/llama-server"
MODEL_VAULT = REPO / "02_ai_models_and_inference/model_vault_gguf"

MANAGED_MODELS = {
    8083: {
        "name": "qwen_coder_7b",
        "model": MODEL_VAULT / "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "args": ["-ngl", "99", "-c", "8192"],
        "rpc": [],
    },
    8082: {
        "name": "mistral_nemo_12b",
        "model": MODEL_VAULT / "Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf",
        "args": ["-ngl", "99", "-c", "8192"],
        "rpc": [],
    },
    8084: {
        "name": "nemotron_70b",
        "model": MODEL_VAULT / "Llama-3.1-Nemotron-70B-Instruct-HF-abliterated-Q4_K_M.gguf",
        "args": ["-ngl", "99", "-c", "4096", "-ts", "43,28,29"],
        "rpc": ["100.93.158.96:50052", "100.73.38.87:50052"],  # MacBook Air + Pixel
    },
}

# ── Utility ───────────────────────────────────────────────────────────────────

def probe_tcp(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def probe_http(url: str, timeout: float = 2.0) -> tuple:
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        body = r.read().decode(errors="replace")
        return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, str(e)
    except Exception as e:
        return None, str(e)[:80]


def model_is_running(port: int) -> bool:
    return probe_tcp("127.0.0.1", port, timeout=0.5)


def model_is_ready(port: int) -> bool:
    code, body = probe_http(f"http://127.0.0.1:{port}/health", timeout=1.5)
    if code == 200:
        try:
            return json.loads(body).get("status") == "ok"
        except Exception:
            return False
    return False


def launch_model(port: int, cfg: dict, active_rpc: list) -> str:
    """Start a llama-server for the given port config."""
    model_path = cfg["model"]
    if not model_path.exists():
        return f"SKIP_MISSING_MODEL:{model_path.name}"
    
    # Filter RPC nodes to only active ones
    rpc_nodes = [r for r in cfg["rpc"] if r.split(":")[0] in active_rpc]
    
    cmd = [
        LLAMA_BIN, "-m", str(model_path),
        "--port", str(port),
        "--host", "0.0.0.0",
        *cfg["args"],
    ]
    if rpc_nodes:
        cmd += ["--rpc", ",".join(rpc_nodes)]
    
    log_file = LOGS / f"{cfg['name']}_{port}.log"
    with open(log_file, "a") as lf:
        subprocess.Popen(cmd, stdout=lf, stderr=lf, start_new_session=True)
    
    return f"LAUNCHED:{cfg['name']}:{port}" + (f":rpc={len(rpc_nodes)}" if rpc_nodes else "")


# ── Nomad Governor Cycle ───────────────────────────────────────────────────────

def run_cycle() -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    report = {"timestamp_utc": ts, "tiers": {}}
    actions = []

    # ── T1: Service Port Health ────────────────────────────────────────────────
    service_ports = {
        "ai_proxy_8080":     ("127.0.0.1", 8080),
        "mistral_nemo_8082": ("127.0.0.1", 8082),
        "qwen_coder_8083":   ("127.0.0.1", 8083),
        "nemotron_70b_8084": ("127.0.0.1", 8084),
        "wol_api_18802":     ("127.0.0.1", 18802),
        "web_ui_4000":       ("127.0.0.1", 4000),
    }
    t1 = {}
    for name, (h, p) in service_ports.items():
        t1[name] = "ONLINE" if probe_tcp(h, p, 0.5) else "OFFLINE"

    # Heal: restart AI proxy if down
    if t1["ai_proxy_8080"] == "OFFLINE":
        result = subprocess.run(
            ["launchctl", "load", "/Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist"],
            capture_output=True, text=True
        )
        t1["ai_proxy_8080_heal"] = "HEAL_ATTEMPTED"
        actions.append({"tier": 1, "action": "HEAL_AI_PROXY", "result": result.returncode})
    report["tiers"]["t1_services"] = t1

    # ── T2: RPC Mesh Probe ─────────────────────────────────────────────────────
    rpc_candidates = {
        "macbook_air_ts":  "100.93.158.96",
        "linux_head_ts":   "100.101.39.98",
        "pixel_10_ts":     "100.73.38.87",
        "macbook_pro_ts":  "100.103.212.21",
        "linux_head_lan":  "192.168.8.224",
    }
    t2 = {}
    active_rpc_ips = []
    for name, ip in rpc_candidates.items():
        live = probe_tcp(ip, 50052, 1.0)
        t2[name] = "ACTIVE" if live else "OFFLINE"
        if live:
            active_rpc_ips.append(ip)
    report["tiers"]["t2_rpc_mesh"] = t2
    report["active_rpc_nodes"] = active_rpc_ips

    # ── T3: AI Model Health & Auto-Restart ────────────────────────────────────
    t3 = {}
    for port, cfg in MANAGED_MODELS.items():
        name = cfg["name"]
        if not model_is_running(port):
            # Auto-restart if model file exists
            result = launch_model(port, cfg, active_rpc_ips)
            t3[name] = f"RESTARTED:{result}"
            actions.append({"tier": 3, "action": f"RESTART_{name}", "port": port, "result": result})
        elif model_is_ready(port):
            t3[name] = "READY"
        else:
            t3[name] = "LOADING"
    
    # Proxy model status
    code, body = probe_http("http://127.0.0.1:8080/v1/proxy/status", 2.0)
    t3["proxy_status"] = "ONLINE" if code == 200 else "OFFLINE"
    report["tiers"]["t3_ai_models"] = t3

    # ── T4: Git & Storage Health ───────────────────────────────────────────────
    t4 = {}
    lock_file = REPO / ".git/index.lock"
    if lock_file.exists():
        lock_file.unlink()
        t4["git_lock"] = "STALE_LOCK_REMOVED"
        actions.append({"tier": 4, "action": "REMOVE_GIT_LOCK"})
    else:
        t4["git_lock"] = "CLEAN"
    
    t4["obsidian_vault"] = "OK" if (REPO / "obsidian_vault").is_dir() else "MISSING"
    t4["lora_datasets_dir"] = "OK" if LORA.is_dir() else "MISSING"
    
    stat = os.statvfs("/Users/aaron")
    free_gb = stat.f_bavail * stat.f_frsize / 1024**3
    t4["disk_free_gb"] = round(free_gb, 1)
    t4["disk_status"] = "OK" if free_gb >= 5.0 else "CRITICAL_LOW"
    
    if free_gb < 5.0:
        # Self-heal: purge pycache and old logs
        subprocess.run(
            "find /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo -name '__pycache__' -type d "
            "-exec rm -rf {} + 2>/dev/null; "
            "find /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs -name '*.log' -mtime +7 -delete 2>/dev/null || true",
            shell=True
        )
        actions.append({"tier": 4, "action": "DISK_PURGE_CACHE"})
    report["tiers"]["t4_storage"] = t4

    # ── T5: Skills Guardian ────────────────────────────────────────────────────
    t5 = {}
    skills_cfg_dir = Path("/Users/aaron/.gemini/config/skills")
    t5["skills_config_dir"] = "OK" if skills_cfg_dir.is_dir() else "MISSING"
    
    key_skills = ["nomad-autonomous-mesh-governor", "swarm", "mesh-universal-ssh"]
    for skill in key_skills:
        t5[f"skill_{skill.replace('-','_')}"] = "OK" if (skills_cfg_dir / skill).is_dir() else "MISSING"
    report["tiers"]["t5_skills_guardian"] = t5

    # ── Summary & ROI ─────────────────────────────────────────────────────────
    online = sum(1 for v in t1.values() if v == "ONLINE")
    rpc_up = len(active_rpc_ips)
    models_ready = sum(1 for v in t3.values() if v in ("READY", "LOADING", "ONLINE"))
    
    roi = round(
        (online / len(service_ports) * 40) +
        (min(rpc_up, 3) / 3 * 30) +
        (models_ready / len(MANAGED_MODELS) * 30),
        2
    )
    
    overall = "HEALTHY" if roi >= 75 else ("DEGRADED" if roi >= 45 else "CRITICAL")
    
    report["summary"] = {
        "services_online":     f"{online}/{len(service_ports)}",
        "rpc_nodes_active":    f"{rpc_up}",
        "models_live":         f"{models_ready}/{len(MANAGED_MODELS)}",
        "disk_free_gb":        round(free_gb, 1),
        "roi_score":           roi,
        "overall_status":      overall,
        "active_rpc_for_sharding": active_rpc_ips,
        "healing_actions":     len(actions),
    }
    report["actions_taken"] = actions

    # ── T6: LoRA Serialization ─────────────────────────────────────────────────
    lora_entry = {
        "timestamp": ts,
        "governor_cycle": "autonomous",
        "instruction": "Nomad Governor: run autonomous 6-tier mesh health cycle",
        "observation": json.dumps(report["summary"]),
        "actions_taken": [a.get("action", str(a)) for a in actions] or ["STATUS_CHECK_OK"],
        "completion": f"ROI={roi} status={overall} rpc_nodes={active_rpc_ips}",
    }
    with open(LORA_LOG, "a") as f:
        f.write(json.dumps(lora_entry) + "\n")

    # Write status JSON
    STATUS_FILE.write_text(json.dumps(report, indent=2))
    return report


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nomad Courier Self-Healer")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously every 60s")
    parser.add_argument("--interval", type=int, default=60, help="Daemon interval seconds")
    args = parser.parse_args()

    if args.once or not args.daemon:
        report = run_cycle()
        s = report["summary"]
        print(f"✅ Nomad Governor Cycle Complete")
        print(f"   Services:  {s['services_online']}")
        print(f"   RPC Nodes: {s['rpc_nodes_active']} active ({', '.join(s['active_rpc_for_sharding']) or 'none'})")
        print(f"   Models:    {s['models_live']}")
        print(f"   Disk:      {s['disk_free_gb']} GB free")
        print(f"   ROI Score: {s['roi_score']}/100")
        print(f"   Status:    {s['overall_status']}")
        if report["actions_taken"]:
            print(f"   Actions:   {[a['action'] for a in report['actions_taken']]}")
        return

    if args.daemon:
        print(f"🚀 Nomad Governor daemon starting (interval={args.interval}s)")
        while True:
            try:
                report = run_cycle()
                s = report["summary"]
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {s['overall_status']} ROI={s['roi_score']} Services={s['services_online']} RPC={s['rpc_nodes_active']} Models={s['models_live']}")
            except Exception as e:
                print(f"[ERROR] Cycle failed: {e}")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
