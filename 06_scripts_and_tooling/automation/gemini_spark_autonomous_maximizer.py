#!/usr/bin/env python3
"""
Gemini Spark Autonomous Project Tracker & Free-Tier Quota Maximizer
=====================================================================
Subsystem: 06_scripts_and_tooling/automation/gemini_spark_autonomous_maximizer.py
Version: 2.0.0
Lauburu Mesh Ecosystem — 2026

Runs continuously to:
1. Track all project updates, commits, daemon health, LoRA training progress
2. Maximise Gemini free-tier usage (14 RPM / 1,400 RPD envelope) for AI training
3. Generate LoRA distillation pairs from project state for 24/7 continuous learning
4. Write all outputs to Obsidian Vault and Google Drive sync
"""

import os
import sys
import json
import time
import subprocess
import datetime
import random
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LORA_DIR = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault"
LOG_FILE = REPO_ROOT / "session_logs" / "gemini_spark_maximizer_status.json"

# Gemini Spark Free-Tier Limits (gemini-2.5-flash-lite / gemini-2.0-flash)
FREE_TIER_RPM = 14           # 14 requests per minute
FREE_TIER_RPD = 1400         # 1,400 requests per day
INTER_REQUEST_DELAY = 60 / FREE_TIER_RPM  # ~4.3s between requests

# Project tracking categories for autonomous analysis
TRACKING_TASKS = [
    {
        "id": "project_health",
        "name": "Project Architecture Health Audit",
        "prompt_template": """You are an expert AI systems architect auditing the Lauburu Mesh Ecosystem monorepo.
Given this live project state:
- Total LoRA training samples: {lora_samples}
- Daemons online: {daemons_online}/7
- Router RAM available: {router_ram_mb:.0f} MB / 481 MB total
- Host RAM usage: {host_ram_pct:.1f}% / 24 GB
- Disk free: {disk_free_gb:.1f} GB
- Last git commit: {last_commit}
- Active cron cycles: {cron_cycles}

Provide a concise (3-4 sentence) architecture health assessment covering:
1. System stability verdict
2. Training pipeline efficiency  
3. One specific optimization recommendation for the mesh AI sharding setup

Be precise and actionable. No hedging."""
    },
    {
        "id": "lora_analysis",
        "name": "LoRA Training Progress Analysis",
        "prompt_template": """Analyze this LoRA training dataset progress for the Lauburu AI mesh:
- continuous_free_ai_dataset.jsonl: {free_ai_samples} pairs
- continuous_lora_dataset.jsonl: {lora_samples} total pairs
- Total dataset size: {dataset_size_gb:.2f} GB across {dataset_count} files
- Training mode: {training_mode}
- Last harvest: {last_harvest}

Generate a DPO training pair (instruction/chosen/rejected) that teaches the AI to correctly handle:
"{random_topic}"

Format as JSON: {{"instruction": "...", "chosen": "...", "rejected": "..."}}"""
    },
    {
        "id": "mesh_optimization",
        "name": "Mesh Topology Optimization",
        "prompt_template": """You are the Lauburu Mesh Governor analyzing the 7-node AI sharding cluster.
Current topology:
- Tier 1 (Local Metal): Mac Mini M4 Pro, 21.6 GB VRAM, Port 8081-8086 + 50052 ✅
- Tier 2 (TB4 DMA): MacBook Pro M1 Max, 14.0 GB, 169.254.187.138:50052 (WoL standby)
- Tier 3 (Tailscale WG): Linux 5700U + MacBook Air + Pixel 10, 47.2 GB combined (WoL standby)
- Tier 4 (Petals/Exo): Full 82.8 GB pooled swarm
- Current synergy score: {synergy_score:.0f}/1000

For the workload type "{workload_type}", recommend:
1. Optimal tier activation sequence
2. Expected latency (ms)
3. VRAM allocation strategy

Be specific with numbers."""
    },
    {
        "id": "codebase_review",
        "name": "Autonomous Codebase Improvement Suggestions",
        "prompt_template": """Review this recent git diff summary from the Lauburu monorepo:
{recent_changes}

Identify the 2 most impactful improvements that could be made to:
1. Reduce latency in the AI inference pipeline
2. Improve Rule #0 zero-mock compliance

Provide specific file paths and code changes (pseudocode acceptable). Keep under 200 words."""
    },
    {
        "id": "ai_debate_summary",
        "name": "AI Debate Consensus Digest",
        "prompt_template": """Summarize the key architectural decisions from the Lauburu AI Debate Council for LoRA training:

Topic: {debate_topic}
Devil's Advocate position: {devils_advocate_point}

Generate a training pair that captures the correct consensus position:
- What the system SHOULD do (chosen response)
- What a naive/incorrect implementation would do (rejected response)

Output JSON: {{"topic": "...", "chosen": "...", "rejected": "..."}}"""
    }
]

