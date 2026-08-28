# BRIEFING — 2026-08-27T09:10:30Z

## Mission
Implement Milestone M5 (Autonomous HuggingFace GGUF Discovery & Hot-Swap Engine) for `router_ai_daemon` (`smolagi`), providing genuine, zero-mock implementations of `hf_discovery.py`, `downloader.py`, `hot_swap_proxy.py`, and `__init__.py` with comprehensive unit and integration tests.

## 🔒 My Identity
- Archetype: worker_m5
- Roles: implementer, qa, specialist
- Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/worker_m5
- Original parent: 74728c58-02e2-4837-ae66-8ed54a29d516
- Milestone: M5 (Autonomous HF Model Routing & Hot-Swap)

## 🔒 Key Constraints
- Strictly adhere to <= 300MB RAM budget (target peak RSS <= 216MB for model routing & swap).
- Zero Flash Wear invariant: use tmpfs paths (`/tmp/models/`, `/tmp/secrets/`, etc.), never write volatile secrets or weights to persistent flash.
- Zero-mock / Real logic: Real SHA-256 verification, real chunked streaming downloader with atomic `.download.tmp` staging and rollback, genuine Hugging Face Hub REST discovery and token auth, and real zero-downtime HTTP hot-swap proxy with in-memory request queueing.
- Exclusive write ownership: `src/model_routing/*` and associated tests `tests/test_model_routing.py`.

## Current Parent
- Conversation ID: 74728c58-02e2-4837-ae66-8ed54a29d516
- Updated: 2026-08-27T09:10:30Z

## Task Summary
- **What to build**:
  1. `src/model_routing/__init__.py`: Package exports for discovery, downloader, and hot-swap proxy.
  2. `src/model_routing/hf_discovery.py`: HF Hub token auth, discovery of sub-1B GGUF models, metadata parsing (quant, size, context, architecture), RAM budget validation (<= 200MB model weight cap).
  3. `src/model_routing/downloader.py`: Chunked streaming download pipeline to tmpfs with pre-flight storage/memory checks, progress callbacks, SHA-256 integrity verification, `.download.tmp` atomic rename and cleanup on failure.
  4. `src/model_routing/hot_swap_proxy.py`: In-process proxy with request queueing during rapid model swap, coordination with `LlamaServerRunner`, zero dropped requests (no 502/504 errors), memory guards, and latency SLAs (< 600ms swap duration).
  5. `tests/test_model_routing.py`: Comprehensive test suite verifying all aspects of F10 and F11.
- **Success criteria**: 100% genuine code, passes all tests, no regressions.
- **Interface contracts**: PROJECT.md § 4 (HF Model Manager <-> llama.cpp Runner `hot_swap_model(repo_id, filename, ram_budget_mb) -> ModelSwapResult`).
- **Code layout**: PROJECT.md § Code Layout.

## Change Tracker
- **Files modified**:
  - `src/model_routing/__init__.py`: Package exports for M5 subsystem
  - `src/model_routing/hf_discovery.py`: HF Hub discovery, token auth, RAM budget validation
  - `src/model_routing/downloader.py`: 64KB chunked streaming downloader to tmpfs with SHA-256 verify & rollback
  - `src/model_routing/hot_swap_proxy.py`: Zero-downtime hot-swap proxy with request queueing & memory guard
  - `tests/test_model_routing.py`: 23 unit & integration tests for M5
- **Build status**: PASS (23/23 tests in `test_model_routing.py`, 113/113 tests in tier suite).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: PASS (100% test pass on all M5 tests).
- **Lint status**: Clean, compliant with PEP 8 and Python 3.10+ typing.
- **Tests added/modified**: Added `tests/test_model_routing.py` covering all features and boundary invariants.

## Loaded Skills
- **Source**: N/A
- **Local copy**: N/A
- **Core methodology**: Minimal changes, real logic, rigorous edge-case testing.

## Key Decisions Made
- Standard library first: `urllib.request`, `hashlib`, `threading`, `dataclasses` ensuring minimal memory overhead and zero runtime dependency friction on Alpine Linux / OpenWrt ARM64.
- Thread-safe request queueing with `threading.Event` signaling ensuring 0 dropped requests and sub-600ms swap lifecycle.

## Artifact Index
- `.agents/worker_m5/DISPATCH.md` — Dispatch instructions
- `.agents/worker_m5/BRIEFING.md` — Situational awareness and state
- `.agents/worker_m5/progress.md` — Liveness heartbeat and milestone tracking
- `.agents/worker_m5/handoff.md` — Milestone M5 completion handoff report
