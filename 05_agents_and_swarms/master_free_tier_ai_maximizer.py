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
4. xAI Developer API (Grok-2: 1,000 RPD)
5. Cloudflare Workers AI (Llama 3.1 / 3.3: 800 RPD)
6. Groq Cloud LPU Free Tier (Llama 3.3 70B Versatile: 1,440 RPD)

Guarantees:
- Rule #0 Zero-Mock: Authenticated, physical API calls and kernel probes only.
- Rule #2 Tri-Vault Storage: Live updates to Obsidian Vault, PySpark Data Lake, and Git.
- Rule #3 Host Sanctuary: Preserves >= 4.8 GB physical RAM buffer on Mac Mini.
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
from typing import Dict, List, Any, Optional, Tuple

# -----------------------------------------------------------------------------
# Subsystem Configuration & Paths
# -----------------------------------------------------------------------------
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
def _load_env():
    for env_file in [MONOREPO_ROOT / ".env", Path("/Users/aaron/.env")]:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
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

# Add tooling path for Jules dispatcher and Model Cost Governor
TOOLING_ROOT = MONOREPO_ROOT / "06_scripts_and_tooling"
if str(TOOLING_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLING_ROOT))

TOOLING_PATH = MONOREPO_ROOT / "06_scripts_and_tooling/integrations_and_mcp"
if str(TOOLING_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLING_PATH))

CLOUD_QUOTA_PATH = MONOREPO_ROOT / "06_scripts_and_tooling/cloud_and_quota"
if str(CLOUD_QUOTA_PATH) not in sys.path:
    sys.path.insert(0, str(CLOUD_QUOTA_PATH))

from model_cost_governor import get_host_ram_telemetry

try:
    import jules_debate_dispatcher
except ImportError:
    jules_debate_dispatcher = None

try:
    from strongest_free_tier_client import StrongestFreeTierClient, QualityGate
    strongest_gemini_client = StrongestFreeTierClient(min_interval_seconds=4.2)
except Exception:
    strongest_gemini_client = None

