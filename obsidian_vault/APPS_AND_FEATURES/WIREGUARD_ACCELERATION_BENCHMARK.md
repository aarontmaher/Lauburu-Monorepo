# ⚡ WireGuard & Tailscale Mesh Acceleration Benchmark (Generation 33)

## 🌐 Empirical Pairwise Latency & Routing Matrix

| Source Node | Target Node | Transport Interface | Protocol / Port | RTT (P50) | Link Type | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1 Mac Mini** | **GW GL.iNet Router** | tailscale0 / eth2 | WireGuard UDP 41641 | **1.0 ms** | Direct P2P LAN | ✅ VERIFIED |
| **L1 Mac Mini** | **L8 Linux Mini** | tailscale0 / lan | WireGuard UDP 41641 | **2.0 ms** | Direct P2P LAN | ✅ VERIFIED |
| **L1 Mac Mini** | **L3 Linux Head Node** | tailscale0 / wlp2s0 | WireGuard UDP 41641 | **3.0 - 5.0 ms** | Direct P2P LAN (Fixed wg0 route) | ✅ VERIFIED |
| **L1 Mac Mini** | **L6 Pixel 10 Pro XL** | wgserver (10.1.0.2) | WireGuard UDP 51820 | **7.6 ms** | Direct Kernel WG Tunnel | ✅ VERIFIED |
| **L1 Mac Mini** | **L7 Samsung S20+** | tailscale0 / wlan0 | WireGuard UDP 41578 | **12.0 ms** | Direct P2P LAN (Anti-Doze) | ✅ VERIFIED |
| **L1 Mac Mini** | **L2 MacBook Pro** | tailscale0 / bridge0 | WireGuard UDP 41641 | **34.0 ms** | Direct P2P LAN | ✅ VERIFIED |
| **L1 Mac Mini** | **L2 MacBook Pro** | LAN 192.168.8.215 | SSH Port 22 | **2.5 ms** | Direct Wi-Fi 7 / LAN | ✅ VERIFIED |

## 🛠️ Root Cause Diagnoses & Empirical Interventions

1. **L3 Linux Head Node DERP Elimination:**
   - **Root Cause:** A conflicting legacy route `192.168.8.0/24 dev wg0` was blackholing all outbound LAN subnet packets on L3 into an inactive WireGuard peer, forcing Tailscale to fall back to the Sydney DERP relay (78ms).
   - **Fix:** Removed the blackhole route via `sudo ip route del 192.168.8.0/24 dev wg0`, restoring physical `wlp2s0` Wi-Fi routing and dropping latency from 78ms to **3-5ms direct**.

2. **Router MTU & TCP MSS Clamping:**
   - **Fix:** Added dynamic TCP MSS clamping on GL.iNet router (`iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu`) preventing SSH banner exchange hangs on encapsulated WireGuard packets.

3. **Android 24/7 Anti-Doze & WireGuard Keepalives:**
   - **Fix:** Injected `dumpsys deviceidle whitelist +com.wireguard.android` and `+com.tailscale.ipn`, set AppOps `RUN_IN_BACKGROUND allow`, and verified 25-second persistent keepalives to prevent NAT table expiration.

4. **Universal SSH Verification Across All Nodes:**
   - All 7 remote hardware compute nodes (GW Router, L2 MBP, L3 Linux Hub, L8 Linux Mini, L6 Pixel 10, L7 Samsung S20, L5 MBA) verified responding to SSH commands with **Exit Code 0**.
