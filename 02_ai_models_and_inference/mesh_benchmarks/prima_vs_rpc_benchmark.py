#!/usr/bin/env python3
"""
mesh_benchmarks/prima_vs_rpc_benchmark.py
==========================================
Benchmarks prima.cpp PRP ring (port 8082) vs legacy llama.cpp RPC (port 8081).
Measures TTFT (Time to First Token) and TPOT (Time Per Output Token).
Zero-mock: all metrics from live inference. Results written to Obsidian + JSONL.

Usage:
  python prima_vs_rpc_benchmark.py [--shots 50] [--model kimi72b]
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ─── Config ───────────────────────────────────────────────────────────────────

PRIMA_URL  = "http://127.0.0.1:8082/v1/chat/completions"
LEGACY_URL = "http://127.0.0.1:8081/v1/chat/completions"

OBSIDIAN_VAULT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault")
LORA_DATASETS  = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/lora_datasets")

TEST_PROMPTS = [
    "Explain the Transformer attention mechanism in 3 sentences.",
    "Write a Python function to merge two sorted lists.",
    "What is the capital of France and why is it historically significant?",
    "Describe the difference between TCP and UDP protocols.",
    "Summarise the key principles of distributed systems design.",
]

# ─── Benchmark Logic ──────────────────────────────────────────────────────────

def run_inference(url: str, prompt: str, max_tokens: int = 200, timeout: float = 120.0) -> dict:
    """Run a single streaming inference and measure TTFT + TPOT."""
    payload = {
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.1,
    }

    t_start = time.perf_counter()
    t_first_token: float | None = None
    token_count = 0
    full_text = ""

    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    return {"error": f"HTTP {resp.status_code}", "ttft_ms": None, "tpot_ms": None}

                for line in resp.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            if t_first_token is None:
                                t_first_token = time.perf_counter()
                            full_text += delta
                            token_count += 1
                    except (json.JSONDecodeError, KeyError):
                        continue

    except Exception as e:
        return {"error": str(e), "ttft_ms": None, "tpot_ms": None}

    t_end = time.perf_counter()
    ttft_ms = ((t_first_token - t_start) * 1000) if t_first_token else None
    total_s = t_end - t_start
    tpot_ms = ((total_s - (t_first_token - t_start if t_first_token else 0)) / max(token_count - 1, 1) * 1000) if token_count > 1 else None

    return {
        "ttft_ms": round(ttft_ms, 1) if ttft_ms else None,
        "tpot_ms": round(tpot_ms, 1) if tpot_ms else None,
        "total_tokens": token_count,
        "total_s": round(total_s, 2),
        "output_preview": full_text[:120],
    }


def check_health(url_base: str) -> bool:
    """Check if an endpoint is healthy."""
    health_url = url_base.replace("/v1/chat/completions", "/health")
    try:
        r = httpx.get(health_url, timeout=5.0)
        return r.status_code == 200
    except Exception:
        return False


def run_benchmark(shots: int = 20) -> dict:
    """Run full benchmark suite against both endpoints."""
    print(f"\n{'='*60}")
    print(f" Lauburu Mesh — prima.cpp vs llama.cpp RPC Benchmark")
    print(f" Shots: {shots} | Time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"{'='*60}\n")

    # Health checks
    prima_up  = check_health(PRIMA_URL)
    legacy_up = check_health(LEGACY_URL)
    print(f"prima.cpp PRP (8082): {'✅ UP' if prima_up else '❌ DOWN'}")
    print(f"llama.cpp RPC (8081): {'✅ UP' if legacy_up else '❌ DOWN'}")

    if not prima_up and not legacy_up:
        print("\n[ERROR] Both backends are DOWN. Start servers first.")
        return {}

    results = {"prima": [], "legacy": []}

    for i in range(shots):
        prompt = TEST_PROMPTS[i % len(TEST_PROMPTS)]
        print(f"\n[Shot {i+1}/{shots}] Prompt: {prompt[:60]}...")

        if prima_up:
            r = run_inference(PRIMA_URL, prompt)
            results["prima"].append(r)
            status = f"TTFT={r.get('ttft_ms')}ms  TPOT={r.get('tpot_ms')}ms  tokens={r.get('total_tokens')}"
            print(f"  prima.cpp (8082): {status}")
        else:
            print("  prima.cpp (8082): SKIPPED (DOWN)")

        if legacy_up:
            r = run_inference(LEGACY_URL, prompt)
            results["legacy"].append(r)
            status = f"TTFT={r.get('ttft_ms')}ms  TPOT={r.get('tpot_ms')}ms  tokens={r.get('total_tokens')}"
            print(f"  llama.cpp (8081): {status}")
        else:
            print("  llama.cpp (8081): SKIPPED (DOWN)")

    return results


def summarise(results: dict) -> dict:
    """Compute summary statistics from raw benchmark results."""
    summary = {}
    for backend, runs in results.items():
        valid_ttft = [r["ttft_ms"] for r in runs if r.get("ttft_ms") is not None]
        valid_tpot = [r["tpot_ms"] for r in runs if r.get("tpot_ms") is not None]
        summary[backend] = {
            "shots": len(runs),
            "ttft_ms_mean": round(statistics.mean(valid_ttft), 1) if valid_ttft else None,
            "ttft_ms_p50":  round(statistics.median(valid_ttft), 1) if valid_ttft else None,
            "ttft_ms_min":  round(min(valid_ttft), 1) if valid_ttft else None,
            "tpot_ms_mean": round(statistics.mean(valid_tpot), 1) if valid_tpot else None,
            "tpot_ms_p50":  round(statistics.median(valid_tpot), 1) if valid_tpot else None,
            "tpot_ms_min":  round(min(valid_tpot), 1) if valid_tpot else None,
        }
    return summary


def write_obsidian(summary: dict, shots: int):
    """Write benchmark results to Obsidian vault."""
    OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path = OBSIDIAN_VAULT / "PRIMA_BENCHMARK_RESULTS.md"

    p = summary.get("prima", {})
    l = summary.get("legacy", {})

    speedup_tpot = None
    if p.get("tpot_ms_mean") and l.get("tpot_ms_mean"):
        speedup_tpot = round(l["tpot_ms_mean"] / p["tpot_ms_mean"], 1)

    md = f"""---
