import argparse
import asyncio
import gc
import json
import socket
import sys
import time
import platform
from typing import Dict, List, Any
import numpy as np
import torch
import hivemind
from hivemind.p2p import P2P
from hivemind.proto import runtime_pb2
from hivemind.compression import serialize_torch_tensor, deserialize_torch_tensor

torch.manual_seed(42)
np.random.seed(42)

SEQUENCE_LENGTHS = [32, 64, 128, 256, 512, 1024]
BATCH_SIZE = 1
HIDDEN_DIM = 4096
COMPRESSION_MODE = runtime_pb2.CompressionType.FLOAT16
WARMUP_ROUNDS = 5
TIMED_ROUNDS = 25
MAX_MSG_SIZE = 33554432 # 32 MB

def stats(arr: List[float]) -> Dict[str, float]:
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "median": float(np.median(arr)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr))
    }

async def run_server():
    server = await P2P.create(host_maddrs=["/ip4/0.0.0.0/tcp/31337"], persistent_conn_max_msg_size=MAX_MSG_SIZE)
    server_addrs = await server.get_visible_maddrs()
    print("=== SERVER STARTED ===")
    print("MADDR:", [str(a) for a in server_addrs])
    
    last_received_tensor = None
    
    async def layer_forward_handler(request: runtime_pb2.Tensor, context) -> runtime_pb2.Tensor:
        nonlocal last_received_tensor
        received = deserialize_torch_tensor(request)
        last_received_tensor = received.clone()
        return serialize_torch_tensor(received, COMPRESSION_MODE)

    await server.add_protobuf_handler("layer_forward", layer_forward_handler, runtime_pb2.Tensor)
    print("Listening for layer_forward requests. Press Ctrl+C to stop.")
    try:
        await asyncio.sleep(86400)
    except KeyboardInterrupt:
        pass
    await server.shutdown()

async def run_client(peer_maddrs: List[str]):
    print("=== CLIENT STARTED ===")
    print("Connecting to:", peer_maddrs)
    client = await P2P.create(initial_peers=peer_maddrs, persistent_conn_max_msg_size=MAX_MSG_SIZE)
    # The server peer ID is the last part of the multiaddress (e.g. /p2p/Qm...)
    server_peer_id = hivemind.p2p.PeerID.from_base58(peer_maddrs[0].split('/')[-1])
    
    results = []

    for seq_len in SEQUENCE_LENGTHS:
        print(f"[*] Testing Sequence Length: {seq_len}...", flush=True)
        num_elements = BATCH_SIZE * seq_len * HIDDEN_DIM
        raw_bytes = num_elements * 4
        
        test_tensor = torch.randn(BATCH_SIZE, seq_len, HIDDEN_DIM, dtype=torch.float32)

        # Warmup
        for _ in range(WARMUP_ROUNDS):
            p = serialize_torch_tensor(test_tensor, COMPRESSION_MODE)
            resp = await client.call_protobuf_handler(server_peer_id, "layer_forward", p, runtime_pb2.Tensor)
            _ = deserialize_torch_tensor(resp)

        ser_latencies_ms = []
        deser_latencies_ms = []
        rpc_latencies_ms = []
        e2e_latencies_ms = []
        wire_size = 0

        for _ in range(TIMED_ROUNDS):
            gc.disable()
            t0 = time.perf_counter_ns()
            proto_in = serialize_torch_tensor(test_tensor, COMPRESSION_MODE)
            t1 = time.perf_counter_ns()
            
            resp_proto = await client.call_protobuf_handler(server_peer_id, "layer_forward", proto_in, runtime_pb2.Tensor)
            t2 = time.perf_counter_ns()

            out_tensor = deserialize_torch_tensor(resp_proto)
            t3 = time.perf_counter_ns()
            gc.enable()

            ser_latencies_ms.append((t1 - t0) / 1e6)
            rpc_latencies_ms.append((t2 - t1) / 1e6)
            deser_latencies_ms.append((t3 - t2) / 1e6)
            e2e_latencies_ms.append((t3 - t0) / 1e6)
            wire_size = proto_in.ByteSize()

        ser_stats = stats(ser_latencies_ms)
        rpc_stats = stats(rpc_latencies_ms)
        deser_stats = stats(deser_latencies_ms)
        e2e_stats = stats(e2e_latencies_ms)

        raw_mb = raw_bytes / (1024 * 1024)
        wire_mb = wire_size / (1024 * 1024)
        e2e_thpt_mb_s = raw_mb / (e2e_stats["mean"] / 1000.0)
        tokens_per_sec = seq_len / (e2e_stats["mean"] / 1000.0)
        
        results.append({
            "seq_len": seq_len,
            "e2e_mean_ms": e2e_stats["mean"],
            "rpc_mean_ms": rpc_stats["mean"],
            "e2e_throughput_mb_s": e2e_thpt_mb_s,
            "tokens_per_sec": tokens_per_sec
        })

        print(f"    -> E2E Thpt: {e2e_thpt_mb_s:.2f} MB/s | {tokens_per_sec:.1f} tokens/s")

    await client.shutdown()
    with open("client_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Client completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--client", type=str, nargs="+")
    args = parser.parse_args()

    if args.server:
        asyncio.run(run_server())
    elif args.client:
        asyncio.run(run_client(args.client))
    else:
        print("Specify --server or --client <maddrs>")
