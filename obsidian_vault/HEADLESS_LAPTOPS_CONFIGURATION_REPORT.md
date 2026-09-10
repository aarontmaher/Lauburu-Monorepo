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
| **MacBook Pro** (`macbook-pro`) | Intel Core i9 / M1 Max Vault, 16 GB RAM | • TS: `100.103.212.21`<br>• LAN: `192.168.8.127`<br>• TB4: `169.254.187.138` (0.27ms RTT) | `com.lauburu.headless`<br>(LaunchAgent `/usr/bin/caffeinate -dimsu`) | `sleep 0`, `displaysleep 0`, `disksleep 0`, `womp 1`, `networkoversleep 1`, `ttyskeepawake 1` |
| **MacBook Air** (`macbook-air`) | Apple M4, 16 GB Unified Memory | • TS: `100.121.202.34`<br>• LAN: `192.168.8.222` | `com.lauburu.headless`<br>(LaunchAgent `/usr/bin/caffeinate -dimsu` + `Amphetamine.app`) | `sleep 0`, `displaysleep 0`, `disksleep 0`, `womp 1`, `networkoversleep 1`, `ttyskeepawake 1` |
| **Linux Laptop** (`linux`) | Dell Inspiron 15 3525, AMD Ryzen 7 5700U | • TS: `100.101.39.98`<br>• LAN: `192.168.8.224` | `lauburu-headless-keepalive.service`<br>(`systemd-inhibit --what=sleep:idle:handle-lid-switch`) | `/etc/systemd/logind.conf.d/99-headless.conf`<br>Masked `sleep.target`, `suspend.target`, `hibernate.target` |

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