#!/usr/bin/env python3
"""
Petals / Hivemind & 4-Node Heterogeneous Cross-Device Pipeline Sharding Benchmark
Ecosystem: L1 (Mac Mini M4 Pro), L1b (Mac Mini M2 Pro), L2 (MacBook Pro Intel), L3 (Linux AMD Ryzen 7)
"""
import os
import sys
import time
import json
import gc
import socket
import platform
import subprocess
import re
import asyncio
from typing import Dict, List, Any
import numpy as np
import torch
import hivemind
from hivemind.p2p import P2P, PeerID
from hivemind.proto import runtime_pb2
from hivemind.compression import serialize_torch_tensor, deserialize_torch_tensor

# Strict reproducibility
torch.manual_seed(42)
np.random.seed(42)

# Darwin Mach Kernel Memory Accounting (Activity Monitor Standard)
def get_darwin_memory_metrics() -> Dict[str, Any]:
    try:
        vm_stat = subprocess.check_output("vm_stat", shell=True, text=True)
        pagesize = int(subprocess.check_output("sysctl -n hw.pagesize", shell=True, text=True).strip())
        memsize = int(subprocess.check_output("sysctl -n hw.memsize", shell=True, text=True).strip())
        pressure = int(subprocess.check_output("sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null || echo 1", shell=True, text=True).strip())

        pages = {}
        for line in vm_stat.splitlines():
            m = re.match(r'\"?([^\":]+)\"?:\s+(\d+)\.', line.strip())
            if m:
                pages[m.group(1)] = int(m.group(2))

        anon = pages.get("Anonymous pages", 0)
        purgeable = pages.get("Pages purgeable", 0)
        wired = pages.get("Pages wired down", 0)
        compressed = pages.get("Pages occupied by compressor", 0)
        file_backed = pages.get("File-backed pages", 0)

        app_mem = max(0, (anon - purgeable) * pagesize)
        wired_mem = wired * pagesize
        compressed_mem = compressed * pagesize
        cached_files = (file_backed + purgeable) * pagesize
        mem_used = app_mem + wired_mem + compressed_mem
        free_headroom = memsize - mem_used
        util_pct = (mem_used / memsize) * 100.0

        return {
            "total_gb": round(memsize / (1024**3), 3),
            "mem_used_gb": round(mem_used / (1024**3), 3),
            "free_headroom_gb": round(free_headroom / (1024**3), 3),
            "app_mem_gb": round(app_mem / (1024**3), 3),
            "wired_gb": round(wired_mem / (1024**3), 3),
            "compressed_gb": round(compressed_mem / (1024**3), 3),
            "cached_gb": round(cached_files / (1024**3), 3),
            "util_pct": round(util_pct, 2),
            "pressure_level": pressure
        }
    except Exception as e:
        return {"error": str(e)}

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
    arr_sorted = sorted(arr)
    n = len(arr_sorted)
    mean_val = sum(arr_sorted) / n
    variance = sum((x - mean_val) ** 2 for x in arr_sorted) / n
    std_val = variance ** 0.5
    median_val = arr_sorted[n // 2] if n % 2 != 0 else (arr_sorted[n // 2 - 1] + arr_sorted[n // 2]) / 2.0
    p95_idx = int(n * 0.95)
    return {
        "mean_ms": round(mean_val, 4),
        "std_ms": round(std_val, 4),
        "min_ms": round(arr_sorted[0], 4),
        "median_ms": round(median_val, 4),
        "p95_ms": round(arr_sorted[min(p95_idx, n - 1)], 4),
        "max_ms": round(arr_sorted[-1], 4)
    }

async def benchmark_petals_p2p_l1_l3():
    print("\n====================================================================")
    print("   PETALS / HIVEMIND CROSS-DEVICE P2P SHARDING: L1 (M4) <-> L3 (AMD) ")
    print("====================================================================")
    print(f"Client (L1): Apple M4 Pro Mac Mini (macOS Darwin 26.6.2, 24GB)")
    print(f"Server (L3): AMD Ryzen 7 5700U Linux Head Node (Ubuntu 24.04, 15GB)")
    print(f"Transport:   1GbE / Wi-Fi LAN (192.168.8.225:31330)")
    print("--------------------------------------------------------------------\n")

    # Deploy remote P2P server script to L3
    remote_server_code = '''
import asyncio
import json
import torch
import hivemind
from hivemind.p2p import P2P
from hivemind.proto import runtime_pb2
from hivemind.compression import serialize_torch_tensor, deserialize_torch_tensor

async def main():
    p2p = await P2P.create(host_maddrs=["/ip4/0.0.0.0/tcp/31330"], persistent_conn_max_msg_size=67108864)
    visible = await p2p.get_visible_maddrs()
    print("SERVER_READY:" + str(p2p.peer_id), flush=True)
    print("MADDRS:" + json.dumps([str(a) for a in visible]), flush=True)
    
    async def forward_handler(req: runtime_pb2.Tensor, ctx) -> runtime_pb2.Tensor:
        t = deserialize_torch_tensor(req)
        # Apply layer normalization simulation
        t_out = t / (torch.norm(t, dim=-1, keepdim=True) + 1e-5)
        return serialize_torch_tensor(t_out, req.compression)
        
    await p2p.add_protobuf_handler("shard_forward", forward_handler, runtime_pb2.Tensor)
    
    # Keep alive until terminated
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
'''
    with open("/tmp/l3_p2p_server.py", "w") as f:
        f.write(remote_server_code)
    subprocess.run(["scp", "-o", "BatchMode=yes", "/tmp/l3_p2p_server.py", "linux@192.168.8.225:/tmp/l3_p2p_server.py"], check=True)

    subprocess.run(["ssh", "-o", "BatchMode=yes", "linux@192.168.8.225", "pkill -f /tmp/l3_p2p_server.py || true"], stderr=subprocess.DEVNULL)
    time.sleep(1.0)

    # Launch server on L3 in background
    cmd_l3 = ["ssh", "-o", "BatchMode=yes", "linux@192.168.8.225", "/home/linux/.venv_sharding/bin/python", "-u", "/tmp/l3_p2p_server.py"]
    proc_l3 = subprocess.Popen(cmd_l3, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # Wait for SERVER_READY line
    peer_id_str = None
    maddrs = []
    for i in range(60):
        line = proc_l3.stdout.readline()
        if not line:
            time.sleep(0.5)
            continue
        line_clean = line.strip()
        if "SERVER_READY:" in line_clean:
            peer_id_str = line_clean.split("SERVER_READY:")[1]
        elif "MADDRS:" in line_clean:
            maddrs = json.loads(line_clean.split("MADDRS:")[1])
            break
        time.sleep(0.2)

    if not peer_id_str or not maddrs:
        print("[Error] Failed to initialize L3 P2P Shard Server.")
        proc_l3.kill()
        return []

    print(f"[L3 Shard Server] Online. Peer ID: {peer_id_str}")
    print(f"[L3 Visible Multiaddrs]: {maddrs}")
    peer_id = PeerID.from_base58(peer_id_str)

    # Filter to accessible IPv4 addresses
    connect_addrs = [a for a in maddrs if "/127.0.0.1" not in a and "/ip4/" in a]
    if not connect_addrs:
        connect_addrs = [f"/ip4/192.168.8.225/tcp/31330/p2p/{peer_id_str}"]

    print(f"[L1 Dialing Target]: {connect_addrs}")
    client_p2p = await P2P.create(initial_peers=connect_addrs, persistent_conn_max_msg_size=67108864)
    print(f"[L1 Client] Connected to L3 over LAN via libp2p!\n")

    HIDDEN_DIMS = [1024, 2048, 4096, 8192]
    COMPRESSIONS = [
        ("FLOAT16", runtime_pb2.CompressionType.FLOAT16),
        ("NONE_FP32", runtime_pb2.CompressionType.NONE)
    ]
    WARMUP = 3
    TIMED = 15

    results = []

    for comp_name, comp_mode in COMPRESSIONS:
        print(f"--- Petals Compression Mode: {comp_name} ---")
        for d in HIDDEN_DIMS:
            b, s = 1, 128
            input_tensor = torch.randn(b, s, d, dtype=torch.float32)
            elements = b * s * d
            raw_bytes = elements * 4

            # Warmup
            for _ in range(WARMUP):
                p = serialize_torch_tensor(input_tensor, comp_mode)
                p.compression = comp_mode
                resp = await client_p2p.call_protobuf_handler(peer_id, "shard_forward", p, runtime_pb2.Tensor)
                _ = deserialize_torch_tensor(resp)

            ser_times, rpc_times, deser_times, e2e_times = [], [], [], []
            wire_size = 0
            out_tensor = None

            for _ in range(TIMED):
                gc.disable()
                t0 = time.perf_counter_ns()
                p = serialize_torch_tensor(input_tensor, comp_mode)
                p.compression = comp_mode
                t1 = time.perf_counter_ns()
                wire_size = p.ByteSize()

                t2 = time.perf_counter_ns()
                resp = await client_p2p.call_protobuf_handler(peer_id, "shard_forward", p, runtime_pb2.Tensor)
                t3 = time.perf_counter_ns()

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

            # Metrics
            expected_norm = input_tensor / (torch.norm(input_tensor, dim=-1, keepdim=True) + 1e-5)
            mse = float(torch.mean((expected_norm - out_tensor) ** 2).item())
            snr = calculate_snr(expected_norm, out_tensor)
            cos_sim = calculate_cosine_sim(expected_norm, out_tensor)

            st_ser = stats(ser_times)
            st_rpc = stats(rpc_times)
            st_deser = stats(deser_times)
            st_e2e = stats(e2e_times)

            thpt_mb_s = (raw_bytes / (1024**2)) / (st_e2e["mean_ms"] / 1000.0)
            tok_s = (b * s) / (st_e2e["mean_ms"] / 1000.0)
            transit_cost_us = (st_rpc["mean_ms"] * 1000.0) / (b * s)

            res = {
                "protocol": "Petals_Hivemind_P2P",
                "nodes": "L1_MacMini_M4 <-> L3_Linux_AMD",
                "transport": "1GbE_LAN",
                "compression": comp_name,
                "hidden_dim": d,
                "elements": elements,
                "raw_bytes": raw_bytes,
                "wire_bytes": wire_size,
                "compression_ratio": round(raw_bytes / wire_size, 2) if wire_size > 0 else 1.0,
                "ser_stats": st_ser,
                "rpc_stats": st_rpc,
                "deser_stats": st_deser,
                "e2e_stats": st_e2e,
                "throughput_mb_s": round(thpt_mb_s, 2),
                "token_rate_tok_s": round(tok_s, 2),
                "transit_cost_us_per_token": round(transit_cost_us, 2),
                "reconstruction_snr_db": round(snr, 2),
                "cosine_similarity": round(cos_sim, 6),
                "reconstruction_mse": mse
            }
            results.append(res)
            print(f"  D={d:4d} | Wire: {wire_size/1024:6.1f} KB | Ser: {st_ser['mean_ms']:5.2f} ms | RPC: {st_rpc['mean_ms']:5.2f} ms | Deser: {st_deser['mean_ms']:5.2f} ms | E2E: {st_e2e['mean_ms']:6.2f} ms | Thpt: {thpt_mb_s:6.2f} MB/s | Rate: {tok_s:5.1f} tok/s | SNR: {snr:5.2f} dB")

    # Cleanup
    await client_p2p.shutdown()
    proc_l3.kill()
    subprocess.run(["ssh", "-o", "BatchMode=yes", "linux@192.168.8.225", "pkill -f l3_p2p_server"], stderr=subprocess.DEVNULL)
    return results

if __name__ == "__main__":
    res = asyncio.run(benchmark_petals_p2p_l1_l3())
    out_f = "obsidian_vault/04_ANALYTICS/SHARDING_RUNS/petals_cross_device_p2p_results_2026.json"
    with open(out_f, "w") as f:
        json.dump(res, f, indent=2)
    print(f"\n[Saved] Petals cross-device telemetry saved to {out_f}")
