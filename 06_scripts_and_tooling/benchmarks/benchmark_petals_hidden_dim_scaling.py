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

# Single isolated independent variable: Hidden Dimension D
# Representing canonical model architecture tiers:
# 1024 (TinyLM), 2048 (MiniLM/Gemma-2B), 4096 (Standard 7B/8B), 5120 (14B), 8192 (Sovereign 70B/72B)
HIDDEN_DIMS = [1024, 2048, 4096, 5120, 8192]

# Strictly held constant parameters
BATCH_SIZE = 1
SEQUENCE_LENGTH = 128
COMPRESSION_MODE = runtime_pb2.CompressionType.FLOAT16
WARMUP_ROUNDS = 5
TIMED_ROUNDS = 25
MAX_MSG_SIZE = 67108864 # 64 MB buffer to prevent unary message frame exhaustion

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
    print("   PETALS / HIVEMIND DISTRIBUTED SHARDING: HIDDEN DIMENSION SCALING  ")
    print("====================================================================")
    print(f"Host Kernel:        {platform.platform()}")
    print(f"Container Hostname: {socket.gethostname()}")
    print(f"Python Version:     {sys.version.split()[0]}")
    print(f"PyTorch Version:    {torch.__version__}")
    print(f"Hivemind Version:   {hivemind.__version__}")
    print(f"Batch Size:         {BATCH_SIZE} (Fixed)")
    print(f"Sequence Length:    {SEQUENCE_LENGTH} (Fixed)")
    print(f"Compression Mode:   FLOAT16 (IEEE 754 half precision, Fixed)")
    print(f"Hidden Dimensions:  {HIDDEN_DIMS} (Single Independent Variable)")
    print(f"Trials per Level:   {WARMUP_ROUNDS} warmup + {TIMED_ROUNDS} timed rounds")
    print("--------------------------------------------------------------------\n")

    # Step 1: Start local P2P Server (simulates downstream transformer shard)
    server = await P2P.create(host_maddrs=["/ip4/127.0.0.1/tcp/0"], persistent_conn_max_msg_size=MAX_MSG_SIZE)
    server_addrs = await server.get_visible_maddrs()
    server_peer_id = server.peer_id
    print(f"[Server] Online. Peer ID: {server_peer_id}")
    print(f"[Server] Visible Multiaddrs: {[str(a) for a in server_addrs]}")

    async def layer_forward_handler(request: runtime_pb2.Tensor, context) -> runtime_pb2.Tensor:
        tensor = deserialize_torch_tensor(request)
        # Server responds with identity forward activation
        return serialize_torch_tensor(tensor, COMPRESSION_MODE)

    await server.add_protobuf_handler("layer_forward", layer_forward_handler, runtime_pb2.Tensor)

    # Step 2: Start local P2P Client (simulates upstream transformer client/shard)
    client = await P2P.create(initial_peers=server_addrs, persistent_conn_max_msg_size=MAX_MSG_SIZE)
    print(f"[Client] Online. Connected to Server Peer: {server_peer_id}\n")

    benchmark_results = []

    for d in HIDDEN_DIMS:
        elements = BATCH_SIZE * SEQUENCE_LENGTH * d
        raw_bytes = elements * 4 # FP32 raw
        print(f"--- Evaluating Hidden Dimension D = {d} (Shape: [{BATCH_SIZE}, {SEQUENCE_LENGTH}, {d}], Elements: {elements:,}, Raw: {raw_bytes / 1024 / 1024:.2f} MB) ---")

        # Fixed deterministic activation tensor
        input_tensor = torch.randn(BATCH_SIZE, SEQUENCE_LENGTH, d, dtype=torch.float32)

        # Warmup rounds
        for _ in range(WARMUP_ROUNDS):
            p = serialize_torch_tensor(input_tensor, COMPRESSION_MODE)
            resp = await client.call_protobuf_handler(server_peer_id, "layer_forward", p, runtime_pb2.Tensor)
            _ = deserialize_torch_tensor(resp)

        ser_times = []
        rpc_times = []
        deser_times = []
        e2e_times = []
        wire_size = 0

        # Timed trials
        for trial in range(TIMED_ROUNDS):
            gc.disable()
            
            # 1. Serialization
            t0 = time.perf_counter_ns()
            proto_tensor = serialize_torch_tensor(input_tensor, COMPRESSION_MODE)
            t1 = time.perf_counter_ns()

            wire_size = proto_tensor.ByteSize()

            # 2. P2P libp2p IPC Transit
            t2 = time.perf_counter_ns()
            resp = await client.call_protobuf_handler(server_peer_id, "layer_forward", proto_tensor, runtime_pb2.Tensor)
            t3 = time.perf_counter_ns()

            # 3. Deserialization
            t4 = time.perf_counter_ns()
            out_tensor = deserialize_torch_tensor(resp)
            t5 = time.perf_counter_ns()

            gc.enable()

            ser_ms = (t1 - t0) / 1e6
            rpc_ms = (t3 - t2) / 1e6
            deser_ms = (t5 - t4) / 1e6
            e2e_ms = ser_ms + rpc_ms + deser_ms

            ser_times.append(ser_ms)
            rpc_times.append(rpc_ms)
            deser_times.append(deser_ms)
            e2e_times.append(e2e_ms)

        # Verification metrics against original tensor
        mse = float(torch.mean((input_tensor - out_tensor) ** 2).item())
        max_abs = float(torch.max(torch.abs(input_tensor - out_tensor)).item())
        snr = calculate_snr(input_tensor, out_tensor)
        cos_sim = calculate_cosine_sim(input_tensor, out_tensor)

        comp_ratio = raw_bytes / wire_size if wire_size > 0 else 1.0
        ser_thpt_mb_s = (raw_bytes / 1024 / 1024) / (np.mean(ser_times) / 1000)
        e2e_thpt_mb_s = (raw_bytes / 1024 / 1024) / (np.mean(e2e_times) / 1000)
        total_tokens = BATCH_SIZE * SEQUENCE_LENGTH
        token_rate_tok_s = total_tokens / (np.mean(e2e_times) / 1000)
        transit_cost_us_per_tok = (np.mean(rpc_times) * 1000) / total_tokens

        res = {
            "hidden_dim": d,
            "batch_size": BATCH_SIZE,
            "sequence_length": SEQUENCE_LENGTH,
            "elements": elements,
            "raw_bytes_fp32": raw_bytes,
            "wire_bytes_fp16": wire_size,
            "compression_ratio": float(comp_ratio),
            "ser_latency_ms": stats(ser_times),
            "rpc_latency_ms": stats(rpc_times),
            "deser_latency_ms": stats(deser_times),
            "e2e_latency_ms": stats(e2e_times),
            "serialization_throughput_mb_s": float(ser_thpt_mb_s),
            "e2e_throughput_mb_s": float(e2e_thpt_mb_s),
            "token_rate_tok_s": float(token_rate_tok_s),
            "transit_cost_us_per_token": float(transit_cost_us_per_tok),
            "reconstruction_mse": mse,
            "reconstruction_max_abs_err": max_abs,
            "snr_db": snr,
            "cosine_similarity": cos_sim
        }
        benchmark_results.append(res)

        print(f"  -> Wire Size:      {wire_size:,} Bytes ({wire_size / 1024 / 1024:.2f} MB, {comp_ratio:.2f}x)")
        print(f"  -> Serialization:  {np.mean(ser_times):.2f} +/- {np.std(ser_times):.2f} ms ({ser_thpt_mb_s:.2f} MB/s)")
        print(f"  -> P2P RPC RTT:    {np.mean(rpc_times):.2f} +/- {np.std(rpc_times):.2f} ms")
        print(f"  -> Deserialization:{np.mean(deser_times):.2f} +/- {np.std(deser_times):.2f} ms")
        print(f"  -> Total E2E:      {np.mean(e2e_times):.2f} +/- {np.std(e2e_times):.2f} ms ({e2e_thpt_mb_s:.2f} MB/s)")
        print(f"  -> Token Rate:     {token_rate_tok_s:.1f} tok/s (Transit Cost: {transit_cost_us_per_tok:.2f} us/tok)")
        print(f"  -> SNR:            {snr:.2f} dB (MSE: {mse:.2e}, Cosine Sim: {cos_sim:.8f})\n")

    # Step 3: Cleanup P2P nodes
    print("[Teardown] Shutting down P2P daemons...")
    await client.shutdown()
    await server.shutdown()
    print("[Teardown] Done.")

    # Save output telemetry
    telemetry = {
        "benchmark_metadata": {
            "title": "Petals Distributed Sharding Empirical Benchmark: Hidden Dimension Architecture Scaling",
            "protocol": "Petals / Hivemind Distributed AI Sharding",
            "tested_variable": "hidden_dim",
            "tested_values": HIDDEN_DIMS,
            "held_constant": {
                "batch_size": BATCH_SIZE,
                "sequence_length": SEQUENCE_LENGTH,
                "compression_mode": "FLOAT16",
                "max_msg_size": MAX_MSG_SIZE,
                "warmup_rounds": WARMUP_ROUNDS,
                "timed_rounds": TIMED_ROUNDS,
                "prng_seed": 42
            },
            "environment": {
                "host_kernel": platform.platform(),
                "hostname": socket.gethostname(),
                "python_version": sys.version.split()[0],
                "pytorch_version": torch.__version__,
                "hivemind_version": hivemind.__version__,
                "hardware_node": "L3 Linux Mini (AMD Ryzen 7 5700U, 15GB RAM)",
                "container_id": socket.gethostname()
            },
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        },
        "results": benchmark_results
    }

    out_path = "/home/benchmarks/petals_hidden_dim_scaling_results.json"
    with open(out_path, "w") as f:
        json.dump(telemetry, f, indent=2)
    print(f"\n[Telemetry] Benchmark results saved to {out_path} ({os.path.getsize(out_path)} Bytes).")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
