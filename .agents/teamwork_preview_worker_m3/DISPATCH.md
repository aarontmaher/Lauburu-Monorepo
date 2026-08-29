## 2026-08-29T12:06:04Z

<USER_REQUEST>
You are teamwork_preview_worker_m3.
Your working directory is /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m3/.
You MUST read the authoritative user request at /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md and the master project specification at /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MISSION: Implement Milestone 3 (M3) — Tri-Vault Storage Auto-Healing, Daemon Supervision & Mesh Hardware Governance.

Files owned:
- `06_scripts_and_tooling/network/daemon_manager.py`
- `06_scripts_and_tooling/network/nomad_courier_self_healer.py`
- `06_scripts_and_tooling/network/router_onboard_micro_governor.sh`
- `00_core_infrastructure/self_healing_hub.py`
- `obsidian_vault/Index.md`

Requirements:
1. Tri-Vault Storage Auto-Healing:
   - Implement/verify continuous health verification and self-healing for Obsidian Vault (`obsidian_vault/Index.md` repair and Wikilinks validation), PySpark Lake, and Git worktree states (automatic `.git/index.lock` clearing and >=5.0GB disk headroom enforcement).
2. 7 Core Daemons Supervision Matrix:
   - Ensure `daemon_manager.py` and `nomad_courier_self_healer.py` supervise Ports 8080-8086, 18802 (Self-Healing Hub / WoL API), 50052 (Metal GPU RPC), 8088 (Supervisor) with sub-second health polling and automatic crash restart (maintaining >=99.99% uptime).
3. GL.iNet Router RAM Watchdog:
   - Ensure `router_onboard_micro_governor.sh` and `nomad_courier_self_healer.py` monitor GL-MT3600BE (`192.168.8.1`) memory, maintaining RAM strictly within <=35MB critical threshold with automatic `drop_caches` invocation.
4. Run validation tests on affected files.
5. Write your handoff to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m3/handoff.md` and notify orchestrator via send_message.
</USER_REQUEST>
