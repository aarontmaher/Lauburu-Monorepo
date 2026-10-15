# 🌐 GL.iNet GL-BE14000 Router Telemetry & Network Healing Distillation (Screen Lens Sovereign)

- **Date:** 2026-10-10
- **Node Identifier:** `GW` (GL.iNet GL-BE14000, OpenWrt 21.02-SNAPSHOT, GL fw v4.9.2)
- **Primary IP:** `192.168.8.1`
- **Dataset File:** `[[lora_datasets/continuous_lora_dataset.jsonl]]` (Line 13084)
- **Protocol:** Screen Lens Sovereign Teacher-Student Telemetry Distillation (Rule 0, 1, 2, 5)

---

## 1. Physical Silcon & Interface Topology

| Interface | Physical Link | IP Address / Mask | Gateway / Nexthop | Metric | Role & Status |
|:---|:---|:---|:---|:---:|:---|
| `eth2` | 2.5 Gbps PHY (NBN NTD) | `100.90.9.130/21` | `100.90.8.1` | **1** | **Primary WAN** (Active, Uptime > 579,000s) |
| `apclii0` | 5GHz Wi-Fi 7 STA | `192.168.0.250/24` | `192.168.0.1` | **2** | **Secondary Fallback WAN** (`TP-Link_Guest_5FAC_5G`) |
| `br-lan` | Switch Fabric & Wi-Fi | `192.168.8.1/24` | — | — | Local LAN (`eth1.1`, `lan5`-`lan8`, `ra0`, `rai0`, `rax0`, etc.) |
| `br-iot` | Isolated IoT VAP | `192.168.10.1/24` | — | — | Isolated IoT Bridge (`rai3`) |
| `tailscale0` | WireGuard Tunnel | `100.70.123.123/32`| `100.64.0.0/10` | — | Mesh Control Plane Overlay |

---

## 2. Kernel & System Telemetry

- **Kernel Release:** Linux 5.4.281 aarch64 (SMP)
- **System Memory:** 2,034,060 kB total (~1.3 GB available)
- **SWAP Space:** 1,048,572 kB active (`/overlay/swapfile`, priority -2, 0 kB used)
- **System Load:** 1.02, 1.01, 1.03 | Uptime: 7 days, 9 hours, 48 minutes

---

## 3. Network Self-Healing Mechanics & Invariants

1. **Bridge Segregation Invariant:**
   - `eth2` (2.5G WAN) is strictly excluded from `br-lan`.
   - Remediates historical defect where `/etc/rc.local` executed `brctl addif br-lan eth2`, preventing carrier packet contamination and DHCP collisions on the local switch fabric.
2. **Deterministic Multi-WAN Failover:**
   - Metric 1 assigned to `eth2` guarantees low-latency wired routing (12ms RTT).
   - Metric 2 assigned to `apclii0` guarantees instant wireless failover if `eth2` drops.
3. **Continuous DHCP Leasetime Management:**
   - Upstream NBN NTD enforces 600s leases.
   - `udhcpc` executes unicast renewals to `100.100.176.1`, failing over safely to broadcast renews to ensure zero lease expiration or IP revocation.
4. **kmwan Health Probing:**
   - Real-time Anycast ICMP tracking across `1.1.1.1`, `8.8.8.8`, `208.67.222.222`, `208.67.220.220`.

---

## 4. Unsloth / QLoRA SFT Dataset Record

- **Record SHA256 (2026-10-10):** `5f894d2a98530e0fd1f0a9eb8d42e337f3da963b87d9f6ea41d2f3d7b6605dca` (Line 13084)
- **Record SHA256 (2026-10-12):** `6b9ceb2fa70a4f42a910453087956cec83409e1e07a7ca4acd15e6f81efced75`
  - **Dataset File:** `[[lora_datasets/continuous_lora_dataset.jsonl]]` (Line 66604)
  - **Record Byte Count:** 19,097 bytes
  - **Source:** `screen_lens_sovereign_router_telemetry`
  - **Domain:** `network_healing_mechanics`
  - **Observed Healing:** Motorcomm `yt92xx` port 0 link recovery (100Mbps), `udhcpc` unicast-to-broadcast renewal fallback (`100.90.9.130/21`), `mt_wifi` 6GHz `rax2` MLME fast roam with PMKID cache hit & GARP bridge healing, and WebSocket auto-reconnect backoff (5.0s).
  - **Quality Score:** `1.0` | **Zero-Mock Verified:** `true`
  - **Visual Truth Verdict:** `TRUTH_VERIFIED`