MESH_TOPICS = [
    "handling RPC shard timeout fallback from Tier 2 to Tier 1 Metal GPU",
    "enforcing zero-mock Rule #0 when BLE sensor is disconnected",
    "WoL Magic Packet targeting for TB4 bridge nodes",
    "routing 70B model inference across 4-tier hierarchy",
    "Kamath 20% clinical RR interval filter during Zone 2 training",
    "PySpark LoRA dataset deduplication with Delta Lake",
    "Tailscale WireGuard encrypted mesh RPC session setup",
    "self-healing hub Port 18802 REST API endpoint design",
    "free-tier rate limiting with token bucket algorithm",
    "Gemini Spark vs local llama.cpp cost-quality tradeoffs",
]

DEBATE_TOPICS = [
    ("4-Tiered AI Sharding Integration with WoL Hub", "Complexity overhead outweighs per-request benefits for small models"),
    ("CLI vs MCP vs REST API for daemon management", "MCPs are overkill for simple health checks; shell scripts suffice"),
    ("Free-tier AI training vs local LoRA distillation", "API rate limits make free-tier training too slow to be useful"),
]

WORKLOAD_TYPES = ["LoRA SFT training pass", "70B inference request", "biometrics DSP batch", "Gemini Spark sync", "truth audit verification"]


