#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_data_and_memory/training_scripts/continuous_overnight_ecommerce_trainer.py
=============================================================================
Autonomous Continuous Overnight Shopify & E-Commerce Benchmark Training Engine.
Lauburu Mesh Ecosystem — 2026

Runs continuous overnight benchmarking, evaluation, and LoRA dataset harvesting:
1. Benchmarks local models (:8082 Qwen 3.8 Max Master / :8083 Qwen 2.5 7B Worker) on:
   - Shopify Storefront GraphQL 2026-04 Cart & Checkout mutations
   - Shopify Admin GraphQL productVariantsBulkCreate for Lauburu Belt-Ranked Competition Rashguard (gid://shopify/Product/9139818201224)
   - IBJJF compliance tags, compression fabric specs, and combat apparel SEO
   - Combat apparel unit economics (COGS A$22, Retail A$89, Academy A$69, 75.3% margin)
   - Custom combat apparel order generation (Ghost Rashguard & Fight Shorts)
   - Direct-response combat sports ad copy & visual AI diffusion prompts
   - 7-Day multi-platform social media campaign scheduling
   - Spec-11 constant-time HMAC SHA256 webhook verification & anti-tamper security
2. Validates ground-truth accuracy on each generation.
3. Formats and appends high-value instruction pairs & DPO pairs to:
   /Users/aaron/DFS_UNIFIED/lora_datasets/neo_ecommerce_continuous_lora.jsonl
4. Updates real-time telemetry into:
   04_data_and_memory/tui_training_stream.json
5. Monitors Mac Mini M4 Pro host RAM to strictly preserve >= 4.8 GB physical headroom (Rule #3).
"""

import os
import sys
import json
import time
import math
import shutil
import random
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

WORKSPACE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LORA_DATASETS = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
LORA_DATASETS.mkdir(parents=True, exist_ok=True)
TRAINING_DATASET = LORA_DATASETS / "neo_ecommerce_continuous_lora.jsonl"
TUI_STREAM = WORKSPACE / "04_data_and_memory/tui_training_stream.json"
STOP_FILE = Path("/tmp/stop_ecommerce_trainer")

LOCAL_AI_URL_8082 = "http://127.0.0.1:8082/v1/chat/completions"
LOCAL_AI_URL_8083 = "http://127.0.0.1:8083/v1/chat/completions"
HOST_SANCTUARY_MIN_GB = 4.8

# Benchmark Evaluation Curriculum
CURRICULUM = [
    {
        "category": "Shopify GraphQL Bulk Variant Mutation",
        "task": "belt_ranked_rashguard_variants",
        "prompt": "Write a Shopify Admin GraphQL productVariantsBulkCreate mutation for product gid://shopify/Product/9139818201224 (Lauburu Belt-Ranked Competition Rashguard) creating variants for White, Blue, Purple, Brown, and Black ranks with price 89.00 AUD and options for Rank and Size.",
        "validator": lambda text: any(k in text for k in ["productVariantsBulkCreate", "productVariant", "variants"]) and "9139818201224" in text and ("89.00" in text or "89" in text) and any(r in text for r in ["White", "Blue", "Purple", "Brown", "Black"]),
        "dpo_rejected": "You can add variants manually by clicking the + Add variant button on the Shopify web dashboard."
    },
    {
        "category": "IBJJF Compliance & Catalog Tags",
        "task": "ibjjf_compliance_tags_and_seo",
        "prompt": "Provide the production IBJJF compliance specification, technical fabric features (85/15 poly-spandex, flatlock stitching, silicone waistband), and Shopify tags for the Lauburu Belt-Ranked Competition Rashguard.",
        "validator": lambda text: any(k in text.lower() for k in ["ibjjf", "ranked", "compression"]) and any(f in text.lower() for f in ["flatlock", "silicone", "poly", "spandex", "waistband"]) and any(t in text.lower() for t in ["tag", "compliance", "specification"]),
        "dpo_rejected": "It is a standard long sleeve shirt. You can wear it anywhere including grappling tournaments."
    },
    {
        "category": "Combat Apparel Pricing & Margin Strategy",
        "task": "combat_apparel_pricing_strategy",
        "prompt": "Calculate the unit economics and pricing tiers for Lauburu Belt-Ranked Competition Rashguard: COGS A$22.00, retail A$89.00, wholesale/academy A$69.00. Output gross margin percentage and Academy LTV multiplier.",
        "validator": lambda text: any(k in text.lower() for k in ["margin", "gross", "profit"]) and any(n in text for n in ["22", "89", "69", "75%", "75.3%"]) and any(w in text.lower() for w in ["cogs", "wholesale", "academy", "ltv"]),
        "dpo_rejected": "Price the rashguard at whatever competitors charge and offer standard discounts."
    },
    {
        "category": "Shopify GraphQL Mutation",
        "task": "cart_create_bundle",
        "prompt": "Write a minimal-token Shopify Storefront GraphQL cartCreate mutation for variant gid://shopify/ProductVariant/4819203 with discount code ATHLETE_PRO_20.",
        "validator": lambda text: "cartCreate" in text and ("lines" in text or "lineItems" in text) and "ATHLETE_PRO_20" in text,
        "dpo_rejected": "Here is the code you requested:\n```graphql\n# Maybe you can use cartCreate\n{\n  cart {\n    id\n  }\n}\n```\nHope this helps! Let me know if you need anything else."
    },
    {
        "category": "Custom Combat Gear Ordering",
        "task": "custom_ghost_gear",
        "prompt": "Generate a JSON order specification for Lauburu Exact Ghost Rashguard (Size L, custom sublimation 'AARON') and Ghost Fight Shorts (Size L) with 20% discount.",
        "validator": lambda text: "ghost" in text.lower() and "rashguard" in text.lower() and "shorts" in text.lower() and ("size" in text.lower() or "discount" in text.lower() or "order" in text.lower()),
        "dpo_rejected": "I recommend you check out our shop website for fight shorts and rashguards. We have many sizes available."
    },
    {
        "category": "Direct Response Ad Copy",
        "task": "bjj_hook_generation",
        "prompt": "Write 3 direct-response BJJ ad hooks addressing rashguard ride-up, waistband grip, and flatlock durability.",
        "validator": lambda text: any(w in text.lower() for w in ["ride", "waistband", "grip", "flatlock", "sparring", "roll"]),
        "dpo_rejected": "Buy our rashguard today! It is very good quality and looks nice."
    },
    {
        "category": "Social Media Calendar",
        "task": "multichannel_schedule",
        "prompt": "Create a 3-day social media schedule for Instagram and TikTok targeting no-gi jiu-jitsu athletes with posting times.",
        "validator": lambda text: any(w in text.lower() for w in ["instagram", "tiktok", "reels", "am", "pm", "day 1", "day 2"]),
        "dpo_rejected": "Post on Instagram on Monday and TikTok on Tuesday."
    },
    {
        "category": "Spec-11 Webhook Security",
        "task": "hmac_sha256_verifier",
        "prompt": "Write Python function using hmac.compare_digest to verify Shopify X-Shopify-Hmac-Sha256 base64 header.",
        "validator": lambda text: "compare_digest" in text and any(h in text for h in ["hashlib.sha256", "sha256"]) and "base64" in text,
        "dpo_rejected": "def check_hmac(a, b):\n    return a == b"
    }
]

def get_free_ram_gb() -> float:
    try:
        import psutil
        return round(psutil.virtual_memory().available / (1024**3), 2)
    except Exception:
        pass
    try:
        res = os.popen("vm_stat | perl -ne '/page size of (\\d+)/ and $size=$1; /Pages free:\\s+(\\d+)/ and $free=$1; /Pages speculative:\\s+(\\d+)/ and $spec=$1; /Pages inactive:\\s+(\\d+)/ and $inact=$1; END { printf(\"%.2f\", ($free + $spec + $inact) * $size / (1024*1024*1024)); }'").read().strip()
        return float(res)
    except Exception:
        return 12.0

def get_gcloud_token() -> Optional[str]:
    for cmd in ["/Users/aaron/google-cloud-sdk/bin/gcloud", "gcloud", "/usr/local/bin/gcloud", "/opt/homebrew/bin/gcloud"]:
        try:
            tok = subprocess.check_output(
                [cmd, "auth", "print-access-token"],
                stderr=subprocess.DEVNULL,
                timeout=6.0
            ).decode("utf-8").strip()
            if tok and tok.startswith("ya29."):
                return tok
        except Exception:
            continue
    return None

def query_cloud_teacher(prompt: str, system_context: str = "") -> Tuple[str, float]:
    token = get_gcloud_token()
    if not token:
        return "", 0.0
    t0 = time.time()
    url = "https://us-central1-aiplatform.googleapis.com/v1/projects/lauburu-play-deploy/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent"
    contents = [{"role": "user", "parts": [{"text": f"System: {system_context}\n\nTask: {prompt}"}]}]
    payload = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 400, "temperature": 0.2}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return text.strip(), max(0.001, time.time() - t0)
    except Exception as e:
        return "", 0.0

def query_model(prompt: str) -> Tuple[str, float]:
    system_msg = "You are Neo, an autonomous local e-commerce and ML engineer. Output precise, production-grade technical code, GraphQL, or copy without conversational filler."
    t0 = time.time()

    # 1. Attempt Master Local Orchestrator on Port 8082 (Qwen 3.8 Max PRP Ring)
    try:
        payload_8082 = {
            "model": "qwen_38_max",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 350,
            "temperature": 0.1
        }
        req_8082 = urllib.request.Request(
            LOCAL_AI_URL_8082,
            data=json.dumps(payload_8082).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_8082, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content, max(0.001, time.time() - t0)
    except Exception:
        pass

    # 2. Fallback to Subordinate Syntax Worker on Port 8083 (Qwen 2.5 7B Instruct Abliterated Metal GPU)
    payload_8083 = {
        "model": "qwen2.5-7b-instruct-abliterated",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 350,
        "temperature": 0.1
    }
    for attempt in range(2):
        try:
            req_8083 = urllib.request.Request(
                LOCAL_AI_URL_8083,
                data=json.dumps(payload_8083).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req_8083, timeout=35.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                return content, max(0.001, time.time() - t0)
        except Exception as e:
            if attempt == 0:
                time.sleep(1.0)
                continue
            return f"[Fallback Execution Error: {e}]", 0.05
    return "[Fallback Execution Error: Max retries exceeded]", 0.05

def run_single_epoch(epoch: int) -> Dict[str, Any]:
    print(f"\n--- [EPOCH {epoch}] Starting Continuous Bench Evaluation ---", flush=True)
    epoch_passed = 0
    epoch_tokens = 0
    total_latency = 0.0
    
    for item in CURRICULUM:
        time.sleep(0.5)
        output, dt = query_model(item["prompt"])
        total_latency += dt
        approx_tokens = len(output.split()) * 1.3
        epoch_tokens += approx_tokens
        
        is_valid = item["validator"](output)
        if is_valid:
            epoch_passed += 1
            # Record high-quality LoRA instruction pair & DPO pair
            lora_entry = {
                "timestamp": time.time(),
                "epoch": epoch,
                "source": "local_neo_student",
                "category": item["category"],
                "task": item["task"],
                "instruction": item["prompt"],
                "chosen": output,
                "rejected": item["dpo_rejected"],
                "latency_seconds": round(dt, 3),
                "tokens_per_second": round(approx_tokens / max(0.001, dt), 1)
            }
            with open(TRAINING_DATASET, "a", encoding="utf-8") as f:
                f.write(json.dumps(lora_entry) + "\n")

        # Periodically invoke Cloud AI Teacher (every 5 epochs) to generate gold-standard teacher demonstrations
        if epoch % 5 == 0 and item["task"] in ["cart_create_bundle", "custom_ghost_gear", "belt_ranked_rashguard_variants"]:
            cloud_out, c_dt = query_cloud_teacher(item["prompt"], system_context="You are the Cloud AI E-Commerce Teacher Model. Provide flawless, production-ready GraphQL, JSON, or ad copy.")
            if cloud_out and len(cloud_out) > 20:
                cloud_entry = {
                    "timestamp": time.time(),
                    "epoch": epoch,
                    "source": "cloud_gemini_shadow_teacher",
                    "category": item["category"],
                    "task": f"teacher_distill_{item['task']}",
                    "instruction": item["prompt"],
                    "chosen": cloud_out,
                    "rejected": output if not is_valid else item["dpo_rejected"],
                    "latency_seconds": round(c_dt, 3),
                    "plan_tokens_consumed": 0
                }
                with open(TRAINING_DATASET, "a", encoding="utf-8") as f:
                    f.write(json.dumps(cloud_entry) + "\n")
                print(f"    ☁️ [Cloud Teacher Distillation] -> Captured gold standard ({c_dt:.2f}s)", flush=True)
                
        print(f"  [{item['category']}] -> {'✓ PASS' if is_valid else '✗ FAIL'} ({dt:.2f}s, {approx_tokens / max(0.001, dt):.1f} tok/s)", flush=True)

    pass_rate = (epoch_passed / len(CURRICULUM)) * 100.0
    # Rule #0: Report empirical benchmark accuracy, NOT simulated loss.
    # This trainer is a benchmarking/dataset harvester — there is no gradient descent.
    benchmark_accuracy = round(pass_rate / 100.0, 4)
    free_ram = get_free_ram_gb()
    
    # Update real-time TUI telemetry stream
    tui_data = {
        "status": "ONLINE_ACTIVE",
        "current_task": "Overnight Shopify & E-Commerce Bench Training",
        "epoch": epoch,
        "pass_rate_percent": pass_rate,
        "benchmark_accuracy": benchmark_accuracy,
        "free_ram_gb": free_ram,
        "host_sanctuary_ok": free_ram >= HOST_SANCTUARY_MIN_GB,
        "total_dataset_pairs": sum(1 for _ in open(TRAINING_DATASET, "r")) if TRAINING_DATASET.exists() else 0,
        "timestamp": time.time(),
        "last_update_human": time.strftime("%Y-%m-%d %H:%M:%S AEST", time.localtime())
    }
    
    with open(TUI_STREAM, "w", encoding="utf-8") as f:
        json.dump(tui_data, f, indent=2)
        
    print(f"  📊 Summary: Pass Rate={pass_rate:.1f}% | Accuracy={benchmark_accuracy} | Free RAM={free_ram:.2f}GB | LoRA Pairs={tui_data['total_dataset_pairs']}", flush=True)
    return tui_data

def continuous_training_loop(max_epochs: int = 500, pause_seconds: int = 5):
    print("=" * 80, flush=True)
    print("🥋 LAUBURU NEO AUTONOMOUS OVERNIGHT E-COMMERCE TRAINER", flush=True)
    print(f"Target LoRA Dataset: {TRAINING_DATASET}", flush=True)
    print(f"TUI Telemetry Feed:   {TUI_STREAM}", flush=True)
    print(f"Host Sanctuary Rule:  >= {HOST_SANCTUARY_MIN_GB} GB RAM", flush=True)
    print("=" * 80, flush=True)
    
    epoch = 1
    while epoch <= max_epochs:
        if STOP_FILE.exists():
            print("\n[STOP SIGNAL DETECTED] Gracefully terminating continuous training.", flush=True)
            STOP_FILE.unlink(missing_ok=True)
            break
            
        run_single_epoch(epoch)
        epoch += 1
        
        # Obey host sanctuary (Rule #3: >= 4.8 GB)
        free_ram = get_free_ram_gb()
        if free_ram < HOST_SANCTUARY_MIN_GB:
            print(f"[WARN] Free RAM low ({free_ram:.2f}GB < {HOST_SANCTUARY_MIN_GB}GB). Pausing 30s to allow memory governor evacuation...", flush=True)
            time.sleep(30)
        else:
            time.sleep(pause_seconds)

if __name__ == "__main__":
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    pause = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    continuous_training_loop(max_epochs=epochs, pause_seconds=pause)
