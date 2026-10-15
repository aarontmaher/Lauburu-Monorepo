---
title: "TP-Link AX USB Wi-Fi Extender Provisioning Status"
date: "2026-09-14"
tags: [tplink, linuxmini, wifi, mesh, zero_mock, physical_hardware]
---

# 📶 TP-Link 802.11ax Wi-Fi Extender Provisioning Status (Empirical Tri-Proof)

## 📊 1. Hardware & Driver Verification (Rule #1)
- **Host Device:** Linux Mini (`lauburu` - Intel Mac Mini 2018, 32 GB RAM)
- **USB Hardware ID:** `Bus 002 Device 004: ID 2357:013f TP-Link 802.11ax WLAN Adapter`
- **Underlying Chipset:** Realtek RTL8852AU (Wi-Fi 6 AX)
- **Kernel Driver:** `rtw89_8852au_git.ko` + `rtw89_usb_git.ko` + `rtw89_core_git.ko` on Linux 6.8.0-41-generic
- **Power Keepalive Config:** `/etc/modprobe.d/rtw89.conf` (`disable_ps_mode=Y`)

## 🌐 2. Multi-Transport Network Addressing
| Interface | MAC Address | IP Address | Metric | State | Link / SSID |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Wi-Fi (`wlx6c4cbcdbf030`)** | `6c:4c:bc:db:f0:30` | `192.168.8.184/24` | 200 | **UP (CONNECTED)** | `GL-MT3600BE-a0f 2.4` (-5 dBm, 286.7 Mbps) |
| **Ethernet (`enp4s0`)** | `3c:cd:36:68:29:e8` | `192.168.8.238/24` | 100 | **UP** | 1000 Mbps Full Duplex (Optional) |
| **Thunderbolt 3 (`thunderbolt0`)** | `12:82:a3:9e:ae:71` | `192.168.2.3/24` / `fe80::1082:a3ff:fe9e:ae71%bridge0` | -- | **UP** | 20 Gb/s PHY DMA Bridge |
| **Tailscale (`tailscale0`)** | -- | `100.115.233.33` | -- | **UP** | WireGuard Mesh Overlay |

## 🛠️ 3. Netplan Configuration (`/etc/netplan/02-wifi-tplink.yaml`)
```yaml
network:
  version: 2
  renderer: networkd
  wifis:
    wlx6c4cbcdbf030:
      dhcp4: true
      dhcp4-overrides:
        route-metric: 200
      optional: true
      access-points:
        "GL-MT3600BE-a0f":
          password: "goldfighting1"
        "GL-MT3600BE-a0f 2.4":
          password: "goldfighting1"
```

## ⚡ 4. Local AI Service Verification
- **Port 8083 (Qwen 3.8 Max 27B Abliterated):** `http://192.168.8.184:8083/health` ➔ `{"status":"ok"}`
- **Continuous 10M Genetic Drafter Trainer:** `active (running)` (PID 821)
- **WAN Egress:** `1.1.1.1` ping 13.0 ms RTT, `https://cloudflare.com` HTTP/2 301 verified.

## Tailscale Mesh Integration Update (2026-09-14)
- **Tailnet Account:** `aaron.t.maher@gmail.com`
- **Tailscale Hostname:** `lauburu`
- **Tailscale IP:** `100.121.247.8`
- **SSH Alias:** `ssh linuxmini-ts`
- **Empirical Link State:**
  - Wi-Fi 6 (802.11ax) on `wlx6c4cbcdbf030`: 5 GHz (Ch 44, 80MHz)
  - Bitrate: `1200.9 MBit/s HE-MCS 11`
  - Signal: `-14 dBm`
  - Zero-mock verified ping & SSH: `Exit Code 0`

## Definitive E2E Proof Log (2026-09-14)
- **Ethernet Cable State:** Physically disconnected (`enp4s0 DOWN`)
- **Wireless Interface:** `wlx6c4cbcdbf030` UP on `192.168.8.184/24`
- **Tailscale WireGuard:** Connected to `aaron.t.maher@gmail.com` on `100.121.247.8`
- **Link Layer:** 5 GHz Ch 44, 80 MHz, signal `-14 dBm` to `-18 dBm`, bitrate `1200.9 MBit/s`
- **Throughput Test (20 MB payload):**
  - Local Wi-Fi: `343.45 Mbps` (`40.94 MB/s`, `0.49 s`, `Exit Code 0`)
  - Tailscale WireGuard: `118.00 Mbps` (`14.07 MB/s`, `1.42 s`, `Exit Code 0`)
- **Visual Proof Asset:** `tailscale_linuxmini_e2e_proof.png` (SHA256: `317b9cf9e6a0b071c3faaa308931d149b3e9f28a57a5663333cbc48cb16fb401`)