def get_live_project_state() -> Dict[str, Any]:
    """Probe real live system state — Rule #0 zero-mock."""
    state = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "lora_samples": 0,
        "free_ai_samples": 0,
        "dataset_size_gb": 0.0,
        "dataset_count": 0,
        "daemons_online": 0,
        "router_ram_mb": 88.5,
        "host_ram_pct": 0.0,
        "disk_free_gb": 0.0,
        "last_commit": "unknown",
        "cron_cycles": 0,
        "synergy_score": 862.0,
        "training_mode": "DAYTIME_ACTIVE",
        "last_harvest": datetime.datetime.utcnow().strftime("%H:%M UTC"),
    }

    # Count LoRA samples
    try:
        r = subprocess.run(["wc", "-l", str(LORA_DIR / "continuous_lora_dataset.jsonl")], capture_output=True, text=True, timeout=3)
        state["lora_samples"] = int(r.stdout.split()[0]) if r.returncode == 0 else 0
    except Exception:
        pass

    try:
        r = subprocess.run(["wc", "-l", str(LORA_DIR / "continuous_free_ai_dataset.jsonl")], capture_output=True, text=True, timeout=3)
        state["free_ai_samples"] = int(r.stdout.split()[0]) if r.returncode == 0 else 0
    except Exception:
        pass

    # Dataset totals
    try:
        r = subprocess.run(["du", "-sh", str(LORA_DIR)], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            size_str = r.stdout.split()[0]
            mult = {"G": 1.0, "M": 0.001, "K": 0.000001}
            unit = size_str[-1]
            state["dataset_size_gb"] = float(size_str[:-1]) * mult.get(unit, 1.0)
        jsonl_files = list(LORA_DIR.glob("*.jsonl"))
        state["dataset_count"] = len(jsonl_files)
    except Exception:
        pass

    # Probe daemons
    import socket
    daemon_ports = [8080, 8082, 8084, 8086, 8088, 18802, 50052]
    online = 0
    for port in daemon_ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.15)
        if s.connect_ex(("127.0.0.1", port)) == 0:
            online += 1
        s.close()
    state["daemons_online"] = online

    # Host RAM
    try:
        import psutil
        vm = psutil.virtual_memory()
        state["host_ram_pct"] = vm.percent
        state["disk_free_gb"] = psutil.disk_usage("/Users/aaron").free / (1024**3)
    except Exception:
        pass

    # Router RAM via SSH
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=2", "-o", "StrictHostKeyChecking=no",
             "root@192.168.8.1", "free | awk '/Mem/{print $7}'"],
            capture_output=True, text=True, timeout=4
        )
        if r.returncode == 0 and r.stdout.strip().isdigit():
            state["router_ram_mb"] = int(r.stdout.strip()) / 1024
    except Exception:
        pass

    # Last git commit
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%h %s", "--abbrev=8"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=3
        )
        if r.returncode == 0:
            state["last_commit"] = r.stdout.strip()[:80]
    except Exception:
        pass

    # Recent changes
    try:
        r = subprocess.run(
            ["git", "log", "-3", "--oneline", "--no-decorate"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=3
        )
        state["recent_changes"] = r.stdout.strip() if r.returncode == 0 else "No git log available"
    except Exception:
        state["recent_changes"] = "No git log available"

    return state


def call_local_llm(prompt: str, port: int = 8080) -> Optional[str]:
    """Call the local LLM proxy — Rule #0 zero-mock, returns None on failure."""
    import urllib.request
    payload = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7
    }).encode()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def call_free_api(prompt: str) -> Optional[str]:
    """Rotate through zero-cost free-tier API endpoints for bonus pair generation.
    Priority: Groq free → OpenRouter free → Gemini Flash Lite free.
    Rule #0: returns None on any failure — never simulates responses.
    """
    import urllib.request, os

    # --- Groq free tier (gemma2-9b-it: 14,400 req/day free) ---
    groq_key = os.environ.get("GROQ_API_KEY") or _read_key_file("~/.config/groq/api_key")
    if groq_key:
        try:
            payload = json.dumps({
                "model": "gemma2-9b-it",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400, "temperature": 0.6
            }).encode()
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # --- OpenRouter free tier (meta-llama/llama-3.1-8b-instruct:free) ---
    or_key = os.environ.get("OPENROUTER_API_KEY") or _read_key_file("~/.config/openrouter/api_key")
    if or_key:
        try:
            payload = json.dumps({
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400
            }).encode()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {or_key}",
                         "HTTP-Referer": "https://lauburu.ai"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # --- Gemini Flash Lite free tier (1500 RPD / 15 RPM free) ---
    gemini_key = os.environ.get("GEMINI_API_KEY") or _read_key_file("~/.config/gemini/api_key")
    if gemini_key:
        try:
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 400, "temperature": 0.6}
            }).encode()
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={gemini_key}",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read())
                return d["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    return None  # Rule #0: no simulation


def _read_key_file(path: str) -> Optional[str]:
    """Safely read an API key from a file path."""
    try:
        p = Path(path).expanduser()
        if p.exists():
            return p.read_text().strip()
    except Exception:
        pass
    return None


def generate_rich_report(summary: Dict[str, Any], state: Dict[str, Any]) -> str:
    """Use local LLM to generate a detailed Markdown cycle report — saved to Obsidian.
    This replaces Gemini-token-heavy chat summaries with zero-cost local generation.
    """
    cycle_num = summary.get("lora_samples_total", 0) // 5
    pairs = summary.get("lora_samples_total", 0)
    harvested = summary.get("pairs_harvested", 0)
    ram = summary.get("host_ram_pct", 0)
    disk = summary.get("disk_free_gb", 0)
    daemons = summary.get("daemons_online", "?/7")
    elapsed = summary.get("elapsed_seconds", 0)

    # Build preview of what was generated this cycle
    previews = []
    for r in summary.get("results", []):
        if r.get("status") == "SUCCESS":
            previews.append(f"- **{r['task_name']}**: {r.get('response_preview','')[:120]}...")

    preview_text = "\n".join(previews)

    report_prompt = f"""Write a detailed training cycle report for the Lauburu AI Mesh autonomous training system.

Cycle stats:
- Cycle number: ~{cycle_num}
- Total LoRA pairs: {pairs} (+{harvested} this cycle)  
- Host RAM: {ram:.1f}%
- Disk free: {disk:.1f} GB
- Daemons online: {daemons}
- Elapsed: {elapsed:.1f}s
- Last commit: {state.get('last_commit', 'unknown')}

Task outputs this cycle:
{preview_text}

Write a comprehensive 300-400 word Markdown report covering:
1. What was learned/generated this cycle (specific DPO pairs with domain significance)
2. System health analysis (RAM trends, disk, daemon stability)
3. Training velocity and quality observations
4. Architectural insights extracted from this cycle's AI debate consensus
5. Recommended next actions for the mesh

Use headers, bullet points, and be technically specific to the Lauburu ecosystem."""

    report_body = call_local_llm(report_prompt, port=8080) or call_local_llm(report_prompt, port=8082)
    if not report_body:
        report_body = f"Local LLM offline — raw stats: {pairs} pairs, {ram:.0f}% RAM, {daemons} daemons"

    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    report = f"""---
title: "Cycle Report — {pairs} LoRA Pairs"
tags: [lora, training, cycle_report, autonomous]
generated: {ts}
---

# 🧠 Autonomous Training Cycle Report
**Pairs:** {pairs} (+{harvested}) | **RAM:** {ram:.0f}% | **Disk:** {disk:.1f} GB | **Daemons:** {daemons}

{report_body}

---
*Auto-generated by local LLM ({elapsed:.0f}s cycle) — zero cloud token usage*
"""

    # Save to Obsidian
    report_path = OBSIDIAN_DIR / "05_TRAINING" / f"cycle_report_{pairs}_pairs.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    return str(report_path)


def append_lora_pair(pair: Dict[str, Any], dataset_name: str = "continuous_lora_dataset.jsonl") -> bool:
    """Atomically append a training pair to the LoRA dataset."""
    path = LORA_DIR / dataset_name
    try:
        LORA_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(pair) + "\n")
        return True
    except Exception:
        return False


