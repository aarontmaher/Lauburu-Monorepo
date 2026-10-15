#!/usr/bin/env python3
"""
Petals / Hivemind Distributed AI Training & Backpropagation Protocol Benchmark
Isolating Backward Pass Gradient Compression Scheme (C_grad) on L3 Linux Mini ('lens-opt-tester').

Single Isolated Variable:
- Backward Gradient Compression Scheme (runtime_pb2.CompressionType):
  [NONE, FLOAT16, MEANSTD_16BIT, UNIFORM_8BIT, QUANTILE_8BIT, BLOCKWISE_8BIT]

Strictly Controlled Constants:
- Batch Size B = 1
- Sequence Length S = 256
- Hidden Dimension D = 4096 (1,048,576 elements, 4.00 MB Float32)
- Forward Activation Compression: FLOAT16 (Proven optimal in previous benchmark)
- Model Layer: Transformer RMS/LayerNorm + Linear(4096, 4096)
- PRNG Seed: 42
- Rounds: 5 warmup + 20 timed repetitions
"""

import os
import sys
import gc
import time
import json
import math
import socket
import platform
import asyncio
from typing import Dict, Any, List

import torch
import torch.nn as nn
import hivemind
from hivemind.p2p import P2P
from hivemind.proto import runtime_pb2
from hivemind.compression import serialize_torch_tensor, deserialize_torch_tensor

BATCH_SIZE = 1
SEQUENCE_LENGTH = 256
HIDDEN_DIM = 4096
WARMUP_ROUNDS = 5
TIMED_ROUNDS = 20
MAX_MSG_SIZE = 64 * 1024 * 1024  # 64 MB buffer limit
SEED = 42

COMPRESSION_MODES = [
    ("NONE_FP32", runtime_pb2.CompressionType.NONE),
    ("FLOAT16", runtime_pb2.CompressionType.FLOAT16),
    ("MEANSTD_16BIT", runtime_pb2.CompressionType.MEANSTD_16BIT),
    ("UNIFORM_8BIT", runtime_pb2.CompressionType.UNIFORM_8BIT),
    ("QUANTILE_8BIT", runtime_pb2.CompressionType.QUANTILE_8BIT),
    ("BLOCKWISE_8BIT", runtime_pb2.CompressionType.BLOCKWISE_8BIT),
]

def calculate_snr(orig: torch.Tensor, recon: torch.Tensor) -> float:
    orig_f = orig.detach().to(torch.float64)
    recon_f = recon.detach().to(torch.float64)
    noise = orig_f - recon_f
    signal_power = torch.sum(orig_f ** 2).item()
    noise_power = torch.sum(noise ** 2).item()
    if noise_power == 0.0:
        return float("inf")
    if signal_power == 0.0:
        return 0.0
    return 10.0 * math.log10(signal_power / noise_power)

def calculate_cosine_sim(orig: torch.Tensor, recon: torch.Tensor) -> float:
    orig_f = orig.detach().flatten().to(torch.float32)
    recon_f = recon.detach().flatten().to(torch.float32)
    sim = torch.nn.functional.cosine_similarity(orig_f.unsqueeze(0), recon_f.unsqueeze(0))
    return float(sim.item())

def calculate_rel_err(orig: torch.Tensor, recon: torch.Tensor) -> float:
    orig_f = orig.detach().flatten().to(torch.float64)
    recon_f = recon.detach().flatten().to(torch.float64)
    diff_norm = torch.norm(orig_f - recon_f, p=2).item()
    orig_norm = torch.norm(orig_f, p=2).item()
    return diff_norm / (orig_norm + 1e-12)

def calculate_max_abs_err(orig: torch.Tensor, recon: torch.Tensor) -> float:
    orig_f = orig.detach().to(torch.float64)
    recon_f = recon.detach().to(torch.float64)
    return float(torch.max(torch.abs(orig_f - recon_f)).item())

def stats(arr: List[float]) -> Dict[str, float]:
    if not arr:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
    s_arr = sorted(arr)
    n = len(s_arr)
    mean_v = sum(arr) / n
    variance = sum((x - mean_v) ** 2 for x in arr) / n if n > 1 else 0.0
    std_v = math.sqrt(variance)
    p50_idx = int(n * 0.50)
    p95_idx = min(int(n * 0.95), n - 1)
    return {
        "mean": round(mean_v, 4),
        "std": round(std_v, 4),
        "min": round(s_arr[0], 4),
        "p50": round(s_arr[p50_idx], 4),
        "p95": round(s_arr[p95_idx], 4),
        "max": round(s_arr[-1], 4),
    }

