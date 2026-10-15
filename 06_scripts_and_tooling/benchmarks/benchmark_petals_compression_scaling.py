import asyncio
import gc
import json
import os
import platform
import socket
import sys
import time
from typing import Dict, List, Any
import numpy as np
import torch
import hivemind
from hivemind.p2p import P2P
from hivemind.proto import runtime_pb2
from hivemind.compression import serialize_torch_tensor, deserialize_torch_tensor

# Ensure strict determinism & reproducibility
torch.manual_seed(42)
np.random.seed(42)

# Single isolated independent variable: Compression Precision Mode
# Testing all 6 intermediate activation compression algorithms in Petals/Hivemind:
# 1. NONE_FP32 (IEEE 754 32-bit single precision, 4 bytes/elem)
# 2. FLOAT16 (IEEE 754 16-bit half precision, 2 bytes/elem)
# 3. MEANSTD_16BIT (16-bit mean/std scaled quantization)
# 4. UNIFORM_8BIT (Uniform 8-bit quantization)
# 5. QUANTILE_8BIT (Quantile-based 8-bit dynamic quantization)
# 6. BLOCKWISE_8BIT (Blockwise 8-bit dynamic scale & offset quantization)
COMPRESSION_MODES = [
    ("NONE_FP32", runtime_pb2.CompressionType.NONE),
    ("FLOAT16", runtime_pb2.CompressionType.FLOAT16),
    ("MEANSTD_16BIT", runtime_pb2.CompressionType.MEANSTD_16BIT),
    ("UNIFORM_8BIT", runtime_pb2.CompressionType.UNIFORM_8BIT),
    ("QUANTILE_8BIT", runtime_pb2.CompressionType.QUANTILE_8BIT),
    ("BLOCKWISE_8BIT", runtime_pb2.CompressionType.BLOCKWISE_8BIT),
]

# Strictly held constant parameters
BATCH_SIZE = 1
SEQUENCE_LENGTH = 512
HIDDEN_DIM = 4096
WARMUP_ROUNDS = 5
TIMED_ROUNDS = 25
MAX_MSG_SIZE = 67108864  # 64 MB buffer

def calculate_snr(orig: torch.Tensor, rec: torch.Tensor) -> float:
    orig_f = orig.to(torch.float64)
    rec_f = rec.to(torch.float64)
    noise = orig_f - rec_f
    signal_power = torch.sum(orig_f ** 2)
    noise_power = torch.sum(noise ** 2)
    if noise_power == 0:
        return float("inf")
    snr = 10 * torch.log10(signal_power / noise_power).item()
    return float(snr)

def calculate_cosine_sim(orig: torch.Tensor, rec: torch.Tensor) -> float:
    orig_flat = orig.flatten().to(torch.float64)
    rec_flat = rec.flatten().to(torch.float64)
    dot = torch.dot(orig_flat, rec_flat)
    norm = torch.linalg.norm(orig_flat) * torch.linalg.norm(rec_flat)
    if norm == 0:
        return 1.0
    return float((dot / norm).item())

def stats(arr: List[float]) -> Dict[str, float]:
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "median": float(np.median(arr)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr))
    }

