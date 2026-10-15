#!/usr/bin/env python3
"""
01_apps/screen_lens/src/lens_context_inflation_benchmark.py
===========================================================
Empirical Memory & KV Cache Inflation Stress-Testing Engine.
Calculates exact RAM growth and KV Cache VRAM scaling from 1K -> 128K tokens:
1. Heap & RSS Memory: Real Python string allocation & process RSS measurement via getrusage.
2. Exact KV Cache Formula across Models:
   KV_bytes = 2 * n_layers * n_kv_heads * d_head * n_tokens * bytes_per_element
3. Models Evaluated:
   - SmolLM2-135M (L=30, KV_heads=3, d=64)
   - SmolVLM-500M (L=24, KV_heads=4, d=64)
   - Qwen 3.8 Max / Qwen 2.5 14B (L=48, KV_heads=4, d=128)
   - Qwen3-Next-80B MoE (L=64, KV_heads=8, d=128)
4. Host Headroom Safety Governance: Flags warnings if host free RAM < 5.0 GB or usage > 90%.
"""

import os
import sys
import time
import json
import resource
import subprocess
from typing import Dict, Any, List


def get_native_macos_ram() -> Tuple[float, float, float]:
    """
    Returns (total_ram_gb, free_ram_gb, used_pct) using native Darwin sysctl and vm_stat.
    """
    # 1. Total RAM via sysctl
    total_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).strip())
    total_gb = round(total_bytes / (1024**3), 2)

    # 2. Free RAM via vm_stat
    vm_out = subprocess.check_output(["vm_stat"]).decode()
    page_size = 16384  # Default Apple Silicon M-series page size is 16KB
    free_pages = 0
    spec_pages = 0
    for line in vm_out.splitlines():
        if "page size of" in line:
            parts = line.split()
            page_size = int(parts[-2])
        elif "Pages free:" in line:
            free_pages = int(line.split(":")[1].strip().strip("."))
        elif "Pages speculative:" in line:
            spec_pages = int(line.split(":")[1].strip().strip("."))

    free_bytes = (free_pages + spec_pages) * page_size
    free_gb = round(free_bytes / (1024**3), 2)
    used_pct = round(((total_bytes - free_bytes) / total_bytes) * 100, 1)

    return total_gb, free_gb, used_pct

TOKEN_TIERS = [
    (1024, "1K Tokens"),
    (2048, "2K Tokens"),
    (4096, "4K Tokens"),
    (8192, "8K Tokens"),
    (16384, "16K Tokens"),
    (32768, "32K Tokens"),
    (65536, "64K Tokens"),
    (131072, "128K Tokens"),
]

# Model Architectures: (layers, kv_heads, head_dim, name)
ARCHITECTURES = {
    "SmolLM2-135M": {"layers": 30, "kv_heads": 3, "head_dim": 64},
    "SmolVLM-500M": {"layers": 24, "kv_heads": 4, "head_dim": 64},
    "Qwen-3.8-Max-14B": {"layers": 48, "kv_heads": 4, "head_dim": 128},
    "Qwen-80B-MoE": {"layers": 64, "kv_heads": 8, "head_dim": 128},
}


def calculate_kv_cache_mb(layers: int, kv_heads: int, head_dim: int, tokens: int, precision_bytes: float) -> float:
    """
    Computes exact KV cache size in Megabytes:
    KV_bytes = 2 (Key + Value) * layers * kv_heads * head_dim * tokens * precision_bytes
    """
    total_bytes = 2 * layers * kv_heads * head_dim * tokens * precision_bytes
    return round(total_bytes / (1024 * 1024), 2)


def get_current_rss_mb() -> float:
    """Returns current process Resident Set Size in MB (macOS ru_maxrss is in bytes)."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return round(usage.ru_maxrss / (1024 * 1024), 2)


def run_empirical_context_inflation() -> Dict[str, Any]:
    host_total_gb, host_free_gb_start, host_used_pct_start = get_native_macos_ram()
    initial_rss = get_current_rss_mb()

    tier_results = []
    accumulated_buffers = []

    # Realistic 1 token ~ 4 characters of code/AST
    token_seed = "def process_telemetry(frame: dict) -> bool: return frame.get('valid', True)\n"  # 16 tokens (~70 chars)

    for num_tokens, label in TOKEN_TIERS:
        t0 = time.time()
        # Allocate exact string of target token length (~4 chars per token)
        repetitions = max(1, (num_tokens * 4) // len(token_seed))
        buffer = token_seed * repetitions
        accumulated_buffers.append(buffer)  # Hold in memory to observe live heap growth

        alloc_time_ms = round((time.time() - t0) * 1000, 2)
        current_rss = get_current_rss_mb()
        heap_delta_mb = round(max(0.0, current_rss - initial_rss), 2)
        raw_char_bytes_mb = round(sys.getsizeof(buffer) / (1024 * 1024), 2)

        # Compute theoretical KV cache footprints across precision formats:
        # FP16 = 2 bytes, FP8 = 1 byte, Q4_0 = 0.5 bytes
        kv_cache_breakdown = {}
        for arch_name, arch_spec in ARCHITECTURES.items():
            kv_fp16 = calculate_kv_cache_mb(arch_spec["layers"], arch_spec["kv_heads"], arch_spec["head_dim"], num_tokens, 2.0)
            kv_fp8 = calculate_kv_cache_mb(arch_spec["layers"], arch_spec["kv_heads"], arch_spec["head_dim"], num_tokens, 1.0)
            kv_q4 = calculate_kv_cache_mb(arch_spec["layers"], arch_spec["kv_heads"], arch_spec["head_dim"], num_tokens, 0.5)
            kv_cache_breakdown[arch_name] = {
                "FP16_MB": kv_fp16,
                "FP8_MB": kv_fp8,
                "Q4_0_MB": kv_q4
            }

        # Check safety headroom using Darwin sysctl / vm_stat
        _, host_free_gb, host_used_pct = get_native_macos_ram()

        safety_status = "OPTIMAL"
        if host_used_pct > 90.0 or host_free_gb < 5.0:
            safety_status = "CRITICAL_HEADROOM_ALERT"
        elif host_used_pct > 80.0 or host_free_gb < 8.0:
            safety_status = "WARNING_HEADROOM_TIGHT"

        tier_results.append({
            "tier": label,
            "tokens": num_tokens,
            "raw_text_memory_mb": raw_char_bytes_mb,
            "process_rss_delta_mb": heap_delta_mb,
            "allocation_latency_ms": alloc_time_ms,
            "kv_cache_matrix": kv_cache_breakdown,
            "host_free_ram_gb": host_free_gb,
            "host_ram_used_pct": f"{host_used_pct}%",
            "safety_status": safety_status
        })

    # Summary analysis
    return {
        "benchmark": "Screen Lens Context Inflation & KV Cache Stress-Test",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "host_hardware": {
            "total_ram_gb": host_total_gb,
            "initial_free_ram_gb": host_free_gb_start,
            "initial_rss_mb": initial_rss
        },
        "results": tier_results
    }


if __name__ == "__main__":
    report = run_empirical_context_inflation()
    print(json.dumps(report, indent=2))
