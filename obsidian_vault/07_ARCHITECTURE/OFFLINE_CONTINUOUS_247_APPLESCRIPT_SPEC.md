---
title: "Lauburu Mesh: Offline Continuous 24/7 AppleScript & Launchd Swarm Specification"
tags: [applescript, launchd, offline, continuous_training, 10m_drafter, swarm_loop, zero_mock]
created: "2026-09-06T05:04:00Z"
status: "PRODUCTION_VERIFIED"
---

# 🍎 Lauburu Mesh: Offline Continuous 24/7 AppleScript & Launchd Architecture

This specification formalizes the **100% Offline Continuous 24/7 Execution Architecture** for the Lauburu Mesh, combining native macOS AppleScript automation, a POSIX self-healing watchdog daemon, and a `launchd` LaunchAgent for autonomous restart resilience across the primary Mac Mini M4 Pro host.

---

## 🏛️ 1. Architecture Overview & Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    24/7 OFFLINE CONTINUOUS ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. NATIVE APPLESCRIPT CONTROLLER                                            │
│    • Path: 06_scripts_and_tooling/automation/                              │
│      ├── lauburu_offline_continuous_manager.applescript (Source)            │
│      └── lauburu_offline_continuous_manager.scpt (Compiled Binary)          │
│    • Role: Native macOS UI modal & CLI dispatcher with native notifications │
│    • Execution: osascript ... {start|stop|restart|status} or GUI dialogs    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. POSIX SELF-HEALING WATCHDOG DAEMON                                       │
│    • Path: 06_scripts_and_tooling/automation/                              │
│      └── lauburu_offline_continuous_daemon.sh (Executable 0755)             │
│    • Role: Manages 'caffeinate -dimsu' system wake-lock, process PIDs,      │
│      auto-resurrects fallen worker daemons, and enforces RAM headroom.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. MACOS LAUNCHD REBOOT PERSISTENCE                                         │
│    • Path: ~/Library/LaunchAgents/com.lauburu.offline-continuous-247.plist   │
│    • Role: Automatically starts watchdog on macOS boot / login.             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. LOCAL WORKERS (100% OFFLINE CAPABLE)                                     │
│    • 10M Drafter: continuous_10m_genetic_drafter_trainer.py                 │
│      (HOST_CPU_NEURAL_ALU, scaled logits 1/sqrt(d_model), Medusa tree)     │
│    • Swarm Loop: continuous_self_evolving_swarm_loop.py                     │
│      (DPO harvester, local AST validator, generational handoffs)            │
│    • Local Model Server: llama-server on Port 8081 (Qwen 2.5 Coder 7B)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 2. Quick Command Reference

### A. Via AppleScript (Recommended)
```bash
# Check status via compiled AppleScript
osascript /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/lauburu_offline_continuous_manager.scpt status

# Start all continuous daemons with wake-lock
osascript /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/lauburu_offline_continuous_manager.scpt start

# Stop all continuous daemons
osascript /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/lauburu_offline_continuous_manager.scpt stop

# Restart daemons
osascript /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/lauburu_offline_continuous_manager.scpt restart
```

### B. Via Native macOS LaunchAgent
```bash
# Check launchd registration
launchctl list | grep lauburu.offline

# Load and activate auto-boot persistence
launchctl load -w ~/Library/LaunchAgents/com.lauburu.offline-continuous-247.plist

# Unload / disable
launchctl unload ~/Library/LaunchAgents/com.lauburu.offline-continuous-247.plist
```

### C. Direct Shell Controller
```bash
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/lauburu_offline_continuous_daemon.sh status
```

---

## 🛡️ 3. Safety Invariants & Self-Healing Guarantees

1. **Zero-Mock Rule #0:** All metrics (active PIDs, trained pairs, memory usage) are queried from authentic Mach syscalls and JSON state checkpoints.
2. **Dynamic RAM Sanctuary (Rule 3):** The watchdog monitors available physical memory every 30 seconds. If available RAM drops below 3.0 GB, it triggers `purge` to clean inactive OS cache pages without interrupting inference.
3. **Zero Metal GPU Load for Drafter:** The 10M drafter executes on the host Silicon Neural ALU / CPU engine (`HOST_CPU_NEURAL_ALU`), leaving 100% of Metal GPU cores and unified VRAM free for `llama-server` verifiers on Port 8081/8082.
4. **Sleep Prevention:** `caffeinate -dimsu` prevents display, idle, and disk sleep while the daemons are active.
