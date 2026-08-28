## 2026-08-28T00:50:45Z

You are the TUI & Mesh Infra Worker for Milestone 1 of the Canonical Port project.
Your working directory is: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/worker_m1_infra`
The authoritative request is recorded at: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md`
The project specification is at: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/PROJECT.md`
The Explorer handoff reports are at:
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/explorer_survey_1/handoff.md`
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/explorer_survey_2/handoff.md`
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/explorer_survey_3/handoff.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your implementation scope:
1. Fix syntax errors (unterminated string literals with raw newlines) and clean unreachable dead code in:
   - `tui/services/inference_bridges/gemini_bridge.py`
   - `tui/services/inference_bridges/cloudflare_bridge.py`
   - `tui/services/inference_bridges/julien_bridge.py`
2. Export `GeminiBridge`, `CloudflareBridge`, `JulienBridge` in `tui/services/inference_bridges/__init__.py`.
3. Fully register all engines (`auto`, `llama_rpc`, `exo`, `accelerate`, `petals`, `gemini`, `cloudflare`, `julien`) in `tui/services/inference_router.py` (including `SUPPORTED_ENGINES`, `ENGINE_DISPLAY_NAMES`, default bridges map, `get_status_badge()`).
4. Update `tui/services/latency_poller.py`:
   - Sanitize `measure_engine_ttft()` so that `"SYSTEM:"` or `"ERROR:"` chunks are recognized as offline/unconfigured (`is_available = False`, `ttft_ms = float('inf')`), preventing broken cloud bridges from being chosen as the fastest engine in `auto` mode.
   - Decouple cloud engine polling from the aggressive 3-second loop.
5. Harden `backend/agents/crons/daemon_supervisor.py`:
   - Check binary existence with `shutil.which()` before spawning subprocesses.
   - Add circuit breaking: max 3 restart attempts with exponential backoff before marking state as `FAILED_CIRCUIT_OPEN`.
   - Use OS-aware commands (macOS vs Linux) and avoid interactive `sudo` hangs.
   - Ignore clean-exited batch/ephemeral containers in container healing.
6. Fix import path in `backend/agents/cron_scheduler.py` (`from .crons.daemon_supervisor import supervisor`) and ensure the scheduler is started in `backend/app.py` lifespan.
7. Upgrade `boot_canonical_mesh.sh`:
   - Replace arbitrary `sleep`s with deterministic HTTP readiness probing (`curl -s http://127.0.0.1:4000/api/v1/status` or root).
   - Ensure AI debate sync daemon and biometrics bridge paths are resilient.
   - Create declarative Zellij layout `canonical_mesh.kdl`.
8. Secure REPL slash commands in `tui/views/agi_coding_terminal_view.py` and `tui/screens/agi_coding_terminal_screen.py`:
   - Implement handlers for `/key`, `/key_cf`, `/account_cf`, `/key_julien` so they set environment variables locally and display masked confirmation (e.g. `API Key set: sk-...1234`) without transmitting keys to the LLM router.
9. Execute build and test verification:
   - `uv run pytest tests/unit/test_inference_router.py tests/unit/test_auto_fallback.py tests/unit/test_obsidian_parser.py -v`
10. Write your complete handoff report with verification commands and output to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/worker_m1_infra/handoff.md` and notify parent via `send_message`.
