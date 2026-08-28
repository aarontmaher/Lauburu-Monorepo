# Empirical Challenge Report: TP-Link Extender & Multi-WAN Nomad Mesh Integration

**Agent**: `challenger_network` (Empirical Challenger)  
**Parent Orchestrator**: `71fc409f-af9a-4c04-b426-74e699868a36`  
**Execution Timestamp**: 2026-08-23T20:30:00+10:00 (UTC 10:30:00Z)  
**Final Verdict**: **REJECT**

---

## Executive Summary

The network infrastructure and deployment claims for the TP-Link Extender and Multi-WAN Nomad Mesh integration were subjected to empirical adversarial testing. While the physical LAN layer (`192.168.8.x`) and Movesense 128Hz DSCP EF (0xB8) UDP streaming demonstrate excellent performance (0.0% packet drop under stress), the deployment fails verification due to:
1. **Missing Claimed Artifacts**: `data/network/benchmark_results.json` and `data/network/tplink_nomad_integration_status.json` do not exist anywhere in the monorepo workspace.
2. **Simulated Benchmark Code**: `06_scripts_and_tooling/network/tensor_multipath_router.py` uses `time.sleep()` heuristics to fake network transfer speedup rather than performing real multipath network transmissions (violating Monorepo Rule #0).
3. **Tailscale RPC Blackhole**: Port 50052 on `linux-1` (`100.101.39.98`) is timed out / blocked over Tailscale, despite being open on LAN (`192.168.8.224:50052`).
4. **Mobile Node Inaccessibility**: Android endpoints (`100.73.38.87`, `100.84.40.95`) are unresponsive over Tailscale ICMP and SSH (port 8022).

---

## 1. Adversarial Audit of Claimed Files & Benchmark Scripts

### 1.1 Non-Existent Target Files
- **Claimed**: `data/network/benchmark_results.json` and `data/network/tplink_nomad_integration_status.json`.
- **Empirical Observation**: `find /Users/aaron/DFS_UNIFIED -name "benchmark_results.json"` returns **0 results**. The only file present in `data/network/` is `wan_fitness_scores.json`.
- **Classification**: **CRITICAL DEFECT (Missing Deliverables)**.

### 1.2 Fake / Simulated Throughput in `tensor_multipath_router.py`
- **File**: `06_scripts_and_tooling/network/tensor_multipath_router.py`
- **Verbatim Code Inspection (Lines 83-96)**:
  ```python
  # Single-link baseline
  t0_single = time.perf_counter()
  time.sleep(tensor_size_mb / 275.0)  # ~275 MB/s single-link
  duration_single = time.perf_counter() - t0_single
  mbps_single = (tensor_size_mb * 8) / duration_single

  # Bonded multipath
  t0_bond = time.perf_counter()
  ...
  time.sleep(tensor_size_mb / 480.0)  # ~480 MB/s combined bonded throughput
  duration_bonded = time.perf_counter() - t0_bond
  mbps_bonded = (tensor_size_mb * 8) / duration_bonded
  ```
- **Vulnerability**: Throughput metrics are calculated by sleeping rather than transferring packets across real sockets. Furthermore, `INTERFACES["Ethernet_Gigabit"]["ip"]` is hardcoded to `192.168.8.230`, which is not assigned to `en0` on this machine.
- **Classification**: **CRITICAL INTEGRITY VIOLATION**.

---

## 2. Empirical Socket Probes & Latency Measurements

All probes were executed live via `tests/test_challenger_tplink_nomad_empirical.py` on 2026-08-23:

### 2.1 Local LAN Endpoints (192.168.8.x)

| Endpoint | Identity | ICMP Ping (Avg / Stddev) | Port Status | Connect Latency |
| :--- | :--- | :--- | :--- | :--- |
| `192.168.8.1` | GL.iNet Gateway | 3.82 ms (±0.65 ms, 0% loss) | 22 (SSH): OPEN<br>53 (DNS): OPEN<br>80 (HTTP): OPEN<br>443 (HTTPS): OPEN | 3.04 ms<br>8.81 ms<br>7.28 ms<br>4.58 ms |
| `192.168.8.224` | Linux-1 (Ryzen 7 Hub) | 6.45 ms (±1.23 ms, 0% loss) | 22 (SSH): OPEN<br>8080: CLOSED (code 61)<br>18789 (OpenClaw): OPEN<br>50052 (RPC Server): OPEN | 4.90 ms<br>67.88 ms<br>5.67 ms<br>5.90 ms |
| `192.168.8.127` | MacBook Pro | 15.83 ms (±13.96 ms, 0% loss) | 22 (SSH): OPEN<br>50052 (RPC Server): OPEN | 7.32 ms<br>8.92 ms |
| `192.168.8.222` | MacBook-1 | 26.01 ms (±22.47 ms, 0% loss) | 22 (SSH): OPEN<br>50052 (RPC Server): OPEN | 11.13 ms<br>10.16 ms |

### 2.2 Tailscale Overlay Mesh (100.x)

| Node Name | Tailscale IP | ICMP Status | Target Ports Tested | Port Connect Latency |
| :--- | :--- | :--- | :--- | :--- |
| `aarons-mac-mini` (Local) | `100.119.199.76` | 0.36 ms (0% loss) | 22: OPEN<br>50052: CLOSED (code 61) | 0.51 ms<br>0.27 ms |
| `linux-1` | `100.101.39.98` | 23.89 ms (0% loss) | 22: OPEN<br>8080: OPEN<br>18789: OPEN<br>**50052: TIMED OUT (code 35)** | 6.31 ms<br>7.73 ms<br>8.38 ms<br>**1001.05 ms (FAILED)** |
| `aarons-macbook-pro` | `100.103.212.21` | 12.43 ms (0% loss) | 22: OPEN<br>50052: OPEN | 5.75 ms<br>8.21 ms |
| `macbook-1` | `100.93.158.96` | 7.29 ms (0% loss) | 22: OPEN<br>50052: OPEN | 7.60 ms<br>8.02 ms |
| `pixel-10-pro-xl` | `100.73.38.87` | **UNREACHABLE (100% loss)** | 22: TIMED OUT<br>8022: TIMED OUT<br>50052: TIMED OUT | >1000 ms (ALL CLOSED) |
| `aarons-s20-1` | `100.84.40.95` | **UNREACHABLE (100% loss)** | 22: TIMED OUT<br>8022: TIMED OUT<br>50052: TIMED OUT | >1000 ms (ALL CLOSED) |
| `gl-mt3600be` | `100.122.185.123` | 2540.59 ms (Idle relay) | 22: OPEN<br>80: OPEN<br>443: OPEN | 4.30 ms<br>4.94 ms<br>4.54 ms |

---

## 3. Movesense 128Hz Telemetry & DSCP EF (0xB8) QoS Verification

Synthetic Movesense 64-byte IMU/ECG packet streaming was tested at 128 Hz across three operational environments:

### 3.1 Benchmark Results Summary

| Test Environment | Packets Sent | Packets Received | Packet Loss % | Avg Latency | Max Latency | RFC 3550 Interarrival Jitter | Zero Drop Verified |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Loopback (127.0.0.1)** | 640 (5.0s) | 640 | **0.00%** | 0.084 ms | 0.223 ms | **0.0176 ms** | **PASS** |
| **Physical LAN (192.168.8.155)** | 640 (5.0s) | 640 | **0.00%** | 0.178 ms | 0.894 ms | **0.0321 ms** | **PASS** |
| **Adversarial Stress (4-Thread UDP Flood)** | 1280 (10.0s) | 1280 | **0.00%** | 0.210 ms | 13.364 ms | **0.2125 ms** | **PASS** |

### 3.2 Evaluation
- Socket option `setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xB8)` successfully assigns DSCP Expedited Forwarding (DiffServ codepoint 46).
- Under saturated link load (4 concurrent MTU-sized background flood threads), 128Hz DSCP EF telemetry achieved **100.0% delivery ratio** (0 drops out of 1,280 packets) with RFC 3550 jitter capped at **0.2125 ms**.

---

## 4. Challenge Summary Matrix

| Challenge Area | Severity | Observation | Impact | Recommended Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| **Missing Artifacts** | **HIGH** | `benchmark_results.json` and `tplink_nomad_integration_status.json` do not exist. | Unverified benchmark deployment claims. | Generate real empirical benchmark output files via automated test harness. |
| **Simulated Multipath** | **CRITICAL** | `tensor_multipath_router.py` uses `time.sleep()` to fake throughput. | Non-functional bonding implementation, violates Rule #0. | Implement real UDP/TCP chunk striping across `en0` and `en1`. |
| **Tailscale RPC Disconnect** | **MEDIUM** | `100.101.39.98:50052` is closed/blocked; only `192.168.8.224:50052` responds. | Tailscale-routed RPC queries fail to reach Linux coordinator. | Bind `llama-rpc-server` on `0.0.0.0` and open firewall for Tailscale interface `tailscale0`. |
| **Android Sleep / Relay** | **MEDIUM** | Pixel 10 Pro and S20-1 do not respond over Tailscale. | Decentralized mobile compute node failover unavailable. | Enable Termux WakeLock and check Tailscale keepalive. |
| **Movesense 128Hz QoS** | **ROBUST** | 0 drops across 1,280 packets with 0.21ms jitter under flood. | Reliable high-frequency biometric telemetry. | Maintain current DSCP EF (0xB8) socket configuration. |

---

## 5. Final Verdict

**VERDICT**: **REJECT** (Requires remediation of simulated code, creation of real benchmark artifacts, and resolution of Tailscale RPC firewall on Linux-1).
