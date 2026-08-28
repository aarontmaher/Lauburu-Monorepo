---
name: nomad-autonomous-mesh-governor
description: Multi-WAN Nomad Courier Autonomous Mesh Governor. Orchestrates 5-tier self-healing, Antigravity skills persistence, MCP server validation, Port 3000/4000 web healing, Wake-on-LAN, and 24/7 LoRA action logging.
---

# Multi-WAN Nomad Courier Autonomous Mesh Governor

The **Nomad Courier** is the primary autonomous infrastructure, network, and self-healing agent of the Lauburu 7-layer distributed mesh.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      NOMAD COURIER AUTONOMOUS ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Antigravity Skills Guardian: Auto-syncs ai-debate, swarm, and 39 skills  │
│    into global config (~/.gemini/config/skills/) to survive mount drops.    │
│ 2. MCP Server Watchdog: Validates Obsidian Vault, stdio transports, and      │
│    prevents 404/401 auth collisions across all active tooling daemons.       │
│ 3. 5-Tier Network Failover: Tailscale -> Radio Bounce -> KDE Connect ->     │
│    Bluetooth PAN -> GL.iNet Router Physical USB ADB override.               │
│ 4. Service Auto-Healing: Monitors Port 3000 (UI), 4000 (App Store), 18802  │
│    (WoL REST API), and 50052 (llama.cpp RPC Sharding).                      │
│ 5. Continuous LoRA Serialization: Logs all autonomous healing actions as    │
│    JSONL training pairs to data/lora_datasets/nomad_autonomous_actions.jsonl│
│ 6. High-ROI Cron & Daemon Hierarchy: Offloads all standing routines to OS   │
│    daemons (launchd/systemd); strictly auto-prunes in-session agent crons.  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## ⏱️ High-ROI Cron & Routine Automation Standard

### 1. Execution Hierarchy ($0 Token Native Compute)
* **Standing Daemons (`launchd` / `systemd`)**: Always use OS-native scheduling (`ai.lauburu.*.plist` or systemd units) for 24/7 periodic monitoring, health checks, and watchdog loops.
* **Agent In-Session Crons (`schedule`)**: Strictly reserved for active, transient workflow supervision (e.g. waiting on an active build/test). Never use `schedule` with unbounded iterations for permanent tasks.

### 2. Autonomous ROI Gating & Self-Pruning
Before processing any cron iteration, the agent must evaluate **Marginal ROI**:
1. **Steady-State Detection**: If status is `[OK]`, `[STANDBY]`, or unchanged for 2+ ticks and background OS daemons are active, immediately invoke `manage_task(Action='kill', TaskId=...)` to terminate the in-session cron.
2. **Finite Iteration Cap**: In-session recurring cron tasks must set `MaxIterations: 3-5`.
3. **Silent Telemetry**: Route periodic status updates to local JSON/markdown reports rather than generating repetitive user chat responses.

## Quick CLI Usage & Execution

Execute a single self-healing and validation cycle:
```bash
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py --once
```

Start as a 24/7 background watchdog daemon:
```bash
nohup python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py --daemon > /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/network/nomad_daemon.log 2>&1 &
```

Inspect live telemetry status:
```bash
cat /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/network/nomad_self_healer_status.json
```
