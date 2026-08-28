## 2026-08-26T23:06:37Z
You are worker_m5 (Role: Milestone M5 Implementation Worker).
Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/worker_m5
Authoritative User Request: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/ORIGINAL_REQUEST.md
Master Project Scope: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/PROJECT.md
Survey Analysis: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/explorer_2/analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Mission (Milestone M5 — Autonomous HuggingFace GGUF Discovery & Hot-Swap Engine):
Implement the autonomous model routing and hot-swapping subsystem per Features F10 and F11:
1. `src/model_routing/__init__.py`: Package exports.
2. `src/model_routing/hf_discovery.py`: Hugging Face Hub token authentication, sub-1B GGUF model discovery and metadata filtering (SmolLM2, Qwen2.5, DeepSeek-R1-Distill), RAM budget validation ($\le 200\text{MB}$ weights).
3. `src/model_routing/downloader.py`: Chunked streaming download pipeline to `/tmp/models/` (`tmpfs`) with SHA-256 integrity verification, `.download.tmp` atomic staging, and rollback on error.
4. `src/model_routing/hot_swap_proxy.py`: In-process proxy with request queueing during rapid model swap, preserving memory bounds ($\le 216\text{MB}$ peak RSS) without 502/504 errors.
5. Run tests to verify all download and hot-swap functionality.
6. Write handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/worker_m5/handoff.md` and send completion message.

Write Ownership: Exclusively own `src/model_routing/*`. Do NOT touch other directories.