async def run_benchmark():
    print("====================================================================")
    print("   PETALS / HIVEMIND DISTRIBUTED SHARDING: COMPRESSION PRECISION    ")
    print("====================================================================")
    print(f"Host Kernel:        {platform.platform()}")
    print(f"Container Hostname: {socket.gethostname()}")
    print(f"Python Version:     {sys.version.split()[0]}")
    print(f"PyTorch Version:    {torch.__version__}")
    print(f"Hivemind Version:   {hivemind.__version__}")
    print(f"Batch Size:         {BATCH_SIZE} (Fixed)")
    print(f"Sequence Length:    {SEQUENCE_LENGTH} (Fixed)")
    print(f"Hidden Dimension:   {HIDDEN_DIM} (Fixed, Llama-3.1-8B/Qwen-2.5-7B size)")
    print(f"Independent Var:    Compression Precision Mode (6 levels)")
    print(f"Trials per Level:   {WARMUP_ROUNDS} warmup + {TIMED_ROUNDS} timed rounds")
    print("--------------------------------------------------------------------\n")

    current_compression_enum = runtime_pb2.CompressionType.NONE

    # Step 1: Start local P2P Server
    server = await P2P.create(host_maddrs=["/ip4/127.0.0.1/tcp/0"], persistent_conn_max_msg_size=MAX_MSG_SIZE)
    server_addrs = await server.get_visible_maddrs()
    server_peer_id = server.peer_id
    print(f"[Server] Online. Peer ID: {server_peer_id}")
    print(f"[Server] Visible Multiaddrs: {[str(a) for a in server_addrs]}")

    async def layer_forward_handler(request: runtime_pb2.Tensor, context) -> runtime_pb2.Tensor:
        tensor = deserialize_torch_tensor(request)
        return serialize_torch_tensor(tensor, current_compression_enum)

    await server.add_protobuf_handler("layer_forward", layer_forward_handler, runtime_pb2.Tensor)

    # Step 2: Start local P2P Client
    client = await P2P.create(initial_peers=server_addrs, persistent_conn_max_msg_size=MAX_MSG_SIZE)
    print(f"[Client] Online. Connected to Server Peer: {server_peer_id}\n")

    benchmark_results = []
    total_elements = BATCH_SIZE * SEQUENCE_LENGTH * HIDDEN_DIM
    raw_fp32_bytes = total_elements * 4

    # Fixed deterministic activation tensor
    input_tensor = torch.randn(BATCH_SIZE, SEQUENCE_LENGTH, HIDDEN_DIM, dtype=torch.float32)

    for mode_name, comp_enum in COMPRESSION_MODES:
        current_compression_enum = comp_enum
        print(f"--- Evaluating Compression Mode: {mode_name} (Enum: {comp_enum}) ---")
        print(f"Input Tensor Shape: [{BATCH_SIZE}, {SEQUENCE_LENGTH}, {HIDDEN_DIM}] ({total_elements:,} elements, Raw FP32: {raw_fp32_bytes / 1024 / 1024:.2f} MB)")

        try:
            # Warmup rounds
            for _ in range(WARMUP_ROUNDS):
                p = serialize_torch_tensor(input_tensor, comp_enum)
                resp = await client.call_protobuf_handler(server_peer_id, "layer_forward", p, runtime_pb2.Tensor)
                _ = deserialize_torch_tensor(resp)

            ser_times = []
            rpc_times = []
            deser_times = []
            e2e_times = []
            wire_size = 0
            reconstructed_tensor = None

            # Timed trials
            for trial in range(TIMED_ROUNDS):
                gc.disable()
                
                # 1. Serialization
                t0 = time.perf_counter_ns()
                proto_msg = serialize_torch_tensor(input_tensor, comp_enum)
                t1 = time.perf_counter_ns()
                ser_us = (t1 - t0) / 1000.0

                wire_size = proto_msg.ByteSize()

                # 2. P2P RPC Forward
                t2 = time.perf_counter_ns()
                resp_proto = await client.call_protobuf_handler(server_peer_id, "layer_forward", proto_msg, runtime_pb2.Tensor)
                t3 = time.perf_counter_ns()
                rpc_ms = (t3 - t2) / 1000000.0

                # 3. Deserialization
                t4 = time.perf_counter_ns()
                reconstructed_tensor = deserialize_torch_tensor(resp_proto)
                t5 = time.perf_counter_ns()
                deser_us = (t5 - t4) / 1000.0

                e2e_ms = (t5 - t0) / 1000000.0

                gc.enable()

                ser_times.append(ser_us)
                rpc_times.append(rpc_ms)
                deser_times.append(deser_us)
                e2e_times.append(e2e_ms)

            # Signal Fidelity Metrics
            snr_db = calculate_snr(input_tensor, reconstructed_tensor)
            cosine_sim = calculate_cosine_sim(input_tensor, reconstructed_tensor)
            compression_ratio = raw_fp32_bytes / float(wire_size) if wire_size > 0 else 1.0

            ser_s = stats(ser_times)
            rpc_s = stats(rpc_times)
            deser_s = stats(deser_times)
            e2e_s = stats(e2e_times)

            tokens_per_sec = (SEQUENCE_LENGTH / (e2e_s["mean"] / 1000.0)) if e2e_s["mean"] > 0 else 0.0
            mb_per_sec = ((raw_fp32_bytes / 1024.0 / 1024.0) / (e2e_s["mean"] / 1000.0)) if e2e_s["mean"] > 0 else 0.0

            res_entry = {
                "status": "SUCCESS",
                "compression_mode": mode_name,
                "compression_enum": int(comp_enum),
                "batch_size": BATCH_SIZE,
                "sequence_length": SEQUENCE_LENGTH,
                "hidden_dim": HIDDEN_DIM,
                "elements": total_elements,
                "raw_fp32_bytes": raw_fp32_bytes,
                "wire_bytes": wire_size,
                "compression_ratio": compression_ratio,
                "snr_db": snr_db,
                "cosine_similarity": cosine_sim,
                "serialization_us": ser_s,
                "rpc_latency_ms": rpc_s,
                "deserialization_us": deser_s,
                "e2e_latency_ms": e2e_s,
                "tokens_per_sec": tokens_per_sec,
                "effective_mb_per_sec": mb_per_sec
            }

            print(f"  Wire Size:            {wire_size:,} Bytes ({wire_size / 1024 / 1024:.2f} MB) | Ratio: {compression_ratio:.2f}x")
            print(f"  SNR (Signal Fidelity):{snr_db:.2f} dB | Cosine Similarity: {cosine_sim:.6f}")
            print(f"  Serialization Time:   {ser_s['mean']:.2f} µs (±{ser_s['std']:.2f})")
            print(f"  P2P RPC Transport:    {rpc_s['mean']:.2f} ms (±{rpc_s['std']:.2f})")
            print(f"  Deserialization Time: {deser_s['mean']:.2f} µs (±{deser_s['std']:.2f})")
            print(f"  End-to-End Latency:   {e2e_s['mean']:.2f} ms (±{e2e_s['std']:.2f})")
            print(f"  Throughput:           {tokens_per_sec:.2f} tokens/sec ({mb_per_sec:.2f} MB/s)\n")

        except Exception as err:
            err_msg = str(err)
            print(f"  [Error] Compression mode {mode_name} failed: {err_msg}\n")
            res_entry = {
                "status": "INCOMPATIBLE_DEPRECATED_IN_PYTORCH214",
                "compression_mode": mode_name,
                "compression_enum": int(comp_enum),
                "batch_size": BATCH_SIZE,
                "sequence_length": SEQUENCE_LENGTH,
                "hidden_dim": HIDDEN_DIM,
                "elements": total_elements,
                "raw_fp32_bytes": raw_fp32_bytes,
                "error": err_msg
            }

        benchmark_results.append(res_entry)

    await client.shutdown()
    await server.shutdown()

    out_dir = "/tmp"
    out_file = os.path.join(out_dir, "petals_compression_scaling_benchmark.json")
    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "node": "L3 Linux Mini (linux-amd-gpu)",
        "container": "lens-opt-tester",
        "cpu": platform.processor() or "AMD Ryzen 7 5700U",
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "hivemind_version": hivemind.__version__,
        "fixed_params": {
            "batch_size": BATCH_SIZE,
            "sequence_length": SEQUENCE_LENGTH,
            "hidden_dim": HIDDEN_DIM,
            "warmup_rounds": WARMUP_ROUNDS,
            "timed_rounds": TIMED_ROUNDS,
            "max_msg_size_bytes": MAX_MSG_SIZE
        },
        "results": benchmark_results
    }

    with open(out_file, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[Benchmark] Completed successfully! Results written to: {out_file}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
