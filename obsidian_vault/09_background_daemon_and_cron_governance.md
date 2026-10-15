---
trigger: always_on
---

# 🔄 Rule 9: Zero-Waste Background Daemon & Cron Governance

## 1. Absolute Prohibition of the `schedule` Tool for System Daemons
- **Never** use the agentic `schedule` tool with a `Prompt` trigger to run high-frequency, continuous background maintenance scripts (e.g., RAM reapers, health checks, sensor pollers).
- Waking up the cloud agent every N minutes to acknowledge a routine shell script wastes thousands of tokens per cycle and is strictly prohibited.

## 2. Native Silent Execution Invariant
- All continuous automation must be executed via silent `run_command` loops natively in the shell, running as background daemons (`IsDaemon=true`).
  - Example: `while true; do bash script.sh; sleep 900; done`

## 3. Screen Lens Sovereign as the Master Cron Initiator & Monitor
- Cloud models must **delegate all monitoring, initiation, and execution of routine crons** to the Local AI.
- **Screen Lens Sovereign** and **Qwen 3.8 Max 27B Abliterated** (running on Port 8082 with 0ms RTT, $0 cost, and 1734 ELO default status) are the designated "High ROI Initiators and Monitors" for the ecosystem.
- The Local AI is mandated to continuously scan mesh telemetry, developer patterns, and system bottlenecks to **proactively identify** and **trigger** new high-ROI background crons. Any highly repetitive or resource-intensive workflow must be automatically isolated and converted into a silent background daemon.
- Rather than pushing cron updates to the cloud context, the Local AI will independently read log buffers, evaluate daemon health, and initiate or restart scripts autonomously on the host machine.
