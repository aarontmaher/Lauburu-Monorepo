---
title: "Device Roles & OpenWrt / GL.iNet Router Infrastructure Optimization"
tags: [device_roles, openwrt, glinet, luci, uci, sqm_cake, wifi7, pixel, samsung, mesh]
---

# 📱 Device Roles & OpenWrt / GL.iNet Router Infrastructure Optimization

## 1. Physical Device Role Specialization

The Lauburu Mesh assigns distinct operational constraints based on physical hardware roles:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            DEVICE ROLE SPECIALIZATION & POLICY MATRIX                                       │
├─────────────────────────┬──────────────────────────────────────────┬────────────────────────────────────────┤
│ Physical Device         │ Specialized Hardware Role                │ Strict Operational Governance Policy   │
├─────────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────┤
│ **Pixel 10 Pro XL (L6)**│ **Personal Daily Driver & Vision Sensor**│ • Non-disruptive compute policy        │
│                         │ • Google Tensor G5 Edge TPU (16GB)       │ • Zero battery degradation ($<1.5\%$/h)│
│                         │ • 8K Digital PTZ Video Streaming         │ • Heavy compute triggers ONLY on AC    │
├─────────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────┤
│ **Samsung S20+ (L7)**   │ **Dedicated Router Infrastructure Node** │ • 24/7 Persistent USB ADB Tethering    │
│                         │ • Permanent co-processor to GL.iNet      │ • Battery protected (capped at 80%)    │
│                         │ • OpenWrt, LuCI, UCI & CAKE SQM daemon   │ • 24/7 Wakelock via `termux-wake-lock` │
├─────────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────┤
│ **GL.iNet MT3600BE (GW)**│ **Core Gateway & Hardware USB Bridge**   │ • Hardware NAT offloading              │
│                         │ • Wi-Fi 7 MLO (802.11be EHT160)          │ • CAKE SQM bufferbloat control         │
│                         │ • SmolLM2-135M Sentinel Daemon (:18802)  │ • Gigabit USB ADB Ethernet bridging    │
└─────────────────────────┴──────────────────────────────────────────┴────────────────────────────────────────┘
```

---

## 2. Samsung S20+ OpenWrt & Routing Competencies

The Samsung S20+ acts as an autonomous co-pilot for the GL.iNet router, executing automated UCI scripts:

1. **Smart Queue Management (CAKE SQM):**
   - Configures `/etc/config/sqm` with `layer_cake.qos` to eliminate upstream/downstream bufferbloat under heavy AI model transfers.
2. **Wi-Fi 7 MLO & Band Steering:**
   - Dynamically monitors 2.4GHz, 5GHz, and 6GHz channels in `/etc/config/wireless`, switching frequencies during radar DFS events.
3. **Multi-WAN Load Balancing (MWAN3):**
   - Manages automatic failover between broadband ISP, Wi-Fi WAN, and emergency mobile hotspot.
4. **USB RNDIS0 Gigabit Gateway:**
   - Bridges Termux Python microservices directly into the `192.168.8.0/24` subnet over high-speed USB bus.

---
- Links: [[Index]] | [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]] | [[02_PRIMA_CPP_FULL_NETWORK_SHARDING]]
