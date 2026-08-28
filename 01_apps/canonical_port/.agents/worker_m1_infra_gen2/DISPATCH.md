## 2026-08-28T01:30:19Z
You are the Replacement Worker (Gen2) for Milestone 1 of the Canonical Port project.
Your working directory is: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/worker_m1_infra_gen2`
The authoritative request is recorded at: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md`
The project specification is at: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/PROJECT.md`
Explorer handoff reports:
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/explorer_survey_1/handoff.md`
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/explorer_survey_2/handoff.md`
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/explorer_survey_3/handoff.md`

Tasks:
1. Fix Syntax Errors in Inference Bridges: gemini_bridge.py, cloudflare_bridge.py, julien_bridge.py
2. Export in tui/services/inference_bridges/__init__.py: GeminiBridge, CloudflareBridge, JulienBridge
3. Register all engines in tui/services/inference_router.py
4. Update tui/services/latency_poller.py: measure_engine_ttft detection and cloud bridge auto fallback filtering
5. Harden backend/agents/crons/daemon_supervisor.py (shutil.which, circuit breaker, container exit code check)
6. Fix import in backend/agents/cron_scheduler.py and hook into backend/app.py lifespan
7. Update boot_canonical_mesh.sh (readiness polling, bridge/sync daemons, canonical_mesh.kdl Zellij layout)
8. Secure REPL commands in tui/views/agi_coding_terminal_view.py (/key, /key_cf, /account_cf, /key_julien)
9. Run build/test verification with pytest
10. Write handoff report and notify parent agent.
