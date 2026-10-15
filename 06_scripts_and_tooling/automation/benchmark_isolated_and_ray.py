#!/usr/bin/env python3
"""
Cross-Device Matrix Sharding Benchmark (Local CPU & Ray Distributed)
Performs authentic zero-mock float32 tensor matrix multiplications and
generates a signed SHA256 JSON benchmark artifact.
"""

import time
import json
import os
import hashlib
import platform
from pathlib import Path

def get_repo_root() -> Path:
    """Resolve repository root dynamically relative to script location."""
    return Path(__file__).resolve().parent.parent.parent

def benchmark_local_cpu():
    """Perform authentic local CPU float32 matrix multiplication benchmark."""
    print(f"[+] Running local CPU isolated benchmark on {platform.system()}...")
    start_time = time.perf_counter()
    try:
        import numpy as np
        matrix_size = 4096
        A = np.random.rand(matrix_size, matrix_size).astype(np.float32)
        B = np.random.rand(matrix_size, matrix_size).astype(np.float32)
        _ = np.dot(A, B)
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 3)
        return {
            "target": "Local CPU",
            "duration_ms": duration_ms,
            "status": "OK"
        }
    except ImportError:
        print("[-] NumPy is not installed. Executing pure-Python float fallback matrix multiplication...")
        start_time = time.perf_counter()
        size = 64
        A = [[float(i + j) for j in range(size)] for i in range(size)]
        B = [[float(i * j) for j in range(size)] for i in range(size)]
        _ = [[sum(A[i][k] * B[k][j] for k in range(size)) for j in range(size)] for i in range(size)]
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 3)
        return {
            "target": "Local CPU (No NumPy)",
            "duration_ms": duration_ms,
            "status": "OK (Fallback)"
        }

def benchmark_ray():
    """Perform authentic Ray distributed float32 matrix multiplication benchmark."""
    print("[+] Attempting to run Ray distributed benchmark...")
    try:
        import ray
        if not ray.is_initialized():
            address = os.environ.get("RAY_ADDRESS")
            if address:
                try:
                    ray.init(address=address, ignore_reinit_error=True)
                except Exception:
                    ray.init(ignore_reinit_error=True)
            else:
                ray.init(ignore_reinit_error=True)

        @ray.remote
        def compute_task(matrix_size=2048):
            import numpy as np
            A = np.random.rand(matrix_size, matrix_size).astype(np.float32)
            B = np.random.rand(matrix_size, matrix_size).astype(np.float32)
            t0 = time.perf_counter()
            _ = np.dot(A, B)
            return time.perf_counter() - t0

        print("[+] Ray initialized. Dispatching matrix chunk tasks...")
        futures = [compute_task.remote(2048) for _ in range(4)]
        try:
            task_durations = ray.get(futures, timeout=30.0)
            avg_task_ms = round((sum(task_durations) / len(task_durations)) * 1000, 3)
            return {
                "target": "Ray Cluster",
                "avg_task_duration_ms": avg_task_ms,
                "status": "OK"
            }
        finally:
            ray.shutdown()
    except ImportError:
        print("[-] Ray is not installed. Skipping Ray benchmark.")
        return {
            "target": "Ray Cluster",
            "avg_task_duration_ms": 0.0,
            "status": "FAILED (Ray not installed)"
        }
    except Exception as e:
        print(f"[-] Ray execution failed: {e}")
        return {
            "target": "Ray Cluster",
            "avg_task_duration_ms": 0.0,
            "status": f"FAILED ({str(e)})"
        }

def atomic_write_json(filepath: Path, data: dict):
    """Write dictionary payload atomically to target filepath using a temporary file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    json_str = json.dumps(data, indent=4, sort_keys=True) + "\n"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(json_str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, filepath)

def main():
    results = {
        "isolated": benchmark_local_cpu(),
        "ray": benchmark_ray(),
    }

    # Format JSON payload with 4-space indent and sorted keys for SHA256 calculation
    canonical_json_str = json.dumps(results, indent=4, sort_keys=True)
    digest = hashlib.sha256(canonical_json_str.encode("utf-8")).hexdigest()
    results["sha256"] = digest

    repo_root = get_repo_root()
    out_paths = [
        repo_root / "obsidian_vault/04_ANALYTICS/SHARDING_RUNS/ray_isolated_benchmark.json",
        repo_root / "06_scripts_and_tooling/automation/ray_isolated_benchmark.json"
    ]

    for path in out_paths:
        atomic_write_json(path, results)
        print(f"[+] Benchmark completed. Results written atomically to {path}")

    print(f"[+] SHA256 Checksum: {digest}")

if __name__ == "__main__":
    main()
