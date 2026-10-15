---
title: "Lauburu Mesh: Headless Laptop Fleet Configuration & Verification"
tags: [mesh, headless, hardware, power_management, clamshell, obsidian_canonical]
updated: "2026-09-03T02:52:00+10:00"
truth_audited: true
audit_swarm_verified: "2026-09-03"
audit_swarm_engine: "local_llamacpp_rpc+cloud_frontier"
mesh_topology_version: "8-node-verified"
canonical_source: true
---

# 💻 Lauburu Mesh: Headless Laptop Fleet Setup

All 3 laptops across the Lauburu 7-Layer Mesh have been configured for **100% headless, zero-sleep, lid-closed (clamshell) operation**. You can close their lids and put them away immediately without any interruption to remote SSH, AI model sharding, background daemons, or telemetry sync.

---

## 📋 Configured Laptop Fleet Matrix

| Laptop Node | Hardware Specs | IP Endpoints & Routing | Headless Daemon / Service | Power & Sleep Invariants |
| :--- | :--- | :--- | :--- | :--- |
| **MacBook Pro** (`macbook-pro` L2) | Intel Core i7-9750H (x86_64), 16 GB RAM | • TS: `100.103.212.21`<br>• LAN: `192.168.8.127`<br>• TB: Unlinked (LAN Wi-Fi 5 ~6.5ms RTT) | `com.lauburu.headless`<br>(LaunchAgent `/usr/bin/caffeinate -dimsu`) | `sleep 0`, `displaysleep 0`, `disksleep 0`, `womp 1`, `networkoversleep 1`, `ttyskeepawake 1` |
| **MacBook Air** (`macbook-air` L1a/L5) | Apple M4 (4P+6E cores), 16 GB Unified Memory | • TS: `100.121.202.34`<br>• LAN: `192.168.8.248` (Glances :61208) | `com.lauburu.headless`<br>(LaunchAgent `/usr/bin/caffeinate -dimsu` + `Amphetamine.app`) | `sleep 0`, `displaysleep 0`, `disksleep 0`, `womp 1`, `networkoversleep 1`, `ttyskeepawake 1` |
| **Linux Head Node** (`linux` L3) | AMD Ryzen 7 5700U, 15 GB RAM, Ubuntu Linux | • TS: `100.101.39.98`<br>• LAN: `192.168.8.225`<br>• BT: Paired to L1 (-28 dBm) | `lauburu-headless-keepalive.service`<br>(`systemd-inhibit --what=sleep:idle:handle-lid-switch`) | `/etc/systemd/logind.conf.d/99-headless.conf`<br>Masked `sleep.target`, `suspend.target`, `hibernate.target` |

---

## 🔒 Verification & Invariants Applied

1. **Darwin Clamshell Protection (`macbook-pro`, `macbook-air`):**
   - Persistent LaunchAgents loaded with `KeepAlive: true` and `RunAtLoad: true`.
   - Continuous kernel and user-level sleep prevention assertions held (`PreventSystemSleep`, `PreventUserIdleSystemSleep`, `PreventUserIdleDisplaySleep`).
   - Network wake and TCP keepalive assertions prevent interface tear-down on lid close.

2. **Linux Systemd Masking & Logind Configuration (`linux`):**
   - `HandleLidSwitch=ignore`, `HandleLidSwitchExternalPower=ignore`, `HandleLidSwitchDocked=ignore` active in `systemd-logind`.
   - `systemd-inhibit` system service blocking idle and lid sleep events indefinitely.
   - All standard sleep targets masked at the systemd root level.

3. **SSH Orchestration Configured:**
   - Host `~/.ssh/config` updated with verified direct and Tailscale IP endpoints.
   - Passwordless ed25519 authentication verified across all nodes.