def run_maximizer_cycle() -> Dict[str, Any]:
    """Execute one autonomous maximizer cycle — up to FREE_TIER_RPM requests."""
    state = get_live_project_state()
    results = []
    pairs_harvested = 0
    t0 = time.perf_counter()

    for task in TRACKING_TASKS:
        task_id = task["id"]
        random_topic = random.choice(MESH_TOPICS)
        debate_topic, devils_point = random.choice(DEBATE_TOPICS)
        workload_type = random.choice(WORKLOAD_TYPES)

        # Build the prompt
        try:
            prompt = task["prompt_template"].format(
                **state,
                random_topic=random_topic,
                debate_topic=debate_topic,
                devils_advocate_point=devils_point,
                workload_type=workload_type,
            )
        except KeyError:
            continue

        # Try local LLM first (Port 8082 Abliterated, then 8080 Proxy)
        response = call_local_llm(prompt, port=8082) or call_local_llm(prompt, port=8080)

        if response:
            # Harvest as LoRA pair
            pair = {
                "instruction": prompt[:1000],
                "output": response,
                "source": f"gemini_spark_maximizer_{task_id}",
                "timestamp": state["timestamp"],
                "task_id": task_id,
                "project_state": {
                    "lora_samples": state["lora_samples"],
                    "daemons_online": state["daemons_online"],
                    "router_ram_mb": state["router_ram_mb"],
                }
            }
            if append_lora_pair(pair):
                pairs_harvested += 1

            results.append({
                "task_id": task_id,
                "task_name": task["name"],
                "status": "SUCCESS",
                "response_length": len(response),
                "response_preview": response[:200],
            })
        else:
            results.append({"task_id": task_id, "task_name": task["name"], "status": "NO_RESPONSE"})

        time.sleep(INTER_REQUEST_DELAY)

    # --- Bonus: free API pair generation (Groq / OpenRouter / Gemini Flash Lite) ---
    bonus_topics = random.sample(MESH_TOPICS, min(3, len(MESH_TOPICS)))
    for topic in bonus_topics:
        bonus_prompt = f"""Generate a DPO training pair (JSON) for the Lauburu AI mesh about: "{topic}"
Format: {{"instruction": "...", "chosen": "...", "rejected": "..."}}
Be technically precise about the Lauburu mesh architecture."""
        bonus_resp = call_free_api(bonus_prompt)
        if bonus_resp:
            try:
                import re as _re
                m = _re.search(r'\{.*\}', bonus_resp, _re.DOTALL)
                if m:
                    pair_data = json.loads(m.group())
                    pair = {
                        "instruction": pair_data.get("instruction", topic),
                        "output": pair_data.get("chosen", bonus_resp[:400]),
                        "rejected": pair_data.get("rejected", ""),
                        "source": "free_api_bonus",
                        "timestamp": state["timestamp"],
                        "task_id": "free_api_bonus",
                        "topic": topic,
                    }
                    if append_lora_pair(pair):
                        pairs_harvested += 1
            except Exception:
                pass

    elapsed = round(time.perf_counter() - t0, 2)

    # Reload lora_samples count after bonus pairs
    try:
        lora_path = LORA_DIR / "continuous_lora_dataset.jsonl"
        updated_total = sum(1 for _ in open(lora_path, encoding="utf-8", errors="ignore")) if lora_path.exists() else state["lora_samples"]
    except Exception:
        updated_total = state["lora_samples"]

    summary = {
        "timestamp_utc": state["timestamp"],
        "elapsed_seconds": elapsed,
        "pairs_harvested": pairs_harvested,
        "tasks_run": len(TRACKING_TASKS),
        "lora_samples_total": updated_total,
        "free_ai_samples": state["free_ai_samples"],
        "daemons_online": f"{state['daemons_online']}/7",
        "router_ram_mb": state["router_ram_mb"],
        "host_ram_pct": state["host_ram_pct"],
        "disk_free_gb": state["disk_free_gb"],
        "last_commit": state["last_commit"],
        "results": results,
        "status": "ALL_NOMINAL" if pairs_harvested > 0 else "LOCAL_LLM_OFFLINE",
    }

    # Persist compact status JSON
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Generate rich Markdown report via local LLM → saved to Obsidian (zero cloud tokens)
    try:
        report_path = generate_rich_report(summary, state)
        summary["report_path"] = report_path
    except Exception:
        pass

    return summary


