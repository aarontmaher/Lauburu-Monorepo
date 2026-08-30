---
title: "prima.cpp PRP Ring — Deployment Log"
tags: [prima_cpp, PRP, Halda, ZeroMQ, distributed_inference, mesh, llama_cpp]
date: 2026-08-30
status: LIVE
---

# prima.cpp PRP Ring — Deployed 2026-08-30

## Ring Topology

| Node | Role | Port | Binary | Backend |
|---|---|---|---|---|
| Mac Mini M4 (`127.0.0.1`) | **Master** | `8082` | prima-server v4234 | Metal + HiGHS + ZMQ |
| MacBook Pro x86_64 (`100.103.212.21`) | Worker | `50053` | prima-server v1 | Metal + ZMQ |
| MacBook Air M4 (`100.93.158.96`) | Worker | `50053` | prima-server v1 | Metal + HiGHS + ZMQ |
| Linux Head Node (`100.101.39.98`) | Worker | `50053` | building (join pending) | CPU + ZMQ |

## Proven Functional

- `/health` → `{"status":"ok"}` ✅
- Qwen2.5-Coder-7B inference across 3-node ring confirmed ✅
- `next_node_ip = 100.103.212.21:50053,100.93.158.96:50053` visible in master log ✅
- Ring adapter proxy on port `8083` (FastAPI, routes →8082 with →8081 fallback) ✅

## Build Command (macOS ARM64)

```bash
cd ~/prima_cpp
CPPFLAGS="-I$(brew --prefix zeromq)/include" \
LDFLAGS="-L$(brew --prefix zeromq)/lib -lzmq -L$(brew --prefix highs)/lib -lhighs" \
make USE_HIGHS=1 \
     HIGHS_CPPFLAGS="-isystem $(brew --prefix highs)/include/highs" \
     HIGHS_LDFLAGS="-L$(brew --prefix highs)/lib -lhighs" \
     -j$(sysctl -n hw.logicalcpu)
```

## Architecture Notes

- prima.cpp uses **ZeroMQ** (not TCP RPC) for activation streaming between ring nodes
- `--next ip1:port,ip2:port` on master establishes the ring
- No `--worker` flag — workers simply listen on a port
- Halda ILP solver requires `USE_HIGHS=1` (HiGHS LP library) — auto-profiles FLOPS/disk BW
- `win_size` = model layer count assigned to this node's compute window

## LoRA Dataset Entry

```json
{"instruction": "Deploy prima.cpp PRP ring across heterogeneous mesh", "response": "Build with Makefile (not CMake): CPPFLAGS=-I$(brew --prefix zeromq)/include make USE_HIGHS=1. Workers simply listen on a port. Master uses --next ip1:port,ip2:port. SSH user on remote Macs is aaronmaher, not aaron. HOME may be /Users/aaronmaher, not /Users/aaron."}
```

## Related Files

- [[launch_prima_ring.sh]]
- [[prima_ring_adapter.py]]  
- [[prima_vs_rpc_benchmark.py]]
- [[prima_sharding_manifest.json]]
