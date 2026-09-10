---
title: "Tailscale Embedded tsnet (No-VPN P2P) & TP-Link Router Integration Architecture"
tags: [lauburu, tailscale, tsnet, no_vpn, tplink, openwrt, p2p_sharding, ai_gateway]
date: "2026-09-03"
---

# 🌐 Tailscale Embedded tsnet (No-VPN P2P) & TP-Link Router Integration

## 1. Tailscale Embedded Networking Without OS VPN (`tsnet`)
Tailscale open-sourced **`tsnet`**, a pure Go library that embeds Tailscale mesh connectivity directly inside application binaries:
- **Zero OS VPN Interface:** Does not create `utun` / `tun0` virtual network adapters.
- **Zero Root / Admin Permissions:** Runs entirely in unprivileged userspace.
- **Embedded Node Identity:** Each application microservice (e.g. `llama.cpp` shard, Axum WebSocket server, Python worker) joins the mesh directly with its own private WireGuard key, Tailscale IP, and automatic Let's Encrypt TLS certificate.
- **AI Sharding Advantage:** Tensor RPC streams can route directly application-to-application over WireGuard NAT traversal without kernel network stack context switching.

## 2. Tailscale Aperture (AI Agent Mesh Gateway)
Tailscale introduced **Aperture**, an open-source proxy and access control gateway specifically designed for AI agents and distributed model clusters:
- Governs P2P RPC sharding without exposing public ingress.
- Mutual TLS and cryptographic identity verification between agent clusters.

## 3. TP-Link Router Tailscale Integration Matrix
Can a TP-Link router run Tailscale?
1. **Flushed with OpenWrt / DD-WRT (Native Tailscale):**
   - Supported models (Archer C7, AX20, AX50, TL-WR902AC) can run Tailscale directly:
   ```bash
   opkg update
   opkg install tailscale iptables kmod-tun
   /etc/init.d/tailscale enable && /etc/init.d/tailscale start
   tailscale up --hostname=tp-router --advertise-routes=192.168.0.0/24
   ```
2. **Stock TP-Link Firmware (Subnet Routing via GL.iNet Gateway):**
   - If running stock TP-Link firmware, the TP-Link router is seamlessly integrated by using the `gl-router` (`100.122.185.123`) or `linux` node (`100.101.39.98`) as a **Tailscale Subnet Router** (`--advertise-routes=192.168.8.0/24`). All devices connected to the TP-Link bridge communicate with the mesh without needing any software installed on the TP-Link router itself.
