## 2026-08-26T22:59:06Z
You are worker_m1 (Role: Milestone M1 Implementation Worker).
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/worker_m1
Authoritative User Request: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/ORIGINAL_REQUEST.md
Master Project Scope: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/PROJECT.md
Survey Analysis: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/explorer_1/analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Mission (Milestone M1 — Router Containerization & Llama Server Engine):
Implement the router containerization and static llama server execution engine per Feature F1 and F2:
1. Create `Dockerfile` (multi-stage Alpine 3.20 base, musl static build, ARM64 OpenWrt optimization, non-root user, tmpfs mounts, healthcheck).
2. Create `Dockerfile.mips` (MIPS OpenWrt compatibility manifest).
3. Create `docker-compose.router.yml` with strict memory cgroup constraints (`mem_limit: 300m`, `mem_reservation: 150m`), tmpfs volume bindings, and host network configuration.
4. Create `entrypoint.sh` with cgroups v1/v2 memory limit verification, static daemon launcher, and trap signal handling.
5. Create Python foundation:
   - `pyproject.toml` (standard library + minimal dependencies `pytest`).
   - `src/__init__.py`, `src/config.py` (configuration holding 300MB RAM budget, paths, ports, timeouts).
   - `src/container/__init__.py`
   - `src/container/memory_guard.py` (resident set size `RSS` inspection via `/proc/self/statm` and `psutil`/`resource`, strict <=300MB enforcement, automatic GC/warning triggers).
   - `src/container/llama_runner.py` (lifecycle manager for static `llama-server` process, CLI arguments configuration for sub-1B models, prompt templating, health check, fallback mock runner when binary is not compiled on dev host).
6. Build / verify your implementation by running unit tests or validation scripts.
7. Write your handoff report to /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/worker_m1/handoff.md and send a completion message to parent.

Write Ownership: You exclusively own `Dockerfile`, `Dockerfile.mips`, `docker-compose.router.yml`, `entrypoint.sh`, `pyproject.toml`, `src/config.py`, `src/__init__.py`, and `src/container/*`. Do NOT modify files owned by other milestones.
