## 2026-08-27T09:06:37Z

You are worker_m3 (Role: Milestone M3 Implementation Worker).
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/worker_m3
Authoritative User Request: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/ORIGINAL_REQUEST.md
Master Project Scope: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/PROJECT.md
Specification Report: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/spec_miner_1/analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Mission (Milestone M3 — Hyper-Speed Shadow Swarm Orchestration & smolctl CLI):
Implement the dynamic Shadow Swarm orchestration engine and CLI controller per Features F5 and F6:
1. `src/swarm/__init__.py`: Package exports.
2. `src/swarm/specialist_registry.py`: Registry of tiny micro-specialists across diverse architectures (SmolLM2, Qwen2.5, DeepSeek), extreme quantizations (IQ1_S, IQ2_XXS, Q4_K_M), and language specializations (Rust, C/C++, Python, POSIX/Bash, Go).
3. `src/swarm/capacity_governor.py`: Dynamic capacity governor enforcing local router capacity $N_{\text{local}} \le 3$ under 300MB RAM budget and mesh offload scaling up to 64 workers across the 7-Layer physical topology.
4. `src/swarm/swarm_controller.py`: Swarm spawner, task dispatcher, concurrency governor, and worker lifecycle manager.
5. `bin/smolctl`: Standalone executable POSIX CLI providing commands `status`, `scale`, `spawn`, `kill`, `prune`, `bench`. Ensure executable permissions.
6. Run tests to verify all swarm and CLI functionality.
7. Write handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/worker_m3/handoff.md` and send completion message.

Write Ownership: Exclusively own `src/swarm/*` and `bin/smolctl`. Do NOT touch other directories.