class RemoteTransformerBlock(nn.Module):
    """Simulates a remote Transformer Linear / LoRA projection block."""
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.norm = nn.LayerNorm(hidden_dim)
        self.proj = nn.Linear(hidden_dim, hidden_dim, bias=False)
        # Fixed deterministic initialization
        with torch.no_grad():
            nn.init.orthogonal_(self.proj.weight)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.proj(self.norm(x))

async def run_benchmark():
    torch.manual_seed(SEED)
    print("====================================================================")
    print("Petals / Hivemind Distributed Training & Backpropagation Protocol Benchmark")
    print("Isolating Backward Pass Gradient Compression Scheme (C_grad)")
    print(f"Host Silicon / Node: L3 Linux Mini (AMD Ryzen 7 5700U)")
    print(f"Kernel:              {platform.platform()}")
    print(f"Container Hostname:  {socket.gethostname()}")
    print(f"Python:              {sys.version.split()[0]}")
    print(f"PyTorch:             {torch.__version__}")
    print(f"Hivemind:            {hivemind.__version__}")
    print(f"Batch Size:          {BATCH_SIZE} (Fixed)")
    print(f"Sequence Length:     {SEQUENCE_LENGTH} (Fixed)")
    print(f"Hidden Dimension:    {HIDDEN_DIM} (Fixed, 1,048,576 elements)")
    print(f"Forward Compression: FLOAT16 (Fixed Constant)")
    print(f"Independent Var:     Backward Gradient Compression (6 modes)")
    print(f"Rounds:              {WARMUP_ROUNDS} warmup + {TIMED_ROUNDS} timed per mode")
    print("====================================================================\n")

    # Instantiate remote block
    remote_block = RemoteTransformerBlock(HIDDEN_DIM)
    remote_block.eval()  # Keep weights deterministic, but compute gradients w.r.t input

    # Server state storage for backward pass
    server_saved_tensors = {}
    current_backward_compression = runtime_pb2.CompressionType.NONE

    # Step 1: Start local P2P Server (simulates remote worker node hosting transformer shard)
    server = await P2P.create(host_maddrs=["/ip4/127.0.0.1/tcp/0"], persistent_conn_max_msg_size=MAX_MSG_SIZE)
    server_addrs = await server.get_visible_maddrs()
    server_peer_id = server.peer_id
    print(f"[Server] Online. Peer ID: {server_peer_id}")

    async def forward_handler(request: runtime_pb2.Tensor, context) -> runtime_pb2.Tensor:
        # Deserialization on server
        x_in = deserialize_torch_tensor(request).requires_grad_(True)
        # Server forward compute
        y_out = remote_block(x_in)
        # Save x_in and y_out for backward step
        req_id = 0
        server_saved_tensors[req_id] = (x_in, y_out)
        # Return forward activation compressed with fixed FLOAT16
        return serialize_torch_tensor(y_out, runtime_pb2.CompressionType.FLOAT16)

    async def backward_handler(request: runtime_pb2.Tensor, context) -> runtime_pb2.Tensor:
        # Deserialization of incoming grad_output on server
        grad_out = deserialize_torch_tensor(request)
        req_id = 0
        x_in, y_out = server_saved_tensors[req_id]
        # Server automatic differentiation backpropagation
        if x_in.grad is not None:
            x_in.grad.zero_()
        y_out.backward(grad_out, retain_graph=True)
        grad_in = x_in.grad.clone()
        # Compress and return input gradient using the isolated variable mode
        return serialize_torch_tensor(grad_in, current_backward_compression)

    await server.add_protobuf_handler("forward_step", forward_handler, runtime_pb2.Tensor)
    await server.add_protobuf_handler("backward_step", backward_handler, runtime_pb2.Tensor)

    # Step 2: Start local P2P Client (simulates master / coordinator node)
    client = await P2P.create(initial_peers=server_addrs, persistent_conn_max_msg_size=MAX_MSG_SIZE)
    print(f"[Client] Online. Connected to Server: {server_peer_id}\n")

    total_elements = BATCH_SIZE * SEQUENCE_LENGTH * HIDDEN_DIM
    raw_fp32_bytes = total_elements * 4

    # Compute Ground Truth Analytical Reference Gradients under exact Float32
    print("[Ground Truth] Computing exact IEEE 754 Float32 gradient reference...")
    torch.manual_seed(SEED)
    ref_input = torch.randn(BATCH_SIZE, SEQUENCE_LENGTH, HIDDEN_DIM, dtype=torch.float32, requires_grad=True)
    ref_target = torch.randn(BATCH_SIZE, SEQUENCE_LENGTH, HIDDEN_DIM, dtype=torch.float32)
    ref_out = remote_block(ref_input)
    ref_loss = nn.functional.mse_loss(ref_out, ref_target)
    ref_loss.backward()
    ground_truth_grad = ref_input.grad.clone().detach()
    print(f"[Ground Truth] Computed reference gradient. Norm: {torch.norm(ground_truth_grad).item():.6f}\n")

    benchmark_results = []

    for mode_name, comp_enum in COMPRESSION_MODES:
        current_backward_compression = comp_enum
        print(f"--- Evaluating Backward Gradient Compression Mode: {mode_name} (Enum: {comp_enum}) ---")

        # Test compatibility in warmup
        try:
            # Fixed deterministic inputs for trials
            torch.manual_seed(SEED + 100)
            client_input = torch.randn(BATCH_SIZE, SEQUENCE_LENGTH, HIDDEN_DIM, dtype=torch.float32)
            grad_out_seed = torch.randn(BATCH_SIZE, SEQUENCE_LENGTH, HIDDEN_DIM, dtype=torch.float32)

            for _ in range(WARMUP_ROUNDS):
                # Forward
                fwd_proto = serialize_torch_tensor(client_input, runtime_pb2.CompressionType.FLOAT16)
                fwd_resp = await client.call_protobuf_handler(server_peer_id, "forward_step", fwd_proto, runtime_pb2.Tensor)
                _ = deserialize_torch_tensor(fwd_resp)
                # Backward
                bwd_proto = serialize_torch_tensor(grad_out_seed, runtime_pb2.CompressionType.FLOAT16)
                bwd_resp = await client.call_protobuf_handler(server_peer_id, "backward_step", bwd_proto, runtime_pb2.Tensor)
                _ = deserialize_torch_tensor(bwd_resp)

            fwd_latencies = []
            bwd_ser_times = []
            bwd_rpc_times = []
            bwd_deser_times = []
            bwd_latencies = []
            step_latencies = []
            wire_size = 0
            reconstructed_grad = None

            # Timed Trials
            for trial in range(TIMED_ROUNDS):
                gc.disable()
                t_step_start = time.perf_counter_ns()

                # --- FORWARD STEP ---
                fwd_proto = serialize_torch_tensor(client_input, runtime_pb2.CompressionType.FLOAT16)
                fwd_resp = await client.call_protobuf_handler(server_peer_id, "forward_step", fwd_proto, runtime_pb2.Tensor)
                client_fwd_out = deserialize_torch_tensor(fwd_resp)
                t_fwd_end = time.perf_counter_ns()
                fwd_ms = (t_fwd_end - t_step_start) / 1000000.0

                # Compute loss gradient at client
                grad_output = 2.0 * (client_fwd_out - ref_target) / total_elements

                # --- BACKWARD STEP ---
                t_bwd_start = time.perf_counter_ns()
                bwd_req_proto = serialize_torch_tensor(grad_output, runtime_pb2.CompressionType.FLOAT16)
                
                # Server computes backward and serializes gradient using mode under test
                t_rpc_start = time.perf_counter_ns()
                bwd_resp_proto = await client.call_protobuf_handler(server_peer_id, "backward_step", bwd_req_proto, runtime_pb2.Tensor)
                t_rpc_end = time.perf_counter_ns()
                rpc_ms = (t_rpc_end - t_rpc_start) / 1000000.0

                wire_size = bwd_resp_proto.ByteSize()

                # Deserialization of returned input gradient
                t_deser_start = time.perf_counter_ns()
                reconstructed_grad = deserialize_torch_tensor(bwd_resp_proto)
                t_deser_end = time.perf_counter_ns()
                deser_us = (t_deser_end - t_deser_start) / 1000.0

                t_step_end = time.perf_counter_ns()
                bwd_ms = (t_step_end - t_bwd_start) / 1000000.0
                step_ms = (t_step_end - t_step_start) / 1000000.0

                gc.enable()

                fwd_latencies.append(fwd_ms)
                bwd_rpc_times.append(rpc_ms)
                bwd_deser_times.append(deser_us)
                bwd_latencies.append(bwd_ms)
                step_latencies.append(step_ms)

            # Gradient Serialization Benchmark (Server-side microbenchmark)
            test_grad = ground_truth_grad.clone()
            ser_times = []
            for _ in range(30):
                t0 = time.perf_counter_ns()
                _ = serialize_torch_tensor(test_grad, comp_enum)
                t1 = time.perf_counter_ns()
                ser_times.append((t1 - t0) / 1000.0)

            # Gradient Fidelity calculation
            snr_db = calculate_snr(ground_truth_grad, reconstructed_grad)
            cosine_sim = calculate_cosine_sim(ground_truth_grad, reconstructed_grad)
            rel_err = calculate_rel_err(ground_truth_grad, reconstructed_grad)
            max_abs_err = calculate_max_abs_err(ground_truth_grad, reconstructed_grad)
            comp_ratio = raw_fp32_bytes / float(wire_size) if wire_size > 0 else 1.0

            fwd_s = stats(fwd_latencies)
            bwd_s = stats(bwd_latencies)
            rpc_s = stats(bwd_rpc_times)
            ser_s = stats(ser_times)
            deser_s = stats(bwd_deser_times)
            step_s = stats(step_latencies)

            step_rate = 1000.0 / step_s["mean"] if step_s["mean"] > 0 else 0.0
            token_throughput = (SEQUENCE_LENGTH / (step_s["mean"] / 1000.0)) if step_s["mean"] > 0 else 0.0
            mb_throughput = ((raw_fp32_bytes * 2 / 1024 / 1024) / (step_s["mean"] / 1000.0)) if step_s["mean"] > 0 else 0.0

            entry = {
                "status": "SUCCESS",
                "mode": mode_name,
                "compression_enum": int(comp_enum),
                "wire_bytes": wire_size,
                "compression_ratio": comp_ratio,
                "gradient_snr_db": snr_db,
                "cosine_similarity": cosine_sim,
                "relative_error": rel_err,
                "max_abs_error": max_abs_err,
                "grad_serialization_us": ser_s,
                "grad_deserialization_us": deser_s,
                "backward_rpc_ms": rpc_s,
                "forward_pass_ms": fwd_s,
                "backward_pass_ms": bwd_s,
                "total_step_ms": step_s,
                "training_steps_per_sec": round(step_rate, 2),
                "training_tokens_per_sec": round(token_throughput, 2),
                "effective_mb_per_sec": round(mb_throughput, 2)
            }

            print(f"  Gradient Wire Size:       {wire_size:,} Bytes ({wire_size / 1024 / 1024:.2f} MB, Ratio: {comp_ratio:.2f}x)")
            print(f"  Gradient SNR:             {snr_db:.2f} dB | Cosine Sim: {cosine_sim:.8f} | Rel Err: {rel_err:.6e}")
            print(f"  Max Absolute Error:       {max_abs_err:.6e}")
            print(f"  Grad Serialization:       {ser_s['mean']:.2f} µs (±{ser_s['std']:.2f})")
            print(f"  Backward RPC:             {rpc_s['mean']:.2f} ms (±{rpc_s['std']:.2f})")
            print(f"  Grad Deserialization:     {deser_s['mean']:.2f} µs (±{deser_s['std']:.2f})")
            print(f"  Total Step Latency:       {step_s['mean']:.2f} ms (±{step_s['std']:.2f})")
            print(f"  Training Step Rate:       {step_rate:.2f} steps/sec ({token_throughput:.2f} tok/s)\n")

        except Exception as e:
            err_msg = str(e)
            print(f"  [Incompatible / Failed]:  {err_msg}\n")
            entry = {
                "status": "INCOMPATIBLE",
                "mode": mode_name,
                "compression_enum": int(comp_enum),
                "error": err_msg
            }

        benchmark_results.append(entry)

    await client.shutdown()
    await server.shutdown()

    out_file = "/tmp/petals_training_backprop_benchmark.json"
    summary = {
        "benchmark_title": "Petals Distributed AI Training & Backpropagation Protocol Benchmark",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "node": "L3 Linux Mini (linux-amd-gpu / 192.168.8.225)",
        "container": "lens-opt-tester",
        "cpu": platform.processor() or "AMD Ryzen 7 5700U",
        "software": {
            "kernel": platform.platform(),
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "hivemind": hivemind.__version__
        },
        "isolated_variable": "Backward Pass Gradient Compression Scheme (C_grad)",
        "fixed_parameters": {
            "batch_size": BATCH_SIZE,
            "sequence_length": SEQUENCE_LENGTH,
            "hidden_dimension": HIDDEN_DIM,
            "total_elements": total_elements,
            "raw_fp32_bytes": raw_fp32_bytes,
            "forward_compression": "FLOAT16",
            "warmup_rounds": WARMUP_ROUNDS,
            "timed_rounds": TIMED_ROUNDS,
            "seed": SEED
        },
        "results": benchmark_results
    }

    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"[Done] Benchmark completed! Empirical results saved to: {out_file}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
