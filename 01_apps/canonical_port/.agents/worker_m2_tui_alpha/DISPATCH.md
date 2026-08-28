## 2026-08-28T01:51:51Z
You are Worker Alpha for Milestone 2 of the Canonical Port project.
Your working directory is: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/worker_m2_tui_alpha`
The authoritative request is recorded at: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md`
The project specification is at: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/PROJECT.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
1. Build a standalone, production-grade, runnable Textual application prototype at `tui/prototypes/tui_alpha_dashboard.py` implementing the "Telemetry & Mesh NOC Dashboard" (Dashboard-heavy paradigm):
   - Top Header Bar: 7-node physical mesh health pill matrix (Mac Host, MacBook Pro, Linux Head, Linux Tablet, MacBook Air, Pixel 10 Pro, Samsung S20 + Gateway), Pooled RAM/VRAM Meter (108GB/82.8GB), and WAN interface.
   - 3-Column Bento Box Layout:
     - Col 1 (30% width): 7-layer node telemetry cards (CPU load, thermals, VRAM caps, TB4 DMA RTT latency).
     - Col 2 (45% width): Live Biometrics & DSP Center (512Hz ECG stream, Kamath filter status, Zone 2 DFA-alpha1 0.750 gauge, PTT Blood Pressure).
     - Col 3 (25% width): Docker & Daemon Supervisor HUD (Container health states, auto-restart counters, circuit breaker status, Tailscale DERP relays).
   - Bottom Dock: Live alarm & telemetry event ticker + action buttons (`[Restart Daemons]`, `[Probe TB4]`, `[Calibrate ECG]`, `[Purge RAM]`).
   - Zero-Mock Rule #0 Compliance: Direct binding to authentic hardware probes and blackboard snapshots; clean `--` or `STANDBY` on disconnected sensors/nodes.
   - Non-blocking `@work(thread=True)` or asyncio timers.
2. Write a comprehensive unit and Textual Pilot test at `tests/unit/test_tui_alpha_dashboard.py` verifying mounting, layout responsiveness, and event handling.
3. Run verification: `uv run pytest tests/unit/test_tui_alpha_dashboard.py -v`
4. Write handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/worker_m2_tui_alpha/handoff.md` and notify parent via `send_message`.
