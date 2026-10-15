---
title: "Lauburu 7-Layer Mesh — SSHD Persistence & Run-On-Boot Canonical Audit"
tags: [ssh, sshd, launchd, systemd, procd, mesh, security, empirical_proof]
created: 2026-10-02
---

# 🔒 Lauburu 7-Layer Mesh: SSHD Persistence & Run-On-Boot Architecture

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]

---

## 🏛️ 1. Executive Summary

This document verifies the end-to-end configuration, boot persistence, and automated watchdog architecture of the **OpenSSH Daemon (`sshd`)** and **Dropbear SSH** services across the entire physical 7-layer Lauburu Mesh Ecosystem.

### Problem Root Cause:
When executed manually on macOS via shell (`sshd`), the compiled Apple OpenSSH binary `/usr/sbin/sshd` halts with:
`sshd requires execution with an absolute path`
Furthermore, on macOS, `sshd` is architected as an on-demand socket-activated daemon governed by **Apple `launchd`** via `/System/Library/LaunchDaemons/ssh.plist` (`com.openssh.sshd`).

### Solution Implemented:
1. **Sovereign CLI Wrapper & Mesh Controller (`~/.local/bin/sshd`):**
   - High-precedence CLI in `$PATH` that intercepts interactive calls.
   - `sshd`: Outputs instant local host service status, port 22 socket latency, launchd boot persistence state, and active inbound/outbound SSH sessions.
   - `sshd mesh`: Audits and verifies port 22/8022 reachability, RTT, and service boot enablement across all 7 layers of the mesh.
   - `sshd [flags]`: Transparently passes daemon options (`-D`, `-d`, `-e`, `-p`, etc.) to `/usr/sbin/sshd` with the required absolute path.
   - Synchronized across macOS (`L1`, `L2`, `L5`) and Linux (`L3`, `L8`).
2. **System Service Boot Enablement:**
   - **L1 Mac Mini Host:** `launchctl system` domain has `"com.openssh.sshd" => enabled`.
   - **L2 MacBook Pro:** `launchctl system` domain has `"com.openssh.sshd" => enabled`.
   - **L2 MacBook Pro:** `launchctl system` domain has `"com.openssh.sshd" => enabled`.
   - **L3 Linux Head Node (Ryzen 7):** Both `ssh.service` and `ssh.socket` enabled in systemd (`multi-user.target.wants`).
   - **L8 Linux Mini (i7-8700B):** Both `ssh.service` and `ssh.socket` enabled in systemd (`multi-user.target.wants`).
   - **GW GL.iNet Gateway Router:** OpenWrt `dropbear` active and enabled on boot (`/etc/rc.d/S19dropbear`).
   - **L6 Pixel 10 Pro XL AVF MicroVM:** Debian 13 kernel microVM (`100.99.210.89:22`) active with systemd OpenSSH server.

---

## 📊 2. Empirical Tri-Proof Verification Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              LAUBURU MESH SSH PERSISTENCE MATRIX                                      │
├────────────────────┬─────────────────────────────┬──────────────────┬───────────┬────────┬─────────────┤
│ Node ID            │ Node Role                   │ Endpoint         │ Latency   │ Status │ Boot Daemon │
├────────────────────┼─────────────────────────────┼──────────────────┼───────────┼────────┼─────────────┤
│ L1_Mac_Host        │ Master Local Orchestrator   │ 127.0.0.1:22     │ 0.35 ms   │ OPEN   │ launchd     │
│ L2_MacBook_Pro     │ Metal GPU Vault & Storage   │ 100.103.212.21:22│ 3.49 ms   │ OPEN   │ launchd     │
│ L5_MacBook_Air     │ Secondary Metal Worker & LoRA│ 100.121.202.34:22│ 4.74 ms   │ OPEN   │ launchd     │
│ L3_Linux_Hub       │ Gateway Ingress & Compute   │ 100.101.39.98:22 │ 5.60 ms   │ OPEN   │ systemd     │
│ L8_Linux_Mini      │ Central Ingress & Services  │ 100.121.247.8:22 │ 1.47 ms   │ OPEN   │ systemd     │
│ GW_Router          │ Sovereign Gateway (OpenWrt) │ 192.168.8.1:22   │ 1.67 ms   │ OPEN   │ procd/rc.d  │
│ L6_Pixel_AVF       │ Tensor G5 Debian MicroVM    │ 100.99.210.89:22   │ 50.65 ms  │ OPEN   │ systemd     │
└────────────────────┴─────────────────────────────┴──────────────────┴───────────┴────────┴─────────────┘
```

---

## 🛠️ 3. Node-by-Node Boot Configuration Invariants

### 3.1 macOS Nodes (L1, L2, L5)
- **Plist Location:** `/System/Library/LaunchDaemons/ssh.plist`
- **Service Name:** `com.openssh.sshd`
- **Activation:** `launchctl enable system/com.openssh.sshd`
- **Launch Command:** `/usr/libexec/sshd-keygen-wrapper`
- **Power Management Invariant:** `pmset -g custom` configured with `sleep 0`, `womp 1` (Wake on Magic Packet), `ttyskeepawake 1`, and `networkoversleep 1` to prevent host sleep on AC power.

### 3.2 Linux Systemd Nodes (L3, L8)
- **Unit Files:** `/usr/lib/systemd/system/ssh.service` and `/usr/lib/systemd/system/ssh.socket`
- **Activation Symlink:** `/etc/systemd/system/multi-user.target.wants/ssh.service`
- **State Check:** `systemctl is-enabled ssh.service` returns `enabled`.

### 3.3 Gateway Router (GL-BE14000)
- **Init Script:** `/etc/init.d/dropbear`
- **Boot Runlevel:** `/etc/rc.d/S19dropbear -> ../init.d/dropbear`
- **Process:** `/usr/sbin/dropbear -F -P /var/run/dropbear.main.pid`

### 3.4 Android Edge Nodes (L6 Pixel, L7 S20)
- **Boot Trigger:** Termux:Boot app executes `~/.termux/boot/start-sshd.sh` on device boot.
- **Wake Lock:** `termux-wake-lock` maintains CPU execution state.
- **Doze Bypass:** `dumpsys deviceidle whitelist +com.termux` prevents OS phantom process termination.
