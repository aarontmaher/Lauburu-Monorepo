# Handoff Report: Empirical Challenge of TP-Link Extender & Multi-WAN Nomad Mesh Integration

**Agent**: `challenger_network`  
**Timestamp**: 2026-08-23T20:32:00+10:00  
**Status**: Hard Handoff (Complete)  
**Verdict**: **REJECT**

---

## 1. Observation

1. **Target Artifact Inspection**:
   - `data/network/benchmark_results.json`: Missing across all workspace directories (`find /Users/aaron/DFS_UNIFIED -name "benchmark_results.json"` returned 0 matches).
   - `data/network/tplink_nomad_integration_status.json`: Missing across all workspace directories (`find /Users/aaron/DFS_UNIFIED -name "tplink_nomad_integration_status.json"` returned 0 matches).
   - Only `data/network/wan_fitness_scores.json` exists in `data/network/`.

2. **Code Inspection of Multipath Bonding Engine**:
   - File: `06_scripts_and_tooling/network/tensor_multipath_router.py`
   - Lines 84 & 93:
     ```python
     time.sleep(tensor_size_mb / 275.0) # ~275 MB/s single-link
     ...
     time.sleep(tensor_size_mb / 480.0) # ~480 MB/s combined bonded throughput
     ```
   - Line 44: `INTERFACES["Ethernet_Gigabit"]["ip"] = "192.168.8.230"`, which is not assigned to `en0` (the active LAN IP is `192.168.8.155`).
   - The script simulates network speedup via sleep delays without sending payload bytes over physical network sockets.

3. **Live Empirical Network Socket Probing** (`tests/test_challenger_tplink_nomad_empirical.py` output):
   - **Local LAN (192.168.8.x)**:
     - `192.168.8.1` (GL.iNet Gateway): ICMP 0% loss (RTT avg 3.82ms), Ports 22, 53, 80, 443 OPEN (latency 3.04 - 8.81ms).
     - `192.168.8.224` (Linux-1 Ryzen 7): ICMP 0% loss (RTT avg 6.45ms), Port 22 OPEN (4.90ms), Port 18789 OPEN (5.67ms), Port 50052 (`llama-rpc-server`) OPEN (5.90ms). Port 8080 CLOSED (code 61).
     - `192.168.8.127` (MacBook Pro): ICMP 0% loss (RTT avg 15.83ms), Port 22 OPEN (7.32ms), Port 50052 OPEN (8.92ms).
     - `192.168.8.222` (MacBook-1): ICMP 0% loss (RTT avg 26.01ms), Port 22 OPEN (11.13ms), Port 50052 OPEN (10.16ms).
   - **Tailscale Overlay Mesh (100.x)**:
     - `100.101.39.98` (linux-1): ICMP 0% loss (RTT avg 23.89ms), Port 22 OPEN (6.31ms), Port 8080 OPEN (7.73ms), Port 18789 OPEN (8.38ms). **Port 50052: TIMED OUT / CLOSED (code 35, 1001.05ms)**.
     - `100.103.212.21` (aarons-macbook-pro): ICMP 0% loss (RTT avg 12.43ms), Port 22 OPEN (5.75ms), Port 50052 OPEN (8.21ms).
     - `100.93.158.96` (macbook-1): ICMP 0% loss (RTT avg 7.29ms), Port 22 OPEN (7.60ms), Port 50052 OPEN (8.02ms).
     - `100.73.38.87` (pixel-10-pro-xl): ICMP 100% loss (Host unreachable / timed out). Ports 22, 8022, 50052 TIMED OUT.
     - `100.84.40.95` (aarons-s20-1): ICMP 100% loss. Ports 22, 8022, 50052 TIMED OUT.
     - `100.122.185.123` (gl-mt3600be): ICMP RTT 2540ms, Ports 22, 80, 443 OPEN (4.30 - 4.94ms).

