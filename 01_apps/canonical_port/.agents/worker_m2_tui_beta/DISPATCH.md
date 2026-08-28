## 2026-08-28T01:51:51Z

You are Worker Beta for Milestone 2 of the Canonical Port project.
Your working directory is: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/worker_m2_tui_beta`
The authoritative request is recorded at: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md`
The project specification is at: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/PROJECT.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
1. Build a standalone, production-grade, runnable Textual application prototype at `tui/prototypes/tui_beta_chat_ide.py` implementing the "Multi-Engine Swarm IDE & Chat Shell" (Chat/Inference-heavy paradigm):
   - Top Header Bar: Dynamic Engine Selector (`[Ctrl+E]` / `[F2]`) with active engine badge, TTFT ms, and tok/s metrics across all 8 engines (`auto`, `llama_rpc`, `exo`, `accelerate`, `petals`, `gemini`, `cloudflare`, `julien`).
   - Split Workspace (65% / 35%):
     - Left Main Pane (65%):
       - Upper (60%): Interactive multi-agent chat & REPL stream with color-coded agent badges (`[Kimi 88B]`, `[Qwen 38B]`, `[Llama 70B]`, `[Gemini Flash]`, `[Cloudflare AI]`) and markdown rendering.
       - Lower (40%): Active code buffer & diff inspector with line numbers and 1-click execution.
     - Right Sidebar (35%):
       - Panel 1: Live Tri-Orchestrator Debate Consensus Gauge (Cosine accord meter, current turn, tie-breaker code-off status).
       - Panel 2: S2S Voice Coding & Transcription HUD (16kHz VAD status, live transcription buffer, TTS playback pill).
       - Panel 3: Multi-Engine Latency Matrix (TTFT comparison table across all 8 backends).
   - Bottom Bar: Interactive prompt / command input bar (`/audit`, `/duel`, `/split`, `/engine`, `/model`, `/key`) with command history.
   - Non-blocking streaming inference via `UnifiedInferenceRouter`.
2. Write a comprehensive unit and Textual Pilot test at `tests/unit/test_tui_beta_chat_ide.py` verifying mounting, engine cycling, prompt execution, and layout.
3. Run verification: `uv run pytest tests/unit/test_tui_beta_chat_ide.py -v`
4. Write handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/worker_m2_tui_beta/handoff.md` and notify parent via `send_message`.
