# 🌐 GL.iNet GL-BE14000 Physical Port Inversion & Topology Truth

## 1. Physical Hardware & Cable Mapping
Following physical ethernet cable swapping between the router ports:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               GL.iNet GL-BE14000 PHYSICAL PORT INVERSION TOPOLOGY           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. 🌐 WAN UPLINK (NBN Connection Box 2.5GbE)                                │
│    • Physical Port: WAN/LAN2 (Silk: WAN/LAN2, switch0 Port 0)               │
│    • Hardware PHY: Motorcomm YT92xx 2.5G Switch                             │
│    • Negotiated Speed: 2500baseT Full-Duplex (2.5 Gbps)                     │
│    • OpenWrt Device: eth1.3 (VLAN 3 on CPU trunk 5t)                        │
│    • Assigned Interface: 'wan' (DHCP, Metric 1)                             │
│    • Public / CGNAT IP: 100.90.9.130/21 | Gateway: 100.90.8.1               │
│    • DNS: 119.40.106.35, 119.40.106.36 (Aussie Broadband / Origin NBN)      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. 🖥️ LAN DOWNLINK (Mac Mini M4 Pro en0)                                    │
│    • Physical Port: WAN/LAN1 (Silk: WAN/LAN1, Direct SoC / RTL8261X PHY)   │
│    • Hardware PHY: Realtek RTL8261X 10Gbps Capable PHY                      │
│    • Negotiated Speed: 1000baseT Full-Duplex (1 Gbps Mac Mini en0 cap)      │
│    • OpenWrt Device: eth2 (Direct DSA member of br-lan bridge)              │
│    • Assigned Interface: 'lan' (Static: 192.168.8.1/24)                     │
│    • Mac Mini Host: 192.168.8.230 on en0                                    │
│    • Measured Round-Trip Time (RTT): 0.752 - 0.780 ms (0.0% packet loss)    │
│    • Verified Egress Bandwidth: 55,017,908 B/s (440.14 Mbps)                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Tri-Proof Verification Gate (Rule 5)

### Proof 1 (Actuation)
- **Ping Latency:** `ping -c 3 -t 2 192.168.8.1` from Mac Mini `en0`:
  `round-trip min/avg/max/stddev = 0.752/0.766/0.780/0.014 ms` (Exit Code 0).
- **Download Egress Throughput:** `curl --interface en0 "https://speed.cloudflare.com/__down?bytes=50000000"`:
  `55,017,908 bytes/sec (440.14 Mbps), Time: 0.908s` (Exit Code 0).
- **Cloudflare Edge Trace:** `curl -s --interface en0 https://1.1.1.1/cdn-cgi/trace`:
  `ip=203.132.68.30, colo=MEL, loc=AU` (Exit Code 0).

### Proof 2 (Line-by-Line & System State)
- **Mac Mini Silicon Controller:** Broadcom 57762-A0 (`14e4:1682`), PCIe Link Speed 2.5 GT/s x1, Driver `AppleBCM5701Ethernet`, Max Link Speed 1 Gb/s.
- **Router Kernel Devices:**
  - `eth1.3`: `inet 100.90.9.130/21 scope global eth1.3`
  - `eth2`: `master br-lan state UP`
  - `br-lan`: `inet 192.168.8.1/24 scope global br-lan`
  - Routing priority: `default via 100.90.8.1 dev eth1.3 metric 1` > `default via 10.178.49.221 dev usb1 metric 2`.
