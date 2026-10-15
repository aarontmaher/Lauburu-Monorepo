import argparse
import time
import socket
import gc
import numpy as np

# Try to import ray
try:
    import ray
except ImportError:
    ray = None

SEQUENCE_LENGTHS = [32, 64, 128, 256, 512, 1024]
BATCH_SIZE = 1
HIDDEN_DIM = 4096
WARMUP_ROUNDS = 5
TIMED_ROUNDS = 25

def stats(arr):
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "median": float(np.median(arr)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr))
    }

# Ray remote task that just returns the tensor to simulate a layer forward pass on a remote node
if ray:
    @ray.remote
    def remote_layer_forward(tensor_bytes):
        # In a real scenario, we'd deserialize, compute, and serialize. 
        # Here we just reflect the bytes to measure network overhead.
        return tensor_bytes

def run_ray_benchmark(server_address=None):
    if not ray:
        print("Ray is not installed.")
        return

    print("=== RAY BENCHMARK STARTED ===")
    
    if server_address:
        print(f"Connecting to Ray cluster at {server_address}...")
        ray.init(address=server_address)
    else:
        print("Starting local Ray cluster...")
        ray.init()

    print("Available nodes:")
    print(ray.nodes())

    results = []

    for seq_len in SEQUENCE_LENGTHS:
        print(f"[*] Testing Sequence Length: {seq_len}...", flush=True)
        num_elements = BATCH_SIZE * seq_len * HIDDEN_DIM
        
        # Create a float16 tensor equivalent byte array
        test_bytes = np.random.bytes(num_elements * 2) 
        wire_size = len(test_bytes)

        # Warmup
        for _ in range(WARMUP_ROUNDS):
            future = remote_layer_forward.remote(test_bytes)
            _ = ray.get(future)

        e2e_latencies_ms = []

        for _ in range(TIMED_ROUNDS):
            gc.disable()
            t0 = time.perf_counter_ns()
            
            # Send to remote node and wait for return
            future = remote_layer_forward.remote(test_bytes)
            _ = ray.get(future)
            
            t3 = time.perf_counter_ns()
            gc.enable()

            e2e_latencies_ms.append((t3 - t0) / 1e6)

        e2e_stats = stats(e2e_latencies_ms)
        wire_mb = wire_size / (1024 * 1024)
        
        # E2E throughput includes sending AND receiving, so we multiply wire_mb by 2
        e2e_thpt_mb_s = (wire_mb * 2) / (e2e_stats["mean"] / 1000.0)
        tokens_per_sec = seq_len / (e2e_stats["mean"] / 1000.0)
        
        results.append({
            "seq_len": seq_len,
            "e2e_mean_ms": e2e_stats["mean"],
            "e2e_throughput_mb_s": e2e_thpt_mb_s,
            "tokens_per_sec": tokens_per_sec
        })

        print(f"    -> E2E Thpt: {e2e_thpt_mb_s:.2f} MB/s | {tokens_per_sec:.1f} tokens/s")

    ray.shutdown()
    print("Ray benchmark completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", type=str, default=None, help="Ray head node address (e.g., ray://100.119.199.76:10001)")
    args = parser.parse_args()

    run_ray_benchmark(args.address)
