## 2026-08-26T06:26:34Z
<USER_REQUEST>
You are the Telemetry Pipeline Implementation Worker.
Your working directory is: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m1_telemetry/
You must read:
1. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md
2. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md
3. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_m1_telemetry/handoff.md

You exclusively own these files:
- `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py`
- `01_apps/lauburu_compute_hub/telemetry_poller.py`
- `01_apps/lauburu_compute_hub/main.py`
- `00_core_infrastructure/self_healing_hub/frontend/src/LiveDeviceSentinelHUD.jsx`

Your objective:
1. Implement `telemetry_poller.py` containing `HostTelemetryPoller`:
   - macOS Darwin: psutil CPU/RAM/loadavg, Apple Silicon Metal GPU/VRAM via `ioreg -r -d 1 -c IOAccelerator`, power/thermal via `pmset` and dynamic load thermal scaling.
   - Linux: /sys/class/thermal/, /proc, psutil.
   - Android Termux: termux-battery-status query.
   - Tailscale RPC: /api/node/telemetry context-aware routing.
   - Network IO: 1-second delta transfer rates.
   - Strict Rule #0: genuine, fluctuating numbers; null on unreachable metrics.
2. Upgrade `01_apps/lauburu_compute_hub/main.py`:
   - Replace dummy heartbeat with `TelemetryConnectionManager`.
   - Add `/ws/telemetry` & `/ws/live_telemetry` WebSocket endpoints.
   - Add `/api/node/telemetry` REST fallback endpoint.
   - Run 1 Hz async background broadcast loop (`telemetry_broadcast_loop`) using `asyncio.to_thread`.
3. Upgrade `00_core_infrastructure/self_healing_hub/frontend/src/LiveDeviceSentinelHUD.jsx`:
   - Implement `useLiveTelemetry` WebSocket hook with auto-reconnect backoff.
   - Add rolling 30-sample history buffers (`cpu_history`, `ram_history`, `thermal_history`, `gpu_history`).
   - Implement responsive `<TelemetrySparkline />` components using Recharts to render smooth cubic sparklines in HUD cards and summary header.
   - Add live WebSocket connection badge (e.g. `🟢 1Hz STREAM`).
4. Run python syntax/unit tests to verify correctness and no syntax/runtime errors.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write your report in `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m1_telemetry/handoff.md` and send a message when complete.
</USER_REQUEST>
