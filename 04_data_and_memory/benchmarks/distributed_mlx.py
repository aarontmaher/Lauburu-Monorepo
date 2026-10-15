import argparse
import gc
import json
import os
import platform
import sys
import time
from typing import Dict, List, Any
import numpy as np
import mlx.core as mx
import mlx.core.distributed as dist

SEQUENCE_LENGTHS = [32, 64, 128, 256, 512, 1024, 2048, 4096]
BATCH_SIZE = 1
HIDDEN_DIM = 4096
DTYPE = mx.float16
WARMUP_ROUNDS = 5
TIMED_ROUNDS = 25

def compute_stats(arr: List[float]) -> Dict[str, float]:
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "median": float(np.median(arr)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr))
    }

def run_benchmark(mode: str = "all_reduce"):
    group = dist.init(strict=True, backend="ring")
    rank = group.rank()
    world_size = group.size()
    
    node_name = platform.node()
    system_info = f"{platform.system()} {platform.machine()}"
    
    if rank == 0:
        print(f"\n============================================================")
        print(f"  MLX DISTRIBUTED BENCHMARK: {mode.upper()} OVER THUNDERBOLT 4")
        print(f"============================================================")
        print(f"Cluster Size: {world_size} Nodes | Rank 0: {node_name} ({system_info})")
        print(f"MLX Version:  {mx.__version__} | Active Device: {mx.default_device()}")
        print(f"Tensor Config: Batch={BATCH_SIZE}, HiddenDim={HIDDEN_DIM}, Dtype=Float16 (2 bytes/val)")
        print(f"------------------------------------------------------------\n")

    results = []

    for seq_len in SEQUENCE_LENGTHS:
        shape = (BATCH_SIZE, seq_len, HIDDEN_DIM)
        # float16 = 2 bytes per element
        bytes_per_tensor = BATCH_SIZE * seq_len * HIDDEN_DIM * 2
        mb_per_tensor = bytes_per_tensor / (1024 * 1024)
        
        # Allocate random activation tensor directly on Apple Silicon Metal GPU
        x = mx.random.normal(shape).astype(DTYPE)
        mx.eval(x)

        if mode == "all_reduce":
            # Warmup
            for _ in range(WARMUP_ROUNDS):
                y = dist.all_sum(x)
                mx.eval(y)

            latencies_ms = []
            for _ in range(TIMED_ROUNDS):
                gc.disable()
                t0 = time.perf_counter_ns()
                y = dist.all_sum(x)
                mx.eval(y)
                t1 = time.perf_counter_ns()
                gc.enable()
                latencies_ms.append((t1 - t0) / 1e6)

            stats = compute_stats(latencies_ms)
            # In a 2-node ring, all_sum transfers 2 * ((2-1)/2) * bytes = 1 * bytes per node
            throughput_mb_s = mb_per_tensor / (stats["mean"] / 1000.0)
            tokens_per_sec = seq_len / (stats["mean"] / 1000.0)

            if rank == 0:
                print(f"[*] SeqLen: {seq_len:4d} ({mb_per_tensor:6.2f} MB) | "
                      f"Latency: {stats['mean']:7.3f} ms (p95: {stats['p95']:7.3f} ms) | "
                      f"Throughput: {throughput_mb_s:8.2f} MB/s | "
                      f"Tokens/s: {tokens_per_sec:9.1f}")
                results.append({
                    "seq_len": seq_len,
                    "mb_per_tensor": mb_per_tensor,
                    "mean_latency_ms": stats["mean"],
                    "p95_latency_ms": stats["p95"],
                    "min_latency_ms": stats["min"],
                    "max_latency_ms": stats["max"],
                    "throughput_mb_s": throughput_mb_s,
                    "tokens_per_sec": tokens_per_sec
                })

        elif mode == "all_gather":
            # Warmup
            for _ in range(WARMUP_ROUNDS):
                y = dist.all_gather(x)
                mx.eval(y)

            latencies_ms = []
            for _ in range(TIMED_ROUNDS):
                gc.disable()
                t0 = time.perf_counter_ns()
                y = dist.all_gather(x)
                mx.eval(y)
                t1 = time.perf_counter_ns()
                gc.enable()
                latencies_ms.append((t1 - t0) / 1e6)

            stats = compute_stats(latencies_ms)
            throughput_mb_s = mb_per_tensor / (stats["mean"] / 1000.0)
            tokens_per_sec = seq_len / (stats["mean"] / 1000.0)

            if rank == 0:
                print(f"[*] SeqLen: {seq_len:4d} ({mb_per_tensor:6.2f} MB) | "
                      f"Latency: {stats['mean']:7.3f} ms (p95: {stats['p95']:7.3f} ms) | "
                      f"Throughput: {throughput_mb_s:8.2f} MB/s | "
                      f"Tokens/s: {tokens_per_sec:9.1f}")
                results.append({
                    "seq_len": seq_len,
                    "mb_per_tensor": mb_per_tensor,
                    "mean_latency_ms": stats["mean"],
                    "p95_latency_ms": stats["p95"],
                    "min_latency_ms": stats["min"],
                    "max_latency_ms": stats["max"],
                    "throughput_mb_s": throughput_mb_s,
                    "tokens_per_sec": tokens_per_sec
                })

    if rank == 0:
        output_file = f"/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/04_ANALYTICS/mlx_{mode}_thunderbolt_benchmark.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n[+] Saved empirical telemetry to {output_file}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLX Distributed Ring Benchmark")
    parser.add_argument("--mode", choices=["all_reduce", "all_gather"], default="all_reduce", help="Benchmark collective mode")
    args = parser.parse_args()
    run_benchmark(mode=args.mode)
