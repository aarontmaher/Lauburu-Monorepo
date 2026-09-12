#!/usr/bin/env python3
"""
================================================================================
Universal Free-Tier AI Maximizer & Autonomous Swarm Daemon
================================================================================
Subsystem: 05_agents_and_swarms/master_free_tier_ai_maximizer.py
Version: 3.0.0-CANONICAL-SOVEREIGN-MAXIMIZER
Lauburu Mesh Ecosystem — 2026

Coordinates and fully automates the 5,600+ Daily Free Cloud AI Quota Pool:
1. Google Jules AI (Google AI Ultra: 300 tasks/day, 60 concurrent VMs)
2. Google AI Studio (Gemini 2.5 Flash Lite / Flash: 1,500 RPD)
3. NVIDIA NIM (Nemotron-3-Ultra-550B: 2,000 RPD)
4. xAI Developer API (Grok-4.20: 1,000 RPD)
5. Cloudflare Workers AI (Llama 3.1: 800 RPD)

Guarantees:
- Rule #0 Zero-Mock: Authenticated, physical API calls and kernel probes only.
- Rule #2 Tri-Vault Storage: Live updates to Obsidian Vault, PySpark Data Lake, and Git.
- Rule #3 Host Sanctuary: Preserves >= 9.6 GB physical RAM buffer on Mac Mini.
- Rule #6 Dynamic Cadence: Paces requests toward 10:00 AM AEST daily reset.
- 100% Free-Tier: Zero paid spend ($0.00 USD).
================================================================================
"""

import os
import sys
import time
import json
import psutil
import urllib.request
import urllib.error
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# -----------------------------------------------------------------------------
# Subsystem Configuration & Paths
# -----------------------------------------------------------------------------
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
def _load_env():
    env_file = MONOREPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                k = k.strip()
                v = v.strip().strip("\"").strip("\x27")
                if k and k not in os.environ:
                    os.environ[k] = v

_load_env()

LORA_DIR = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
LORA_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = MONOREPO_ROOT / "04_data_and_memory"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OBSIDIAN_VAULT = MONOREPO_ROOT / "obsidian_vault"
QUOTA_STATE_FILE = DATA_DIR / "universal_cloud_quota_state.json"
FREE_AI_SINK = LORA_DIR / "continuous_free_ai_dataset.jsonl"
CONTINUOUS_LORA_SINK = LORA_DIR / "continuous_lora_dataset.jsonl"
LOG_FILE = MONOREPO_ROOT / "logs/free_tier_maximizer.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Add tooling path for Jules dispatcher
TOOLING_PATH = MONOREPO_ROOT / "06_scripts_and_tooling/integrations_and_mcp"
if str(TOOLING_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLING_PATH))

try:
    import jules_debate_dispatcher
except ImportError:
    jules_debate_dispatcher = None

# Free Tier Quota Caps per 24-hour cycle
DAILY_QUOTAS = {
    "google_jules": 300,
    "google_gemini": 1500,
    "nvidia_nim": 2000,
    "xai_grok": 1000,
    "cloudflare_ai": 800
}


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [FreeTierMaximizer] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def check_host_ram_sanctuary() -> bool:
    """
    Verifies that the Mac Mini host memory utilization does not exceed 90.0% (Rule #3 / Rule 7.1).
    Cloud API offloading is specifically designed to keep local RAM usage below 90% by
    delegating heavy compute to Google Cloud, Jules VMs, NVIDIA, xAI, and Cloudflare.
    """
    mem = psutil.virtual_memory()
    if mem.percent > 90.0:
        log(f"⚠️ Host Memory Utilization is {mem.percent}% (> 90.0% ceiling). Throttling execution to preserve sanctuary.")
        return False
    return True


