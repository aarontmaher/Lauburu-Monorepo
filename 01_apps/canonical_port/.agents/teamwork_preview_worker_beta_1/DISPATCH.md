# Dispatch Assignment: Track Beta Worker (Chat & IDE Interface)

## Mission
Implement the competitive Track Beta React prototype (`src/prototypes/TrackBetaChatIde.jsx`) and refine terminal/governance subcomponents in `src/components/terminal/` and `src/components/governance/`.

## Key Instructions & Constraints
1. Read `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md` and `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/PROJECT.md`.
2. Exclusive Write Ownership:
   - `src/prototypes/TrackBetaChatIde.jsx`
   - `src/components/terminal/`
   - `src/components/governance/`
3. Requirements:
   - High visual density 65%/35% workspace split:
     * Left pane: Multi-agent chat stream with color-coded badges, AST code buffer editor, live diff inspector, 1-click execution console.
     * Right sidebar: Tri-Orchestrator debate panel, 8-engine dynamic selector (`auto`, `llama_rpc`, `exo`, `petals`, `gemini`, `cloudflare`, etc.), latency matrix, and voice coding HUD.
   - Slash Command Dispatcher dock (`/audit`, `/duel`, `/split`, `/engine`, `/nodes`, `/biometrics`, `/restart_daemons`, `/key`).
   - Non-blocking state management: code buffer typing must have zero input latency during streaming.
   - Strict adherence to Rule #0 (Zero-Mock): fallback to clean `--` or `STANDBY` when models/backends are unreachable.
4. MANDATORY INTEGRITY WARNING:
   > DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
5. Verify build with `npm run build`.
6. Output handoff to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_worker_beta_1/handoff.md`.
