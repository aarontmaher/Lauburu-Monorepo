# 🌐 Distributed Petals / Hivemind Network Topology & Scaling Benchmark

**Date:** 2026-10-12
**Scope:** Distributed Cross-Device AI Sharding
**Variable Isolated:** Sequence Chunk Length ($S$) scaling across diverse Layer 1 to Layer 3 MTU boundaries.

## 1. Network Topology & Discovery

The benchmark evaluated the `hivemind.p2p.P2P` RPC protocol sending raw `FLOAT16` tensor chunks (`Batch=1, Hidden=4096`) between the Mac Mini M4 Host (L1) and the Linux AMD Head Node (L3). 

**Nodes:**
*   **L1 (Mac Mini M4 - Server):** Tailscale IP `100.119.199.76` (Native Python venv)
*   **L3 (Linux AMD - Client):** Tailscale IP `100.101.39.98` (Docker container `lens-opt-tester`)

### The MTU Blackhole Anomaly
Initial connections via TCP port 31337 succeeded (verified via `nc -vz`), but the DHT Swarm RPC hung indefinitely when transmitting the 256KB tensor payload for $S=32$. 

**Root Cause:**
A classic Path MTU Discovery (PMTUD) blackhole. 
1.  **Tailscale** uses a default MTU of 1280.
2.  **Docker Bridge (`docker0`)** uses a default MTU of 1500.
3.  When `libp2p` transmits the 256KB payload, packets are fragmented with the `DF` (Don't Fragment) bit set. Tailscale replies with ICMP Fragmentation Needed, but the Docker bridge drops the ICMP response or fails to relay it to the container, causing silent TCP hangs.

**Resolution:**
Executed `ip link set eth0 mtu 1280` inside the L3 Docker container to align with Tailscale, immediately unblocking the RPC pipeline.

## 2. Empirical Telemetry Data

### Test A: Localhost Tailscale Loopback (L1 Native ↔ L1 Native)
Connecting to the Tailscale IP natively on the same machine to establish baseline P2P overhead without physical network congestion.

| Sequence Length | Payload Size (Bytes) | End-to-End Throughput | Tokens/Sec |
| :--- | :--- | :--- | :--- |
| **32** | 262,144 | 33.60 MB/s | ~2,150 |
| **64** | 524,288 | 44.06 MB/s | ~2,819 |
| **128** | 1,048,576 | 43.23 MB/s | ~2,766 |
| **256** | 2,097,152 | 47.56 MB/s | ~3,043 |
| **512** | 4,194,304 | 40.59 MB/s | ~2,597 |
| **1024** | 8,388,608 | 29.98 MB/s | ~1,918 |

**Analysis:**
Throughput peaks at $S=256$. Beyond that, local TCP buffer pressure and Python object serialization overhead degrade performance.

### Test B: Cross-Mesh Tailscale (L1 Native ↔ L3 Docker container MTU 1280)
Transmitting the tensor across the Tailscale overlay network from L1 to L3.

| Sequence Length | End-to-End Throughput | Tokens/Sec |
| :--- | :--- | :--- |
| **32** | 0.67 MB/s | ~43 |
| **64** | 0.72 MB/s | ~46 |
| **128** | 0.52 MB/s | ~33 |
| **256** | 0.86 MB/s | ~55 |
| **512** | 1.68 MB/s | ~108 |
| **1024** | 2.49 MB/s | ~160 |

**Analysis:**
The throughput collapses from ~47 MB/s down to **~1.5 MB/s** across the Tailscale overlay when terminating inside a Docker container. 
This extreme bottleneck (~90 tokens/s) renders real-time token generation physically impossible over this specific topology if weights are distributed at the token level (Pipeline Parallelism).

## 3. Conclusions & Canonical Directives

1.  **Avoid Docker for Distributed P2P:** Docker's `bridge` networking combined with Tailscale overlay creates massive packet fragmentation overhead and MTU blackholes. Any `hivemind` or AI sharding daemon MUST be run natively on the host OS or via `--net host` to bypass `veth` processing.
2.  **Tailscale as Fallback Only:** While Tailscale guarantees connectivity, the cryptography and UDP encapsulation overhead reduces throughput to <1 MB/s for large DHT payloads. For primary sharding, agents MUST use the underlying physical IP addresses (e.g., `192.168.8.x`) or the Thunderbolt bridge (`169.254.x.x` / 40 Gbps) as defined in `00_canonical_hardware_matrix.md`.
3.  **Maximum Swarm Payload:** The default Hivemind daemon crashes at payloads $>4\text{MB}$. The `P2P.create(persistent_conn_max_msg_size=33554432)` override is mandatory for context sizes $>256$.

## Test Run Addendum (Daily Mesh Benchmark Automation)

The automated sidecar successfully bootstrapped cross-node execution natively on **L3** and **L2** over the VPN overlay without Docker MTU limitations, demonstrating continuous sharding health testing capabilities.

**L3 (Native Linux AMD via Tailscale) telemetry:**
- 32 seq: ~127 tokens/s (1.99 MB/s)
- 512 seq: ~247.1 tokens/s (3.86 MB/s)

**L2 (Native macOS Intel via Tailscale) telemetry:**
- 32 seq: ~219.7 tokens/s (3.43 MB/s)
- 1024 seq: ~418.5 tokens/s (6.54 MB/s)
