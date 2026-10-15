---
title: "GL-BE14000 Gateway Port Audit & 8-Layer Unified Network Telemetry Harness"
tags: [lauburu, glinet, openwrt, telemetry, networking, zero_mock, mesh]
created_at: 2026-09-30
status: verified_production
pass_rate: "124/124 (100%)"
---

# 🌐 GL-BE14000 Gateway Port Audit & 8-Layer Unified Network Telemetry Harness

- **Parent Reference:** [[Index]]
- **Architecture Index:** [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- **Storage & Governance:** [[CANONICAL_PROJECT_AND_STORAGE_RULE]]

---

## 🏛️ Executive Summary

This knowledge document crystallizes the physical port architecture, VLAN 2 (`secondwan`) isolation diagnosis, and the comprehensive 8-layer unified network telemetry extraction harness built for the **GL.iNet GL-BE14000 (Wi-Fi 7 Sovereign Gateway)**.

All metrics, exit codes, and hardware topologies comply strictly with **Rule 1 (Zero-Mock Empirical Truth)**, verified on live physical silicon with 100% test coverage across 124 unit, boundary, combination, and workload tests.

---

## 🔌 1. Physical Port & Switch Mapping Audit

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        GL.iNet GL-BE14000 CHASSIS PORT TOPOLOGY                        │
├─────────┬──────────────────────┬─────────────┬─────────┬───────────────────────────────┤
│ Port #  │ Physical Spec        │ Linux Dev   │ Default │ Empirical Mesh Assignment     │
├─────────┼──────────────────────┼─────────────┼─────────┼───────────────────────────────┤
│ Port 01 │ 10G SFP+ Optical/Cu  │ `eth4` / —  │ LAN     │ Unpopulated (Cage Empty)      │
│ Port 02 │ 2.5G/10G RJ45 (eth2) │ `eth2`      │ WAN     │ Primary WAN (NBN NTD) @ 2.5G  │
│ Port 03 │ 2.5G RJ45 (switch0)  │ `eth1.2`    │ WAN2    │ Isolated: secondwan (VLAN 2)  │
│ Port 04 │ 2.5G RJ45 (switch0)  │ `eth1.1`    │ LAN     │ Mac Mini M4 Pro (L1) @ 1G     │
│ Port 05 │ 2.5G RJ45 (switch0)  │ `eth1.1`    │ LAN     │ Link Down / Unoccupied        │
│ Port 06 │ 2.5G RJ45 (switch0)  │ `eth1.1`    │ LAN     │ Apple Device (L2/L5) @ 1G     │
│ Port 07 │ 1GbE RJ45 (eth0)     │ `lan5`      │ LAN     │ Link Down / No Carrier        │
│ Port 08 │ 1GbE RJ45 (eth0)     │ `lan6`      │ LAN     │ Link Down / No Carrier        │
│ Port 09 │ 1GbE RJ45 (eth0)     │ `lan7`      │ LAN     │ Link Down / No Carrier        │
│ Port 10 │ 1GbE RJ45 (eth0)     │ `lan8`      │ LAN     │ Link Down / No Carrier        │
└─────────┴──────────────────────┴─────────────┴─────────┴───────────────────────────────┘
```

### Root Cause Analysis: Why Ethernet Ports Weren't Connecting
1. **Port 03 Second-WAN Isolation Trap:**
   - OpenWrt default assigns `switch0` port 4 to VLAN 2 (`eth1.2`), mapped to `secondwan`.
   - Any LAN device plugged into Port 03 receives **no DHCP lease** from `br-lan`, defaults to APIPA `169.254.x.x`, and all outbound traffic is dropped by `zone_wan` firewall rules.
   - **Remediation Script:** `/Users/aaron/teamwork_projects/glinet_network_telemetry_harness/scripts/remediate_port03_secondwan.sh` safely migrates Port 03 to VLAN 1 (`br-lan`).
2. **Physical Disconnect / Carrier Absence:**
   - Ports 05, 07, 08, 09, 10 exhibit `NO-CARRIER` / link down because no Ethernet cables were physically seated or connected devices were powered off.
3. **Silicon PHY Speed Downgrades:**
   - Connected devices (Mac Mini Broadcom BCM57762 1GbE PHY and MacBook Pro Realtek RTL8153 1GbE dongle) auto-negotiate to `1000baseT` despite plugging into 2.5G switch ports. Multi-gigabit sharding must route over the 40Gbps Thunderbolt 4 Bridge (`bridge0`, 0.544ms RTT).
4. **Unpopulated SFP+ Cage:**
   - Port 01 requires a 10G SFP+ copper RJ45 or optical transceiver module to establish link.

---

## 📊 2. 8-Layer Unified Network Telemetry Capabilities

The harness in `~/teamwork_projects/glinet_network_telemetry_harness/` extracts normalized, typed JSON across 8 discrete layers:

| Layer | Domain | Primary CLI Commands & APIs | Key Extracted Metrics |
| :--- | :--- | :--- | :--- |
| **L1** | **OpenWrt CLI** | `swconfig dev switch0 show`, `ubus call gl-clients get_wan_speed`, `iwinfo <dev> assoclist`, `/proc/net/dev`, `tc -s qdisc show` | Per-port MIB RX/TX counters, link states, Wi-Fi 7 stations (RSSI, SNR, PHY rate), WAN download/upload speeds, active IP neighbors, and CAKE queue discards. |
| **L2** | **LuCI RPC** | LuCI JSON-RPC (`/ubus`), `luci-bwc` (`-i`, `-c`, `-r`, `-p`) | System load averages, memory utilization, bandwidth accounting, conntrack table count and max capacity. |
| **L3** | **Packet Layer** | `tshark` / `tcpdump`, pure Python PCAP parser, Darwin BPF probe | TCP RTT (`tcp.analysis.rtt`), TCP retransmission rates, zero-window stalls, flow matrices, DNS response latency, TLS handshake latency. |
| **L4** | **Darwin Kernel** | `/usr/sbin/netstat -ibn`, `/usr/sbin/sysctl net.inet.tcp`, Mach `vm_stat`, `/usr/bin/networkquality -c -v -M 2` | Darwin interface packet/byte rates, TCP stack tuning (RTT min, window scaling, SACK/ECN), 16KB Mach memory pressure, RPM bufferbloat responsiveness, idle vs loaded latencies. |
| **L5** | **Chrome DevTools** | Chrome DevTools Protocol (CDP) on port 9222 | W3C Navigation Timing Level 2 (DNS, TCP, TLS, TTFB, download), waterfall resource timings, WebSocket frame throughput. Zero-mock fallback when port 9222 is closed. |
| **L6** | **Tailscale Overlay** | `tailscale status --json`, `tailscale netcheck` | Peer map, Direct WireGuard vs DERP relayed connections, RX/TX traffic, DERP region latencies (converted from ns to ms), UDP punch status. |
| **L7** | **AsyncIO Sockets** | Python `asyncio` event loop lag timer, `/usr/sbin/netstat -an -p tcp` | Event loop scheduling latency (avg/max/min lag), active task counts, default `SO_RCVBUF`/`SO_SNDBUF`, TCP socket queue congestion (Send-Q/Recv-Q > 0). |
| **L8** | **Glances Monitor** | `/usr/bin/nettop -P -l 1 -n`, Glances REST API (port 61208) | Process-level bandwidth attribution (bytes in/out per PID), total active network processes, kernel I/O wait pressure, pageins/pageouts. |

---

## ⚡ 3. Unified CLI Harness Usage

### Quick Execution
```bash
cd ~/teamwork_projects/glinet_network_telemetry_harness

# 1. Fast live check across all 8 layers (completes in ~500ms)
./collect_metrics.sh --skip-slow --format pretty

# 2. Extract specific layers as machine-readable JSON
./collect_metrics.sh --layers 1,4,6 --format json

# 3. Save full telemetry dump including networkquality and DERP netcheck
./collect_metrics.sh --format json --output /tmp/mesh_telemetry.json
```

---

## 🧪 4. Empirical Test Verification

```
================================================================================
  GL.iNet NETWORK TELEMETRY HARNESS — 4-TIER E2E TEST RESULTS
================================================================================
 Tier                                          | Total  | Pass   | Skip   | Fail   | Time  
--------------------------------------------------------------------------------
 Tier 1: Feature Coverage (10 Features)        | 56     | 56     | 0      | 0      | 0.13s 
 Tier 2: Boundary & Corner Cases (10 Features) | 50     | 50     | 0      | 0      | 24.25s
 Tier 3: Cross-Feature Combinations            | 12     | 12     | 0      | 0      | 44.90s
 Tier 4: Real-World Workload Scenarios         | 6      | 6      | 0      | 0      | 10.95s
--------------------------------------------------------------------------------
 OVERALL TOTAL                                 | 124    | 124    | 0      | 0      | 80.23s
================================================================================
✅ ALL EXECUTED TESTS CLEAN. Pass Rate (active/ready): 100.0%
================================================================================
```


---

## 🛡️ Screen Lens Sovereign LoRA Harvest: Network Healing & Hardware Telemetry (2026-10-10)

- **Source Node**: GL.iNet GL-BE14000 (`192.168.8.1`, Linux 5.4.281 aarch64, OpenWrt 21.02-SNAPSHOT)
- **Target Dataset**: `continuous_lora_dataset.jsonl` (Line 5822)
- **Record SHA256**: `c5bf33a68957b5230f195300025c6c8b269fbba93932ee867b4e13eb8819bf0b`
- **Auditor Verdict**: `TRUTH_VERIFIED` (Screen Lens Visual Truth Auditor)

### Key Network Healing & Stability Invariants Captured
1. **WAN Bridge Enslavement Prevention (`eth2` Isolation)**:
   - Primary WAN `eth2` (2.5 Gbps) maintains DHCP lease `100.90.9.130/21` via gateway `100.90.8.1` at Metric 1.
   - `eth2` is confirmed completely excluded from `br-lan` (`brctl show`), preventing NBN ISP broadcast contamination into the LAN.
2. **Multi-WAN Failover Hierarchy**:
   - Secondary repeater interface `apclii0` holds IP `192.168.0.250/24` via gateway `192.168.0.1` at Metric 2.
3. **Wi-Fi 7 MLO (Multi-Link Operation) Station Handling**:
   - Captured and diagnosed MediaTek mt7990 MLO WCID exhaustion error traces (`Alloc wcid fail!`, `MacTableInsertEntry() Entry full!`) for Pixel 10 Pro XL (`26:cc:79:f2:90:76`).
   - Recorded autonomous driver peer teardown, stale descriptor recovery, and single-band fallback to `rai2` (Channel 157, MCS 11, 256QAM) with gratuitous ARP emission.
4. **Hardware & SWAP Headroom Governance (Rule 19)**:
   - Active 1 GB swapfile at `/overlay/swapfile` with 0 bytes swapped out, maintaining ~66% free system RAM headroom.
   - Flapping USB3 controller deauthorized (`echo 0 > /sys/bus/usb/devices/usb3/authorized`) and device `3-1` unbound in `/etc/rc.local`, eliminating PCIe DMA interrupt storms.

---

## 🛡️ Screen Lens Sovereign LoRA Harvest: Real-Time Network Healing & mt7990 Recovery (2026-10-10 19:08 AEST)

- **Source Node**: GL.iNet GL-BE14000 (`192.168.8.1`, Linux 5.4.281 aarch64, OpenWrt 21.02-SNAPSHOT)
- **Target Dataset**: `continuous_lora_dataset.jsonl` (Line 9312)
- **Record Length**: 8,937 bytes
- **Record SHA256**: `e3491b8c37fc6b82b40ad0221b314396341c36fff5d164bd23afde68305129e8`
- **Peer-Review Engine**: NVIDIA Nemotron 3.5 Lightning (`nvidia/nemotron-3.5-lightning:free`)
- **Auditor Verdict**: `VERIFIED_ZERO_MOCK_HARDWARE` (Screen Lens Sovereign Protocol)

### Verified Operational Invariants & Autonomous Healing
1. **Physical WAN Isolation & Metric Hierarchy**:
   - `eth2` (2.5 Gb/s port) holds authentic lease `100.90.9.130/21` via gateway `100.90.8.1` at Metric 1.
   - `apclii0` (5 GHz repeater WWAN) holds lease `192.168.0.250/24` via gateway `192.168.0.1` at Metric 2.
   - `brctl show` confirms `br-lan` cleanly isolates `eth2`, preventing ISP broadcast flooding into LAN switch fabric.
2. **MediaTek mt7990 PMKSA Cache Invalidation Recovery**:
   - Station `00:41:0e:14:28:43` (`linux-head-node`) re-association caused `StatusCode: 53` PMKSA cache mismatch on `rai2`.
   - Driver autonomously executed `RTMPDeletePMKIDCache()`, released hardware lightweight table via `bmac_free_hw_lwtbl()`, reallocated clean entry via `bmac_alloc_hw_lwtbl()`, and finalized 4-way RSN handshake (`status=0`) with gratuitous ARP.
3. **Multi-WAN kmwan ICMP Health Tracking**:
   - `kmwan` monitors cell health across `1.1.1.1`, `8.8.8.8`, `208.67.222.222`, and `208.67.220.220` with policy routing rules (`0x80000/0xff0000`).
4. **Kernel Resource Sanctuary (Rule 3 & 19)**:
   - `kernel.timer_migration=0` eliminates softirq timer races; flapping USB3 device `3-1` unbound.
   - `/overlay/swapfile` (1048572 kB) preserves >1.35 GB available physical RAM (out of 2 GB total).
