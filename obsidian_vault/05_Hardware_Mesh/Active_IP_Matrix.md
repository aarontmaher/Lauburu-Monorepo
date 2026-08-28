---
truth_audited: true
audit_swarm_verified: "2026-08-28"
audit_swarm_engine: "local_llamacpp_rpc+cloud_frontier"
mesh_topology_version: "8-node-verified"
canonical_source: true
---

# 🌐 Lauburu 8-Node Physical Mesh Active IP & Hardware Matrix

| Layer | Node Name | Network Role | Local IP | Tailscale / Bridge IP | RAM / AI Cap | Key Roles & Protocols |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Primary Host & Memory Governor | `192.168.8.230` | `100.119.199.76` | 24.0 GB (21.6 GB AI) | Apple M4 Pro Mac Mini. Dynamic Cap: 90%. |
| **L2** | `MacBook_Pro` | Metal GPU RPC & Storage Vault | `192.168.8.127` | `100.103.212.21` (TB4: `169.254.187.138`) | 16.0 GB (14.0 GB AI) | 10Gbps Thunderbolt 4 Bridge (0.277ms RTT). |
| **L3** | `Linux_Head_Node` | Gateway Ingress & Compute Hub | `192.168.8.224` | `100.101.39.98` | 16.0 GB (13.8 GB AI) | AMD Ryzen 7 5700U, Docker Hub. |
| **L4** | `Linux_Tablet` | Mobile Linux Compute & Touch DSP | DHCP | `100.81.92.125` | 8.0 GB (6.5 GB AI) | Debian Linux Tablet, secondary Petals worker. |
| **L5** | `MacBook_Air` | Secondary High-Speed Metal Worker | `192.168.8.222` | `100.93.158.96` | 16.0 GB (14.0 GB AI) | Apple M4 MacBook Air, Metal Performance Shaders. |
| **L6** | `Pixel_10_Pro_XL` | 8K Vision Stream & Edge TPU | DHCP | `100.73.38.87` (USB: `169.254.60.151`) | 16.0 GB (12.5 GB AI) | Google Tensor G5, Edge TPU, 8K Digital PTZ. |
| **L7** | `Samsung_S20` | Dedicated Router Internet Source & OpenClaw | `192.168.8.135` | `100.84.40.95` (USB: `rndis0` / `10.183.224.166`) | 12.0 GB (9.0 GB AI) | Samsung Exynos 990, 24/7 USB Router Gateway, Protect Battery: 85%. |
| **GW** | `GL.iNet Router` | Core Gateway & Hardware USB Bridge | `192.168.8.1` | `100.122.185.123` | Embedded | SSID: GL-MT3600BE-a0f-MLO. Hardware USB ADB daemon. |