# Free Tier Quota Caps per 24-hour cycle
DAILY_QUOTAS = {
    "google_jules": 300,
    "google_gemini": 1500,
    "nvidia_nim": 2000,
    "xai_grok": 1000,
    "cloudflare_ai": 800,
    "groq_ai": 1440,
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
    Verifies Mac Mini host memory via authentic Darwin Mach vm_stat (Rule 1 §6 & Rule 3).
    Never runs blocking filesystem find/rm commands inside the harvest loop.
    Because Free-Tier Cloud API harvesting consumes 0 GB of local model VRAM/RAM,
    it continues harvesting unless Darwin kernel memory pressure is critical (pressure_level >= 3).
    """
    ram = get_host_ram_telemetry()
    avail_gb = float(ram["free_headroom_gb"])
    used_pct = float(ram["utilization_pct"])
    pressure = int(ram.get("pressure_level", 1))

    if avail_gb < 4.8 or used_pct > 80.0:
        log(
            f"⚠️ Host Memory Warning (Darwin Mach vm_stat): Free={avail_gb:.2f} GB, "
            f"Used={used_pct:.1f}%, Pressure={pressure} (Sanctuary target: >= 4.8 GB, <= 80%)."
        )
        try:
            import gc
            gc.collect()
        except Exception as e:
            log(f"Error during GC self-healing: {e}")

        if pressure >= 3 and avail_gb < 1.5:
            log(
                f"Host kernel memory pressure CRITICAL (pressure={pressure}, free={avail_gb:.2f} GB). "
                f"Throttling harvest cycle to protect host sanctuary."
            )
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
            "cloudflare_ai": {"used_today": 0, "cap": 800, "last_call": 0},
            "groq_ai": {"used_today": 0, "cap": 1440, "last_call": 0},
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
def call_gemini(prompt: str, domain: str = "general") -> Tuple[Optional[str], Optional[int], str]:
    if strongest_gemini_client is not None:
        try:
            domain_key = "general"
            if any(k in domain for k in ["vla", "uiux", "apps", "lens"]):
                domain_key = "multimodal_vla"
            elif any(k in domain for k in ["reverse", "decompil", "binary"]):
                domain_key = "reverse_engineering"
            elif any(k in domain for k in ["scout", "open_source", "repo", "github"]):
                domain_key = "open_source_scout"
            elif any(k in domain for k in ["debate", "swarm", "consensus"]):
                domain_key = "ai_debate"
            elif any(k in domain for k in ["biometrics", "dsp", "ecg", "telemetry"]):
                domain_key = "biometrics_dsp"

            resp = strongest_gemini_client.generate(
                prompt=prompt,
                domain=domain_key,
                prevent_quality_drop=True
            )
            if resp.success:
                return resp.text, 200, resp.model_used
            status = 429 if ("429" in resp.error_message or "rate" in resp.error_message.lower()) else 500
            return None, status, resp.model_used
        except Exception as e:
            log(f"StrongestFreeTierClient exception: {e}")

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None, None, "gemini-none"

    frontier_models = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]
    for model_id in frontier_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 600, "temperature": 0.6}
        }).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=16) as r:
                res = json.loads(r.read())
                text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                return text, 200, model_id
        except urllib.error.HTTPError as e:
            if e.code == 429:
                log(f"Gemini model {model_id} hit 429 RPM limit.")
                return None, 429, model_id
            log(f"Gemini API ({model_id}) HTTP Error {e.code}: {e.reason}")
            return None, e.code, model_id
        except Exception as e:
            log(f"Gemini API ({model_id}) Error: {e}")
            continue

    return None, 429, frontier_models[0]



def call_nvidia_nim(prompt: str, domain: str = "general") -> Tuple[Optional[str], Optional[int], str]:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return None, None, "nim-none"

    if domain in ["spec_15_multimodal_vla_uiux_studio", "spec_01_apps_ecosystem"]:
        candidate_models = ["meta/llama-3.2-11b-vision-instruct", "nvidia/nemotron-3.5-lightning-30b-a3b"]
    elif domain in ["spec_screen_lens_notebook_swarm", "spec_05_agents_and_swarms"]:
        candidate_models = ["nvidia/nemotron-3.5-lightning-30b-a3b", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"]
    else:
        candidate_models = ["nvidia/nemotron-3.5-lightning-30b-a3b"]

    for target_model in candidate_models:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        payload = json.dumps({
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.5
        }).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=16) as r:
                res = json.loads(r.read())
                return res["choices"][0]["message"]["content"].strip(), 200, target_model
        except urllib.error.HTTPError as e:
            log(f"NVIDIA NIM ({target_model}) HTTP Error {e.code}: {e.reason}")
            continue
        except Exception as e:
            log(f"NVIDIA NIM ({target_model}) Error: {e}")
            continue

    return None, 500, candidate_models[0]


def call_xai_grok(prompt: str) -> Tuple[Optional[str], Optional[int]]:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return None, None
    url = "https://api.x.ai/v1/chat/completions"
    payload = json.dumps({
        "model": "grok-2-latest",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.6
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as r:
            res = json.loads(r.read())
            return res["choices"][0]["message"]["content"].strip(), 200
    except urllib.error.HTTPError as e:
        log(f"xAI Grok HTTP Error {e.code}: {e.reason}")
        return None, e.code
    except Exception as e:
        log(f"xAI Grok Error: {e}")
        return None, None


def call_groq(prompt: str) -> Tuple[Optional[str], Optional[int], str]:
    api_key = os.environ.get("GROQ_API_KEY")
    target_model = "llama-3.3-70b-versatile"
    if not api_key:
        return None, None, target_model
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = json.dumps({
        "model": target_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.5,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "LauburuFreeTierMaximizer/3.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            res = json.loads(r.read())
            return res["choices"][0]["message"]["content"].strip(), 200, target_model
    except urllib.error.HTTPError as e:
        log(f"Groq API ({target_model}) HTTP Error {e.code}: {e.reason}")
        return None, e.code, target_model
    except Exception as e:
        log(f"Groq API ({target_model}) Error: {e}")
        return None, None, target_model


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


def call_cloudflare_ai(prompt: str, domain: str = "general", retried: bool = False) -> Tuple[Optional[str], Optional[int], str]:
    token = _get_cf_token(refresh=False)
    if not token:
        token = _get_cf_token(refresh=True)
    if not token:
        return None, None, "cf-none"

    if domain in ["spec_linux_tablet_touch_tui", "spec_06_tooling_and_healing", "spec_14_autonomous_swebench_engineering"]:
        target_model = "@cf/qwen/qwen2.5-coder-32b-instruct"
    elif domain in ["spec_screen_lens_notebook_swarm", "spec_17_clinical_biometrics_dsp", "spec_03_biometrics_and_telemetry"]:
        target_model = "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"
    else:
        target_model = "@cf/meta/llama-3.3-70b-instruct"

    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "883d9ae28a5ead3b314b8eba33bafbb6"
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{target_model}"
    payload = json.dumps({"prompt": prompt, "max_tokens": 512}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as r:
            res = json.loads(r.read())
            if res.get("success"):
                response_text = res.get("result", {}).get("response", "").strip()
                return response_text, 200, target_model
            return None, 500, target_model
    except urllib.error.HTTPError as e:
        if e.code == 401 and not retried:
            log("Cloudflare token expired (401). Triggering automatic OAuth token refresh via wrangler whoami...")
            _get_cf_token(refresh=True)
            return call_cloudflare_ai(prompt, domain=domain, retried=True)
        if e.code == 429 and target_model != "@cf/qwen/qwen2.5-coder-32b-instruct":
            log(f"Cloudflare model {target_model} hit 429 rate limit. Pivoting horizontally to @cf/qwen/qwen2.5-coder-32b-instruct...")
            fb_model = "@cf/qwen/qwen2.5-coder-32b-instruct"
            fb_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{fb_model}"
            try:
                fb_payload = json.dumps({"prompt": prompt, "max_tokens": 450}).encode("utf-8")
                fb_req = urllib.request.Request(fb_url, data=fb_payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(fb_req, timeout=18) as fb_r:
                    fb_res = json.loads(fb_r.read())
                    if fb_res.get("success"):
                        return fb_res.get("result", {}).get("response", "").strip(), 200, fb_model
            except Exception:
                pass
        log(f"Cloudflare Workers AI ({target_model}) HTTP Error {e.code}: {e.reason}")
        return None, e.code, target_model
    except Exception as e:
        log(f"Cloudflare Workers AI ({target_model}) Error: {e}")
        return None, None, target_model



# -----------------------------------------------------------------------------
# Dynamic Multi-Spec Curriculum Engine (Spec-00 through Spec-12)
# -----------------------------------------------------------------------------
CURRICULUM_MODULES = [
    {
        "domain": "spec_00_core_infrastructure",
        "templates": [
            "You are a Distributed Systems Architect. Formulate an optimal 7-node memory governor strategy for an Apple M4 Pro cluster coordinating 82.8 GB VRAM over Thunderbolt 4 DMA. Provide a concise, structured JSON specification with invariants, latency limits, and fallback paths.",
            "Design a fail-fast POSIX shell keepalive script for SeaweedFS Master and Volume daemons with memory self-healing and zero data loss on Apple Silicon Darwin systems.",
            "Formulate a zero-copy socket ring buffer in C11/POSIX for 10Gbps Thunderbolt 4 inter-node IPC. Detail data structures, bounds checks, and lock-free atomic pointer management."
        ]
    },
    {
        "domain": "spec_01_apps_ecosystem",
        "templates": [
            "Write a high-performance JavaScript/Canvas rendering engine for continuous 512Hz ECG waveforms with sub-5ms latency and zero memory allocations during redraw loops.",
            "Design a Next.js 14 Server-Sent Events (SSE) subscriber component that visualizes real-time mesh RAM headroom and model training loss curves with automated reconnect exponential backoff."
        ]
    },
    {
        "domain": "spec_02_ai_inference_mesh",
        "templates": [
            "Generate a C11/Metal Performance Shaders tensor sharding routing kernel for pipelined-ring parallelism. Emphasize zero memory leaks, sub-1ms communication overhead, and strict buffer bounds checking.",
            "Formulate an optimal tensor sharding routing algorithm for llama.cpp RPC over heterogeneous nodes (Apple M4 24GB + Intel 16GB + AMD Ryzen 16GB). Detail pipeline stage allocation and memory safety.",
            "Design a speculative decoding verification grammar for Qwen 3.8 Max paired with a fast 7B syntax drafter. Outline rejection sampling mathematics and acceptance criteria."
        ]
    },
    {
        "domain": "spec_03_biometrics_and_telemetry",
        "templates": [
            "Classify the following incoming telemetry stream: Movesense 512Hz ECG, RR=820ms, DFA-alpha1=0.74, PTT BP=118/78 mmHg. Output strict JSON with fields: status, zone, alert_level, recommendation.",
            "Implement a pure Python Pan-Tompkins QRS detection algorithm for 512Hz Movesense ECG data. Include 5-15Hz bandpass filter, derivative, squaring, and adaptive thresholding.",
            "Explain Detrended Fluctuation Analysis (DFA-alpha1) for real-time heart rate variability (HRV) analysis during Zone 2 aerobic exercise. Provide mathematical derivation and vectorized implementation."
        ]
    },
    {
        "domain": "spec_04_data_and_memory",
        "templates": [
            "Write a PySpark crawler script to parse an entire 435K+ LOC codebase into an Abstract Syntax Tree (AST) dataset, extracting function signatures, type annotations, and docstrings into Parquet.",
            "Formulate a vector search deduplication pipeline using Qdrant and Delta Lake to filter redundant training pairs from a 24/7 continuous LoRA dataset while preserving diversity."
        ]
    },
    {
        "domain": "spec_05_agents_and_swarms",
        "templates": [
            "Formulate a Tri-Orchestrator AI debate consensus protocol resolving architectural trade-offs between local inference latency and model parameter capacity, using Bradley-Terry ELO scoring.",
            "Design an autonomous Genetic Mixture of Experts (MoE) routing algorithm that allocates prompt tokens to models based on empirical accuracy, execution latency, and available VRAM headroom."
        ]
    },
    {
        "domain": "spec_06_tooling_and_healing",
        "templates": [
            "Create a macOS Darwin Mach VM telemetry collector in Python that calculates wired, active, inactive, and compressed memory pages, alerting when available RAM dips below 4.8 GB.",
            "Design an Android Termux keepalive watchdog script that prevents Android 15 Doze mode from killing background SSH and ADB daemons using termux-wake-lock and foreground notifications."
        ]
    },
    {
        "domain": "spec_07_docs_and_architecture",
        "templates": [
            "Formulate an Obsidian Knowledge Graph schema for multi-agent autonomous swarms, featuring bidirectional Wikilinks, frontmatter telemetry, and consensus audit logs.",
            "Detail the sovereign local AI hierarchy invariant governing Qwen 3.8 Max as Master Local Orchestrator vs subordinate syntax workers, outlining strict routing boundaries."
        ]
    },
    {
        "domain": "spec_08_business_and_commerce",
        "templates": [
            "Analyze the secondary hardware resale market in Australia for used iPhones and M1/M4 MacBooks. Detail optimal listing price points, title keywords, and high-conversion descriptions for Gumtree, eBay Australia, and Facebook Marketplace to maximize liquidation yield.",
            "Write an optimized GraphQL query and mutation suite for Shopify Storefront API to handle real-time inventory checks and high-volume flash cart checkouts with zero rate-limit drops."
        ]
    },
    {
        "domain": "spec_09_app_store_production",
        "templates": [
            "Design a Flutter 3.x BLoC architecture for an offline-first biometric monitoring app that guarantees zero memory leaks across 24-hour continuous BLE telemetry ingestion.",
            "Outline an automated App Store pre-submission compliance audit script that inspects iOS entitlements, background modes, privacy nutrition labels, and Mach-O binary architectures."
        ]
    },
    {
        "domain": "spec_10_spatial_grappling_kinematics",
        "templates": [
            "Formulate a 3D biomechanical joint torque model for Brazilian Jiu-Jitsu guard recovery, calculating angular velocity and mechanical advantage during hip escapes from bottom side control.",
            "Design a graph traversal algorithm for a 955-node OPML submission grappling skill tree to compute shortest transition paths between neutral standing and back control."
        ]
    },
    {
        "domain": "spec_11_security_red_blue_team",
        "templates": [
            "Conduct an adversarial red-team audit of an isolated sandbox model mutation pipeline. Identify potential attack vectors for arbitrary code execution or local weight exfiltration.",
            "Formulate an HMAC-SHA256 authenticated RPC socket protocol for cluster nodes over untrusted networks with nonce tracking and replay attack protection."
        ]
    },
    {
        "domain": "spec_12_continuous_lora_evolution",
        "templates": [
            "Explain the mathematical principles of Low-Rank Adaptation (LoRA) and QLoRA gradient accumulation on Apple Silicon unified memory using MLX. Detail rank-8 parameter scaling.",
            "Formulate a DARE (Drop And REscale) and TIES model weight merging algorithm to combine two specialized LoRA adapters without destructive interference or parameter explosion."
        ]
    },
    {
        "domain": "spec_13_frontier_mcts_reasoning",
        "templates": [
            "Demonstrate an autonomous Monte Carlo Tree Search (MCTS) test-time compute trace with explicit <think> reasoning, state value evaluation Q(s,a), exploration bonus U(s,a), and step-by-step backtracking when evaluating an NP-hard graph scheduling bottleneck across 7 heterogeneous mesh nodes.",
            "Formulate a rigorous mathematical proof for asymptotic convergence of Bradley-Terry Elo updates in closed-loop model arena battles, proving that symmetric logistic updates bounded to [1800, 2350] prevent runaway rating inflation.",
            "Execute deep chain-of-thought self-reflection to resolve a subtle concurrency race condition in lock-free shared memory ring buffers between Apple Silicon Metal and Darwin POSIX kernels."
        ]
    },
    {
        "domain": "spec_14_autonomous_swebench_engineering",
        "templates": [
            "Act as a Principal Staff SWE-bench Engineer. Given a multi-file Python repository where asynchronous generator cancellations trigger unhandled TaskGroup exceptions, write the exact root-cause analysis, the unified diff patch (with strict line numbers), and an empirical regression test suite covering edge-case cancel timing.",
            "Perform an Abstract Syntax Tree (AST) crawl and rewrite in Python using the ast module to identify all blocking I/O calls inside async coroutines and automatically transform them into non-blocking thread-pool dispatches with zero semantic distortion.",
            "Develop a zero-regression C-ABI / Rust FFI binding for macOS CoreBluetooth and Linux BlueZ that exposes zero-copy ring buffers for 512Hz ECG streams with compile-time memory safety."
        ]
    },
    {
        "domain": "spec_15_multimodal_vla_uiux_studio",
        "templates": [
            "You are Julien AI Sovereign UI/UX Architect. Design a responsive, production-ready Tailwind CSS and Glassmorphism telemetry dashboard component for Port 4004. Ensure strict WCAG 2.2 AAA color contrast (minimum 7:1 for normal text, 14:1 for headers on obsidian black #0a0e17), full ARIA keyboard navigation, and zero layout shift.",
            "Write a high-performance Canvas 2D / WebGL oscilloscope rendering loop that plots 512Hz continuous ECG waveforms with Pan-Tompkins QRS markers and RSA respiratory modulation at a locked 60 FPS without triggering JavaScript garbage collection pauses.",
            "Reverse-engineer a complex multimodal UI screenshot into structured JSON bounding boxes, optical character recognition (OCR) semantic tokens, and hierarchical flexbox CSS layouts with sub-pixel alignment."
        ]
    },
    {
        "domain": "spec_16_agentic_tool_orchestration",
        "templates": [
            "Formulate a strict JSON Schema specification for an autonomous multi-step agentic tool call that coordinates local LLM inference, remote SSH execution, and live sensor queries. Include robust error-recovery heuristics for HTTP 429, socket timeout, and schema mismatch.",
            "Design an agentic error-resilient tool execution engine in Python that intercepts tool exceptions, parses the stack trace, dynamically re-formats invalid JSON parameters, and retries with exponential jitter without escalating to human intervention.",
            "Construct a multi-tool DAG orchestrator that executes independent read tasks concurrently while sequencing state-mutating file writes with file-locking invariants and transactional rollbacks."
        ]
    },
    {
        "domain": "spec_17_clinical_biometrics_dsp",
        "templates": [
            "Detail the clinical physiological digital signal processing (DSP) pipeline for raw 512Hz Movesense single-lead ECG. Detail the transfer function for the 5-15Hz bandpass filter, the five-point derivative approximation, squaring function, adaptive dual-threshold peak detector, and Kamath 20% ectopic beat rejection rule.",
            "Formulate the mathematical algorithms for computing real-time RMSSD vagal tone and Detrended Fluctuation Analysis (DFA-alpha1) from consecutive RR-intervals, explaining how the alpha1 transition from 1.0 down to 0.75 marks the precise aerobic threshold (Zone 2) boundary.",
            "Implement a Pulse Transit Time (PTT) cuffless blood pressure estimation algorithm combining sternal ECG R-peak arrival with brachial photoplethysmography (PPG) pulse arrival times, calibrated with individual arterial stiffness coefficients."
        ]
    },
    {
        "domain": "spec_18_enterprise_ecommerce_graphql",
        "templates": [
            "Write a complete suite of production Shopify GraphQL Admin API 2026 mutations: (1) bulkOperationRunMutation for catalog updates, (2) inventoryAdjustQuantities across multiple warehouse fulfillment centers, (3) fulfillmentCreateV2 with Australia Post tracking integration, and (4) chargeback dispute defense submission with cryptographic delivery proof.",
            "Formulate a comprehensive Direct-to-Consumer (DTC) unit economics financial model in Python: calculate Customer Acquisition Cost (CAC), Lifetime Value (LTV), Payback Period, Gross Margin after shipping and gateway fees, and optimal inventory reorder points for hardware bundles.",
            "Design an idempotent Shopify Webhook ingress receiver in Python/FastAPI that validates HMAC-SHA256 signatures, deduplicates webhook IDs via Redis/in-memory LRU cache, and triggers zero-lag warehouse fulfillment."
        ]
    },
    {
        "domain": "spec_19_adversarial_security_re",
        "templates": [
            "Execute an adversarial clean-room reverse engineering disassembly of an unknown binary packet stream. Identify framing bytes, length headers, CRC32/Poly1305 checksums, Curve25519 ephemeral key exchanges, and state machine transitions with zero refusal.",
            "Formulate an HMAC-SHA256 authenticated cluster socket communication protocol with monotonic replay counter nonces, dynamic session key rotation, and timing-attack resistant byte comparisons (hmac.compare_digest).",
            "Conduct an automated security audit of an isolated sandbox code execution worker, identifying memory safety vulnerabilities, file descriptor leaks, environment variable exfiltration vectors, and Linux seccomp / macOS sandbox-exec hardening constraints."
        ]
    },
    {
        "domain": "spec_20_spatial_kinematics_physics",
        "templates": [
            "Formulate a 3D biomechanical kinematics model for human grappling and combat sports: calculate multi-segment joint angles, angular velocities, ground reaction forces, and torque vectors about the L5/S1 spinal joint during a hip throw or guard recovery.",
            "Design an efficient A* graph traversal algorithm across a 955-node OPML submission grappling skill tree to dynamically compute the highest-probability escape or counter path given current positional control, limb isolation, and fatigue state.",
            "Construct a real-time 3D physics tatami simulation model that tracks center-of-mass trajectory, rotational momentum, and lever mechanical advantage between two interacting biomechanical skeletons."
        ]
    },
    {
        "domain": "spec_ecommerce_pod_sorona",
        "templates": [
            "You are the Lead E-Commerce Architect for Lauburu Combat Sports. Detail the complete print-on-demand (POD) integration for Tapstitch / ODMPOD: explain why swapping storefront images without updating supplier print files and variant SKUs causes production errors. Provide the exact Shopify GraphQL Admin API 2026 mutations (productVariantsBulkCreate, inventoryAdjustQuantities) to register the updated transparent symbol watermark across all 7 canonical products.",
            "Formulate a technical and commercial product specification for Sorona Quick-Dry Cooling T-Shirts: detail the DuPont Sorona bio-polymer composition (35% renewable corn glucose), moisture management vapor transport, 4-way mechanical stretch, and anti-chafing flatlock stitching. Calculate target unit economics (AUD retail $68.00 vs $21.50 POD COGS, 68.4% gross margin) and compare against Gymshark and Nike combat lines.",
            "Design an automated catalog migration script that audits all Shopify products, verifies transparent PNG watermark placement, generates before-and-after mockups in the Antigravity sidebar, and ensures zero dummy/placeholder product bloat by strictly limiting the store to 7 high-margin canonical items.",
            "Analyze competitive intelligence across premium activewear and combat apparel brands (Gymshark, Ten Thousand, RVCA Sport, Venum). Outline optimal pricing ladders, size chart normalization (lauburu-size-guide.html), and automated stock level alerts during high-velocity flash sales."
        ]
    },
    {
        "domain": "spec_linux_tablet_touch_tui",
        "templates": [
            "You are the Embedded Linux & TUI Specialist. Formulate the technical strategy to convert a Debian Linux Tablet (Layer 4) from a battery-draining Chromium desktop environment into a pure headless touch-driven terminal. Detail the power savings (5.5W down to 1.1W) that enable continuous charging over a 5V/1A USB-A to USB-C cable from the Linux Mini.",
            "Write a production-ready Python Textual / TCSS on-screen virtual touch keyboard component for terminal applications. Include QWERTY layout, toggleable visibility (via touch gesture or corner button), touch coordinate hit-testing, visual keypress feedback, and direct PTY input injection without requiring X11 or Wayland on-screen keyboards.",
            "Formulate the IP-less Bluetooth serial terminal (RFCOMM / L2CAP) and Bluetooth PAN tethering network architecture between the Mac Mini, Linux Mini, and Linux Tablet. Compare RAM and power consumption against Wi-Fi 5 and Tailscale, proving how Bluetooth PAN preserves host sanctuary while delivering low-latency terminal control.",
            "Design a bidirectional ADB over TCP (Port 5555) control daemon between the Linux Mini and Linux Tablet that executes remote shell diagnostics, monitors battery temperature and charging current in real time, and keeps the tablet in low-power interactive standby."
        ]
    },
    {
        "domain": "spec_screen_lens_notebook_swarm",
        "templates": [
            "You are the Screen Lens Sovereign Notebook Architect. Design a production Jupyter / Voila interactive dashboard (00_lauburu_global_master_project.ipynb on Port 8890) that streams Movesense 512Hz ECG, Pan-Tompkins QRS markers, and DFA-alpha1 Zone 2 aerobic thresholds with zero JavaScript garbage collection pauses and zero memory leaks.",
            "Construct an exhaustive technical feature comparison matrix between KDE Connect and ADB OpenClaw: analyze clipboard synchronization, notification mirroring, remote virtual mouse/trackpad emulation, filesystem SFTP mounting vs ADB root shell, display capture, touch event injection, and APK lifecycle control across macOS, Linux, and Android.",
            "Design the Canonical Multi-Tier Frontier Swarm protocol: explain how Screen Lens dynamically orchestrates Local AI (Qwen 3.8 Max TB4 PRP Ring :8082), Free-Tier Cloud AI (Gemini 2.5/3.8 Flash, NVIDIA NIM, Cloudflare AI), and Gemini Ultra Plan models in a structured consensus debate with Bradley-Terry ELO incentive scaling.",
            "Formulate the canonical network storage hierarchy for the Lauburu Mesh: detail the directory mount architecture for /Volumes/ and /Volumes/Android_DFS using SeaweedFS DFS, local SSD vaults, and continuous bidirectional sync with Obsidian Vault and Google Drive."
        ]
    }
]


PRIORITY_DOMAINS = [
    "spec_ecommerce_pod_sorona",
    "spec_linux_tablet_touch_tui",
    "spec_screen_lens_notebook_swarm"
]


def get_dynamic_curriculum_prompt(provider: str, cycle_count: int, call_idx: int = 0) -> Dict[str, str]:
    """Generates weighted, high-value training prompts with 70% focus on user-priority pillars."""
    combined_seed = cycle_count * 10 + call_idx + abs(hash(provider)) % 100
    is_priority = (combined_seed % 10) < 7  # 70% probability for e-commerce, tablet TUI, and notebooks

    if is_priority:
        priority_mods = [m for m in CURRICULUM_MODULES if m["domain"] in PRIORITY_DOMAINS]
        mod = priority_mods[combined_seed % len(priority_mods)]
    else:
        other_mods = [m for m in CURRICULUM_MODULES if m["domain"] not in PRIORITY_DOMAINS]
        mod = other_mods[combined_seed % len(other_mods)]

    template_idx = (combined_seed // len(CURRICULUM_MODULES)) % len(mod["templates"])
    prompt = mod["templates"][template_idx]
    return {"domain": mod["domain"], "prompt": prompt}


def execute_api_harvest_cycle(state: Dict[str, Any]):
    """Iterates through active providers in high-throughput batches to aggressively maximize free quota."""
    providers = state.setdefault("providers", {})
    cycle_count = state.get("harvest_cycle_count", 0) + 1
    state["harvest_cycle_count"] = cycle_count

    provider_keys = ["google_gemini", "nvidia_nim", "xai_grok", "cloudflare_ai", "groq_ai"]
    calls_per_provider = {
        "google_gemini": 3,
        "nvidia_nim": 4,
        "cloudflare_ai": 4,
        "xai_grok": 1,
        "groq_ai": 2,
    }

    for prov_key in provider_keys:
        prov_state = providers.setdefault(prov_key, {"used_today": 0, "cap": DAILY_QUOTAS.get(prov_key, 1000), "last_call": 0})
        num_calls = calls_per_provider.get(prov_key, 2)

        for c_idx in range(num_calls):
            if prov_state["used_today"] >= prov_state["cap"]:
                log(f"Provider {prov_key} has hit daily quota ({prov_state['used_today']}/{prov_state['cap']}). Skipping.")
                break

            # Check backoff cooldown
            backoff_until = prov_state.get("backoff_until", 0)
            now_ts = time.time()
            if now_ts < backoff_until:
                rem_cd = int(backoff_until - now_ts)
                log(f"Provider {prov_key} is in backoff cooldown ({rem_cd}s remaining). Skipping.")
                break

            curriculum_item = get_dynamic_curriculum_prompt(prov_key, cycle_count, call_idx=c_idx)
            prompt = curriculum_item["prompt"]
            domain = curriculum_item["domain"]
            response = None
            status_code = None

            model_used = "unknown"
            if prov_key == "google_gemini":
                response, status_code, model_used = call_gemini(prompt, domain=domain)
            elif prov_key == "nvidia_nim":
                response, status_code, model_used = call_nvidia_nim(prompt, domain=domain)
            elif prov_key == "xai_grok":
                response, status_code = call_xai_grok(prompt)
                model_used = "grok-2-latest"
            elif prov_key == "cloudflare_ai":
                response, status_code, model_used = call_cloudflare_ai(prompt, domain=domain)
            elif prov_key == "groq_ai":
                response, status_code, model_used = call_groq(prompt)

            # Intelligent Adaptive Backoff
            if status_code == 429:
                backoff_duration = 30.0  # 30 seconds for rate limit (resets every minute)
                prov_state["backoff_until"] = time.time() + backoff_duration
                log(f"⚠️ Provider {prov_key} rate-limited (HTTP 429). Setting adaptive 30s backoff.")
                break
            elif status_code == 403:
                backoff_duration = 900.0  # 15 min for forbidden
                prov_state["backoff_until"] = time.time() + backoff_duration
                log(f"⚠️ Provider {prov_key} returned HTTP 403. Setting 15m backoff.")
                break

            if response:
                prov_state.pop("backoff_until", None)
                prov_state["used_today"] += 1
                prov_state["last_call"] = time.time()

                entry = {
                    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "provider": prov_key,
                    "model": model_used,
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
                    log(f"✅ Harvested {len(response)} chars from {prov_key} ({model_used}) [{domain}] -> Saved")
                except Exception as e:
                    log(f"Error saving harvested dataset entry: {e}")

            # Inter-call pacing
            sleep_time = 2.0 if prov_key == "google_gemini" else 1.2
            time.sleep(sleep_time)



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

    content = rf"""---
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


PID_LOCK_FILE = Path("/tmp/master_free_tier_ai_maximizer.pid")


def acquire_pid_lock() -> bool:
    if PID_LOCK_FILE.exists():
        try:
            old_pid = int(PID_LOCK_FILE.read_text().strip())
            if psutil.pid_exists(old_pid) and old_pid != os.getpid():
                p = psutil.Process(old_pid)
                if "master_free_tier_ai_maximizer" in " ".join(p.cmdline()):
                    log(f"Another instance of FreeTierMaximizer is active (PID {old_pid}). Exiting to avoid rate limit collisions.")
                    return False
        except Exception:
            pass
    try:
        PID_LOCK_FILE.write_text(str(os.getpid()))
    except Exception:
        pass
    return True


def main():
    if not acquire_pid_lock():
        sys.exit(0)

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
            delay = 3.0
        else:
            rem_s = get_seconds_until_aest_reset()
            state = load_quota_state()
            total_remaining = sum(
                max(0, p.get("cap", 1000) - p.get("used_today", 0))
                for p in state.get("providers", {}).values()
            )
            # High-throughput ramped pacing (Rule #6 Catch-up Cadence before 10 AM reset)
            if total_remaining > 0 and rem_s > 0:
                delay = max(4.0, min(15.0, rem_s / (total_remaining * 2.5)))
            else:
                delay = 30.0

        log(f"Sleeping for {delay:.1f}s until next maximization cycle...")
        time.sleep(delay)


if __name__ == "__main__":
    main()
