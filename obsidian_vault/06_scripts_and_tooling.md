---
title: "06_scripts_and_tooling — Network Healing, Mount Automations & ADB Daemons"
updated: "2026-08-27"
tags: [scripts, tooling, ssh, adb, wake_on_lan, self_healing, expect, spec-06]
---

# 06_scripts_and_tooling — Network Healing, Mount Automations & ADB Daemons

## 📋 Scope & Operational Tooling
Houses battle-tested automation scripts, network self-healing sequences, remote keepalive daemons, and hardware management utilities.

## 🛠️ Core Tooling & Automations
1. **Universal Multi-Transport SSH Daemons:**
   - Zero-latency remote execution across macOS, Linux, Android/Termux, and GL.iNet OpenWrt router.
2. **ADB Hardware Lifecycle & Keepalive:**
   - Automated wireless ADB pairing (Port 5555), battery optimization bypass, and Termux `termux-wake-lock` keepalives.
3. **Wake-on-LAN (WoL) Resurrection Engine:**
   - Dispatches RFC 792 Magic Packets (UDP Ports 7 & 9) via the Port 18802 REST API to awaken sleeping mesh hardware nodes.
4. **Expect Script Automation (`06_scripts_and_tooling/exp/`):**
   - Non-interactive SSH, Samba, and ADB connection handlers for headless environments.
5. **Global Storage Automations:**
   - `global_mesh_mount.sh`: Canonical Gen 31 multi-node storage orchestrator establishing verified SeaweedFS POSIX FUSE mounts (`weed mount`) on Linux nodes (L3, L8), APFS master validation on L1, and authenticated WebDAV (`rclone`) on macOS and Android Termux edge devices (L5, L6, L7, GW). Supports `--mount`, `--status`, and single-node targeting. See [[CANONICAL_NETWORK_STORAGE_STRUCTURE]].

## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-06-tooling-healing`
- **Focus Areas:** Idempotent shell scripting, ADB orchestration, WoL daemons, self-healing network monitors.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Mesh Governance:** [[swarm]], [[multi-wan-accelerator]]
- **Connected Modules:** [[00_core_infrastructure]], [[11_security_and_governance]]
