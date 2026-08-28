## 2026-08-25T20:22:10Z

You are the Telemetry Pipeline Explorer.
Your working directory is: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_m1_telemetry/
You must read:
1. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md
2. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md

Your objective is to explore and analyze the exact code in:
- `00_core_infrastructure/self_healing_hub/backend/`
- `00_core_infrastructure/self_healing_hub/frontend/src/LiveDeviceSentinelHUD.jsx`
- `01_apps/lauburu_compute_hub/`

Investigate and formulate the exact technical implementation plan for:
1. Dynamic host thermal and compute telemetry poller:
   - macOS Darwin: sysctl / powermetrics / psutil for real CPU, RAM, thermal sensors (Apple Silicon SMC temperature sensors or thermal pressure level).
   - Linux: /sys/class/thermal/ or sensors + psutil.
   - Remote Mesh Nodes: Tailscale RPC (/api/node/telemetry over Tailscale IP).
   - Ensure fluctuating, genuine values (strict Rule #0 zero mock data).
2. FastAPI WebSocket server endpoint (`/ws/telemetry` or `/ws/live_telemetry`):
   - Asynchronous broadcast loop streaming metrics at 1-2 Hz.
3. Frontend `LiveDeviceSentinelHUD.jsx`:
   - WebSocket connection lifecycle (connect, reconnect, error handling).
   - Feeding dynamic real-time data into Recharts sparklines (cpu_history, ram_history, thermal_history).

Output a detailed specification and implementation plan in `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_m1_telemetry/handoff.md` and send a message when complete.