title: "prima.cpp vs llama.cpp RPC Benchmark Results"
tags: [prima_cpp, benchmark, inference, mesh, lauburu]
updated: "{ts}"
---

# 🚀 prima.cpp PRP vs llama.cpp RPC Benchmark
**Run:** {ts} | **Shots:** {shots}

## Summary

| Metric | prima.cpp PRP (8082) | llama.cpp RPC (8081) | Speedup |
|:--|--:|--:|--:|
| TTFT mean (ms) | {p.get('ttft_ms_mean', '--')} | {l.get('ttft_ms_mean', '--')} | {f"{round(l['ttft_ms_mean']/p['ttft_ms_mean'],1)}×" if p.get('ttft_ms_mean') and l.get('ttft_ms_mean') else '--'} |
| TTFT p50 (ms)  | {p.get('ttft_ms_p50', '--')} | {l.get('ttft_ms_p50', '--')} | — |
| TPOT mean (ms) | {p.get('tpot_ms_mean', '--')} | {l.get('tpot_ms_mean', '--')} | {f"**{speedup_tpot}×**" if speedup_tpot else '--'} |
| TPOT p50 (ms)  | {p.get('tpot_ms_p50', '--')} | {l.get('tpot_ms_p50', '--')} | — |

## Configuration
- **prima.cpp:** Pipelined-Ring Parallelism (PRP) + Halda ILP auto-scheduling
- **llama.cpp:** GGML-RPC tensor split `-ts 28,28,24`
- **Nodes:** Linux Head Node (Vulkan) + MacBook Pro TB4 (Metal) + Mac Mini M4 (Metal)
- **Activation quantization:** INT8 (50% BW reduction)
- **Transport:** Tailscale WireGuard (WAN) + TB4 DMA 10Gbps

## Links
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
"""

    with open(out_path, "w") as f:
        f.write(md)
    print(f"\n✅ Obsidian results: {out_path}")


def write_lora_jsonl(results: dict, summary: dict, shots: int):
    """Write benchmark results as LoRA training instruction pairs."""
    LORA_DATASETS.mkdir(parents=True, exist_ok=True)
    out_path = LORA_DATASETS / "prima_speedup_pairs.jsonl"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    p = summary.get("prima", {})
    l = summary.get("legacy", {})
    speedup = round(l["tpot_ms_mean"] / p["tpot_ms_mean"], 1) if p.get("tpot_ms_mean") and l.get("tpot_ms_mean") else None

    pair = {
        "instruction": "What distributed inference technique provides the best TPOT speedup on the Lauburu mesh for 70B LLMs?",
        "input": f"Measured on {shots} benchmark shots. prima.cpp PRP TPOT={p.get('tpot_ms_mean')}ms, llama.cpp RPC TPOT={l.get('tpot_ms_mean')}ms.",
        "output": f"prima.cpp Pipelined-Ring Parallelism (PRP) with Halda ILP auto-scheduling achieves a {speedup}× speedup over standard llama.cpp GGML-RPC tensor splitting on the Lauburu 3-node mesh (Linux Vulkan + MacBook Pro Metal + Mac Mini M4 Metal). Measured TPOT: prima.cpp={p.get('tpot_ms_mean')}ms vs llama.cpp={l.get('tpot_ms_mean')}ms.",
        "metadata": {"source": "prima_benchmark", "timestamp": ts, "shots": shots, "summary": summary},
    }

    with open(out_path, "a") as f:
        f.write(json.dumps(pair) + "\n")
    print(f"✅ LoRA dataset: {out_path}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="prima.cpp vs llama.cpp RPC benchmark")
    parser.add_argument("--shots", type=int, default=20, help="Number of inference shots per backend")
    args = parser.parse_args()

    results = run_benchmark(shots=args.shots)
    if not results:
        exit(1)

    summary = summarise(results)
    print(f"\n{'='*60}")
    print(" BENCHMARK SUMMARY")
    print(f"{'='*60}")
    for backend, s in summary.items():
        print(f"\n{backend.upper()} (port {'8082' if backend == 'prima' else '8081'}):")
        for k, v in s.items():
            print(f"  {k}: {v}")

    write_obsidian(summary, args.shots)
    write_lora_jsonl(results, summary, args.shots)
    print("\n✅ Benchmark complete.")