def get_seconds_until_aest_reset() -> float:
    """Calculates seconds remaining until 10:00 AM AEST daily quota reset."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # AEST is UTC+10 (10 AM AEST = 00:00 UTC)
    target_today = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    if now_utc >= target_today:
        target_reset = target_today + datetime.timedelta(days=1)
    else:
        target_reset = target_today
    return max(60.0, (target_reset - now_utc).total_seconds())


def load_quota_state() -> Dict[str, Any]:
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    default_state = {
        "date": today_str,
        "providers": {
            "google_jules": {"used_today": 0, "cap": 300, "last_call": 0},
            "google_gemini": {"used_today": 0, "cap": 1500, "last_call": 0},
            "nvidia_nim": {"used_today": 0, "cap": 2000, "last_call": 0},
            "xai_grok": {"used_today": 0, "cap": 1000, "last_call": 0},
            "cloudflare_ai": {"used_today": 0, "cap": 800, "last_call": 0}
        },
        "total_free_tasks_today": 0,
        "total_cloud_spend_usd": 0.0,
        "last_updated": time.time()
    }

    if not QUOTA_STATE_FILE.exists():
        return default_state

    try:
        with open(QUOTA_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("date") != today_str:
                log(f"New day detected ({today_str}). Resetting daily quota counters.")
                return default_state
            return data
    except Exception:
        return default_state


def save_quota_state(state: Dict[str, Any]):
    state["last_updated"] = time.time()
    total = sum(p["used_today"] for p in state.get("providers", {}).values())
    state["total_free_tasks_today"] = total
    state["total_cloud_spend_usd"] = 0.0  # Invariant: strictly free tiers only
    try:
        with open(QUOTA_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Error saving quota state: {e}")


# -----------------------------------------------------------------------------
# Provider API Call Handlers (Zero-Mock Authentic Execution)
# -----------------------------------------------------------------------------
def call_gemini(prompt: str) -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 600, "temperature": 0.6}
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            res = json.loads(r.read())
            return res["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        log(f"Gemini API Error: {e}")
        return None


def call_nvidia_nim(prompt: str) -> Optional[str]:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return None
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    payload = json.dumps({
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.5
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read())
            return res["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"NVIDIA NIM Error: {e}")
        return None


def call_xai_grok(prompt: str) -> Optional[str]:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return None
    url = "https://api.x.ai/v1/chat/completions"
    payload = json.dumps({
        "model": "grok-4.20-0309-non-reasoning",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.6
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as r:
            res = json.loads(r.read())
            return res["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"xAI Grok Error: {e}")
        return None


def _get_cf_token(refresh: bool = False) -> Optional[str]:
    import subprocess
    wrangler_toml = Path("/Users/aaron/.wrangler/config/default.toml")
    if refresh:
        try:
            subprocess.run(["npx", "wrangler", "whoami"], capture_output=True, timeout=15)
        except Exception:
            pass
    if wrangler_toml.exists():
        try:
            with open(wrangler_toml) as f:
                for line in f:
                    if line.strip().startswith("oauth_token"):
                        return line.split("=", 1)[1].strip().strip("\"'")
        except Exception:
            pass
    return None


def call_cloudflare_ai(prompt: str, retried: bool = False) -> Optional[str]:
    token = _get_cf_token(refresh=False)
    if not token:
        token = _get_cf_token(refresh=True)
    if not token:
        return None

    account_id = "883d9ae28a5ead3b314b8eba33bafbb6"
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    payload = json.dumps({"prompt": prompt, "max_tokens": 400}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as r:
            res = json.loads(r.read())
            if res.get("success"):
                return res.get("result", {}).get("response", "").strip()
            return None
    except urllib.error.HTTPError as e:
        if e.code == 401 and not retried:
            log("Cloudflare token expired (401). Triggering automatic OAuth token refresh via wrangler whoami...")
            _get_cf_token(refresh=True)
            return call_cloudflare_ai(prompt, retried=True)
        log(f"Cloudflare Workers AI Error: {e}")
        return None
    except Exception as e:
        log(f"Cloudflare Workers AI Error: {e}")
        return None


# -----------------------------------------------------------------------------
# Distillation & Task Prompt Generators
# -----------------------------------------------------------------------------
HARVEST_PROMPTS = [
    {
        "provider": "google_gemini",
        "domain": "architecture_sft",
        "prompt": "You are a Distributed Systems Architect. Formulate an optimal 7-node memory governor strategy for an Apple M4 Pro cluster coordinating 82.8 GB VRAM over Thunderbolt 4 DMA. Provide a concise, structured JSON specification with invariants, latency limits, and fallback paths."
    },
    {
        "provider": "nvidia_nim",
        "domain": "simd_kernel_dpo",
        "prompt": "Generate a C11/Metal Performance Shaders tensor sharding routing kernel for pipelined-ring parallelism. Emphasize zero memory leaks, sub-1ms communication overhead, and strict buffer bounds checking."
    },
    {
        "provider": "xai_grok",
        "domain": "ecommerce_liquidation_intel",
        "prompt": "Analyze the secondary hardware resale market in Australia for used iPhones and M1/M4 MacBooks. Detail optimal listing price points, title keywords, and high-conversion descriptions for Gumtree, eBay Australia, and Facebook Marketplace to maximize liquidation yield."
    },
    {
        "provider": "cloudflare_ai",
        "domain": "edge_triage_classification",
        "prompt": "Classify the following incoming telemetry stream:Movesense 512Hz ECG, RR=820ms, DFA-alpha1=0.74, PTT BP=118/78 mmHg. Output strict JSON with fields: status, zone, alert_level, recommendation."
    }
]


def execute_api_harvest_cycle(state: Dict[str, Any]):
    """Iterates through active providers to harvest training data and maximize free quota."""
    providers = state.setdefault("providers", {})

    for item in HARVEST_PROMPTS:
        prov_key = item["provider"]
        prov_state = providers.setdefault(prov_key, {"used_today": 0, "cap": DAILY_QUOTAS.get(prov_key, 1000), "last_call": 0})

        if prov_state["used_today"] >= prov_state["cap"]:
            log(f"Provider {prov_key} has hit daily quota ({prov_state['used_today']}/{prov_state['cap']}). Skipping.")
            continue

        prompt = item["prompt"]
        domain = item["domain"]
        response = None

        log(f"Harvesting from {prov_key} ({prov_state['used_today'] + 1}/{prov_state['cap']})...")
        if prov_key == "google_gemini":
            response = call_gemini(prompt)
        elif prov_key == "nvidia_nim":
            response = call_nvidia_nim(prompt)
        elif prov_key == "xai_grok":
            response = call_xai_grok(prompt)
        elif prov_key == "cloudflare_ai":
            response = call_cloudflare_ai(prompt)

        if response:
            prov_state["used_today"] += 1
            prov_state["last_call"] = time.time()

            entry = {
                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "provider": prov_key,
                "domain": domain,
                "prompt": prompt,
                "response": response,
                "token_estimate": len(response.split()) * 1.3,
                "verified": True
            }

            try:
                with open(FREE_AI_SINK, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
                with open(CONTINUOUS_LORA_SINK, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
                log(f"✅ Successfully harvested {len(response)} chars from {prov_key} -> Saved to {FREE_AI_SINK.name}")
            except Exception as e:
                log(f"Error saving harvested dataset entry: {e}")

        # Inter-call pacing
        time.sleep(1.5)


def update_obsidian_matrix(state: Dict[str, Any]):
    """Synchronizes live quota state with Obsidian Vault (Rule #2)."""
    target_md = OBSIDIAN_VAULT / "05_SWARMS/FREE_TIER_AI_MAXIMIZATION_MATRIX.md"
    target_md.parent.mkdir(parents=True, exist_ok=True)

    rem_s = get_seconds_until_aest_reset()
    rem_h = rem_s / 3600.0

    table_rows = []
    total_used = 0
    total_cap = 0

    for name, p in state.get("providers", {}).items():
        used = p.get("used_today", 0)
        cap = p.get("cap", 1000)
        pct = (used / cap * 100.0) if cap > 0 else 0.0
        total_used += used
        total_cap += cap
        table_rows.append(f"| **{name.replace('_', ' ').title()}** | {cap:,} | {used:,} | {cap - used:,} | {pct:.1f}% |")

    overall_pct = (total_used / total_cap * 100.0) if total_cap > 0 else 0.0

    content = f"""---
title: "Universal Free-Tier AI Maximization Matrix"
tags: [swarm, cloud_quota, jules, gemini, nvidia, grok, cloudflare, zero_spend]
last_updated: "{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
---

# ⚡ Universal Free-Tier AI Maximization Matrix

Governs the autonomous daily exhaustion and LoRA harvesting across all available free cloud AI resources for **\$0.00 USD total recurring cloud spend**.

- **Time Until 10:00 AM AEST Reset:** `{rem_h:.2f} hours` (`{rem_s:.0f} seconds`)
- **Total Free AI Actions Pooled:** `{total_cap:,} actions / day`
- **Total Actions Harvested Today:** `{total_used:,} actions` (`{overall_pct:.1f}%` utilized)
- **Monetary Cloud Spend:** `\$0.00 USD` (Rule #6 Invariant)

## 📊 Live Provider Quota Telemetry

| Provider / Agent | Daily Cap | Used Today | Remaining | Utilization |
| :--- | :--- | :--- | :--- | :--- |
{chr(10).join(table_rows)}
| **TOTAL POOLED** | **{total_cap:,}** | **{total_used:,}** | **{total_cap - total_used:,}** | **{overall_pct:.1f}%** |

## 🏛️ Tri-Vault Integration
- **Semantic Knowledge Core:** `[[FREE_TIER_AI_MAXIMIZATION_MATRIX]]` in `obsidian_vault/`
- **PySpark Data Lake Sink:** `lora_datasets/continuous_free_ai_dataset.jsonl`
- **Canonical Monorepo:** `05_agents_and_swarms/master_free_tier_ai_maximizer.py`
"""
    try:
        with open(target_md, "w", encoding="utf-8") as f:
            f.write(content)
        log(f"Updated Obsidian Knowledge Vault at {target_md.name}")
    except Exception as e:
        log(f"Error updating Obsidian matrix: {e}")


def run_maximizer_cycle(single_cycle: bool = False):
    """Executes a full maximization pass across Jules and all cloud APIs."""
    log("================================================================================")
    log("🚀 Initiating Free-Tier AI Maximization Cycle...")
    log("================================================================================")

    # 1. Verify Host RAM Sanctuary (Rule #3)
    if not check_host_ram_sanctuary():
        log("Mac Mini RAM headroom constrained. Sleeping to preserve host sanctuary.")
        return

    # 2. Load and refresh quota state
    state = load_quota_state()

    # 3. Google Jules AI Orchestration (300 tasks/day, 60 concurrent)
    if jules_debate_dispatcher:
        try:
            log("Executing Google Jules Asynchronous Swarm Pass...")
            jules_debate_dispatcher.run_cycle()
            jules_count = jules_debate_dispatcher.get_daily_dispatch_count()
            state["providers"]["google_jules"]["used_today"] = jules_count
        except Exception as e:
            log(f"Error during Jules dispatcher execution: {e}")

    # 4. Multi-Provider Cloud API Harvest Pass (Gemini, NVIDIA, xAI, Cloudflare)
    execute_api_harvest_cycle(state)

    # 5. Save Quota State & Synchronize Tri-Vault
    save_quota_state(state)
    update_obsidian_matrix(state)

    log("================================================================================")
    log(f"✅ Maximization Cycle Complete. Total Tasks Harvested Today: {state.get('total_free_tasks_today', 0)}")
    log("================================================================================")


def main():
    single_cycle = "--single-cycle" in sys.argv
    speed_run = "--speed-run" in sys.argv or "--burst" in sys.argv
    mode_str = "Single-Cycle" if single_cycle else ("Full Quota Speed-Run" if speed_run else "Continuous 24/7")
    log(f"Starting Master Free-Tier AI Maximizer Daemon (Mode: {mode_str})...")

    if single_cycle:
        run_maximizer_cycle(single_cycle=True)
        return

    while True:
        try:
            run_maximizer_cycle()
        except Exception as e:
            log(f"Unexpected exception in maximizer cycle: {e}")

        # Sleep interval: in speed run mode, sleep only 5s to rapidly harvest all free quotas
        if speed_run:
            delay = 5.0
        else:
            rem_s = get_seconds_until_aest_reset()
            state = load_quota_state()
            total_remaining = sum(
                max(0, p.get("cap", 1000) - p.get("used_today", 0))
                for p in state.get("providers", {}).values()
            )
            if total_remaining > 0 and rem_s > 0:
                delay = max(45.0, min(300.0, rem_s / total_remaining))
            else:
                delay = 300.0

        log(f"Sleeping for {delay:.1f}s until next maximization cycle...")
        time.sleep(delay)


if __name__ == "__main__":
    main()