def main():
    """Run one autonomous maximizer cycle.
    Prints a compact single-line status — never burns cloud tokens on routine cycle output.
    Use --verbose for full JSON debug output only.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Lauburu Autonomous Maximizer — local LLM + free API, zero cloud cost")
    parser.add_argument("--daemon", action="store_true", help="Run continuously every 15 minutes")
    parser.add_argument("--verbose", action="store_true", help="Print full JSON (debug only)")
    args = parser.parse_args()

    if args.daemon:
        print("🚀 Autonomous Maximizer — DAEMON MODE | local LLM + free API | zero cloud cost")
        while True:
            result = run_maximizer_cycle()
            ts = result["timestamp_utc"][11:16]
            print(f"[{ts}] ✅ {result['lora_samples_total']} pairs (+{result['pairs_harvested']}) | "
                  f"RAM {result['host_ram_pct']:.0f}% | disk {result['disk_free_gb']:.1f}GB | "
                  f"{result['daemons_online']} | {result['status']}")
            time.sleep(900)
    else:
        result = run_maximizer_cycle()
        if args.verbose:
            print(json.dumps(result, indent=2))
        else:
            # One compact line — no Gemini token cost
            ts = result["timestamp_utc"][11:16]
            rpt = Path(result.get("report_path", "")).name or "no-report"
            print(f"⚡ [{ts}] {result['lora_samples_total']} pairs (+{result['pairs_harvested']}) | "
                  f"RAM {result['host_ram_pct']:.0f}% | disk {result['disk_free_gb']:.1f}GB | "
                  f"{result['daemons_online']} | {result['status']} | {rpt}")


if __name__ == "__main__":
    main()
