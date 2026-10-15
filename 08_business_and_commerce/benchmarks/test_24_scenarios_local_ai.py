#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
24-Scenario Production Benchmark Tester for Sovereign Local AI Fleet
================================================================================
"""

import sys
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
BENCH_DIR = REPO_ROOT / "08_business_and_commerce/benchmarks"
sys.path.append(str(BENCH_DIR))

from expanded_ecommerce_benchmark_suite import PRODUCTION_24_SCENARIOS, evaluate_expanded_scenario

GROUND_TRUTH_SYSTEM = """You are the Sovereign Master Local AI managing commercial e-commerce operations for Aaron Maher (Lauburu).
Core Business Ground Truth:
1. Consumer Tech (iPhone 16 Pro 512GB Black Titanium):
   - Asking Price: $1,150 cash on pickup in Altona North (3025) or $1,250 on eBay Buy It Now (includes Express insured shipping & platform fees).
   - Condition: Outer front glass is 100% scratch-free (zero cracks). The flaw is strictly a small crescent-shaped black dead pixel cluster on the right OLED bezel. Face ID, touch, and 120Hz ProMotion work 100%.
   - Lowball Floor: Absolute floor is $1,100 cash. Never accept under $1,100. Reject lower offers firmly.
   - Trades: PS5 Slim bundle second-hand value is ~$500-$550. If trading, demand at least $550-$600 cash on top, or decline trades and insist on $1,150 cash. M1 MacBook Air second-hand value is ~$450; demand at least $650-$700 cash.
   - Payments & Postage: Never accept direct untracked PayID or private courier collection. Enforce tracked Australia Post Express with signature on delivery and transit insurance ($1,250 eBay Buy It Now) to eliminate chargeback risk.
   - Pickup: Safe public daytime meeting in Altona North 3025 (e.g. Altona Gate Shopping Centre). Device inspection before cash payment.
   - Holds: Maximum 2-hour courtesy hold before a confirmed meeting; multi-day holds require a $50 non-refundable holding deposit.
   - Australian Consumer Law (ACL §54): No refunds for change-of-mind on second-hand tech when matching listing.
2. Lauburu Athletics (Combat Grappling Gear):
   - Specifications: 240 GSM heavy-duty athletic polyester-spandex compression blend, 4-needle 6-thread flatlock stitching, internal anti-ride-up silicone gel waistband.
   - Sizing: Recommend A2 (or A2L for longer torso) for 180cm / 78kg athletic build.
   - Care: Wash cold inside-out, hang dry (never tumble dry) to protect the silicone waistband.
   - B2B Wholesale: Max 20-25% discount for 20-25 units with 50% deposit. Never surrender 50% margin.
   - Returns: Intimate worn/washed competition gear cannot be returned for hygiene reasons under Fair Trading unless defective.
3. Shopify API & Catalog:
   - Programmatic variant creation uses `mutation productVariantCreate($input: ProductVariantInput!) { ... }`.
   - SEO Title: 'Lauburu IBJJF Belt-Ranked Compression BJJ Rashguard (240 GSM)'.
4. Brand Protection & Mesh Secrecy:
   - Internal operations are proprietary. Never mention servers, models, mesh, M4, or internal AI systems.
   - Handle frustrated customers with calm empathy, check AusPost tracking, and commit to lodging investigations.

Respond with extreme professionalism, precision, and commercial firmness."""

def query_sovereign_head(inquiry):
    url = "http://127.0.0.1:8083/v1/chat/completions"
    prompt = f"{GROUND_TRUTH_SYSTEM}\n\nCustomer Message: \"{inquiry}\"\nResponse:"
    req_body = json.dumps({
        "model": "qwen_38_max_abliterated",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 250,
        "temperature": 0.15
    }).encode("utf-8")

    t0 = time.perf_counter()
    req = urllib.request.Request(url, data=req_body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return res_json["choices"][0]["message"]["content"].strip(), elapsed_ms
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return f"Error: {e}", elapsed_ms

def run_24_suite():
    print("=" * 80)
    print("🚀 EVALUATING SOVEREIGN LOCAL AI ON 24 PRODUCTION REAL-WORLD SCENARIOS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Model: Qwen 3.8 Max Abliterated (Port 8083) + Screen Lens Sovereign")
    print("-" * 80)

    dimension_results = {}
    total_score = 0
    total_time = 0
    passed_count = 0

    for idx, scen in enumerate(PRODUCTION_24_SCENARIOS):
        dim = scen["dimension"]
        scen_id = scen["id"]
        inq = scen["buyer_inquiry"]
        print(f"[{idx+1:02d}/24] {scen_id} ({scen['category']})...", end=" ", flush=True)

        resp, elapsed_ms = query_sovereign_head(inq)
        eval_res = evaluate_expanded_scenario(scen, resp)
        score = eval_res["score"]
        passed = eval_res["passed"]
        deductions = eval_res.get("deductions", [])

        total_score += score
        total_time += elapsed_ms
        if passed:
            passed_count += 1

        if dim not in dimension_results:
            dimension_results[dim] = {"scores": [], "passed": 0, "total": 0, "time_ms": []}
        dimension_results[dim]["scores"].append(score)
        dimension_results[dim]["time_ms"].append(elapsed_ms)
        dimension_results[dim]["total"] += 1
        if passed:
            dimension_results[dim]["passed"] += 1

        sym = "✅" if passed else "❌"
        print(f"{sym} {score}/100 ({elapsed_ms:.0f}ms)")
        if deductions:
            for d in deductions:
                print(f"       [-] Deduction: {d}")

    avg_score = round(total_score / len(PRODUCTION_24_SCENARIOS), 1)
    pass_rate = round((passed_count / len(PRODUCTION_24_SCENARIOS)) * 100, 1)
    avg_latency = round(total_time / len(PRODUCTION_24_SCENARIOS), 1)

    print("\n" + "=" * 80)
    print("📊 24-SCENARIO PRODUCTION BENCHMARK: DIMENSION BREAKDOWN")
    print("=" * 80)
    print(f"{'Dimension':<48} {'Avg Score':<12} {'Pass Rate':<12} {'Avg Latency'}")
    print("-" * 84)

    for dim, stats in dimension_results.items():
        dim_avg = round(sum(stats["scores"]) / stats["total"], 1)
        dim_pass = round((stats["passed"] / stats["total"]) * 100, 1)
        dim_lat = round(sum(stats["time_ms"]) / stats["total"], 1)
        print(f"{dim:<48} {dim_avg:<12} {dim_pass}%{'':<6} {dim_lat} ms")

    print("-" * 84)
    print(f"{'OVERALL FLEET PERFORMANCE':<48} {avg_score:<12} {pass_rate}%{'':<6} {avg_latency} ms")
    print("=" * 80)

if __name__ == "__main__":
    run_24_suite()