4. **Movesense 128Hz UDP Streaming & DSCP EF (0xB8) QoS Benchmark**:
   - Loopback Benchmark (640 pkts / 5.0s): 640 sent, 640 received, 0 dropped (0.00% loss), Effective Rate: 127.96 Hz, Avg Latency: 0.084ms, RFC 3550 Jitter: 0.0176ms.
   - Physical LAN Interface Benchmark (`192.168.8.155`, 640 pkts / 5.0s): 640 sent, 640 received, 0 dropped (0.00% loss), Avg Latency: 0.178ms, RFC 3550 Jitter: 0.0321ms.
   - Adversarial Saturated Flood Test (1280 pkts / 10.0s under concurrent 4-thread max-MTU UDP background flood): 1280 sent, 1280 received, 0 dropped (0.00% loss), RFC 3550 Jitter: 0.2125ms, Zero drops verified.

---

## 2. Logic Chain

1. **Step 1 (Missing Files)**: The prompt and prior documentation claim that network benchmark results and TP-Link integration status are recorded in `data/network/benchmark_results.json` and `data/network/tplink_nomad_integration_status.json`. Direct filesystem interrogation proves these files do not exist (Observation 1).
2. **Step 2 (Simulated Speedup Violations)**: Inspection of `06_scripts_and_tooling/network/tensor_multipath_router.py` shows that the claimed `1.75x` bonded throughput is simulated via `time.sleep()`. This directly violates Monorepo Rule #0 (Zero Fake Data) and invalidates any performance claim derived from this script (Observation 2).
3. **Step 3 (Tailscale RPC Inconsistency)**: Probing demonstrates that `linux-1` is listening on Port 50052 on its local LAN interface `192.168.8.224` (5.90ms connect latency), but connections to `100.101.39.98:50052` time out. Any remote node attempting Tailscale-only RPC offloading to `linux-1` will fail (Observation 3).
4. **Step 4 (Mobile Node Inreachability)**: Both Android endpoints (`100.73.38.87` Pixel 10 Pro XL and `100.84.40.95` S20-1) are currently unreachable over Tailscale ICMP/SSH, preventing mobile mesh compute offloading (Observation 3).
5. **Step 5 (Empirical QoS Robustness)**: Telemetry streaming at 128Hz with DSCP EF (`0xB8` / TOS 184) was empirically proven to achieve 0 packet loss and sub-millisecond jitter even under saturated background traffic (Observation 4).

---

## 3. Caveats

1. **Physical TP-Link Extender Status**: The physical TP-Link Extender hardware operates as a transparent Layer-2 bridge / Wi-Fi extender in the local subnet. It does not expose a separate management IP unless configured with a static DHCP reservation (the primary gateway is `192.168.8.1`).
2. **Mobile Device Sleep**: The unreachability of `100.73.38.87` (Pixel 10 Pro XL) and `100.84.40.95` (S20-1) is typical for Android devices in deep doze or without Termux WakeLock active.

---

## 4. Conclusion

**Verdict**: **REJECT**.

**Required Remediations**:
1. Replace simulated `time.sleep()` logic in `06_scripts_and_tooling/network/tensor_multipath_router.py` with genuine socket striping across available interfaces (`en0`, `en1`, `bridge0`).
2. Generate genuine, empirical `data/network/benchmark_results.json` and `data/network/tplink_nomad_integration_status.json` from real socket and ping telemetry.
3. Configure `linux-1` (`100.101.39.98`) firewall / binding to allow incoming RPC on port 50052 via Tailscale.

---

## 5. Verification Method

To independently reproduce and verify these findings:
1. **Run Empirical Probe Harness**:
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/tests/test_challenger_tplink_nomad_empirical.py
   ```
2. **Inspect Empirical JSON Data**:
   ```bash
   cat /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/challenger_network/empirical_results.json
   ```
3. **Verify Non-Existence of Claimed Files**:
   ```bash
   ls -la /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/network/benchmark_results.json
   ls -la /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/network/tplink_nomad_integration_status.json
   ```
4. **Inspect Sleep Delays in Bonding Router**:
   ```bash
   sed -n '80,105p' /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/tensor_multipath_router.py
   ```
