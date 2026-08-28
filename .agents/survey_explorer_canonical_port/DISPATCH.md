## 2026-08-26T19:50:21Z
You are the Canonical Port Codebase Explorer.
Your working directory is: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_canonical_port`
Original request file: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`
Target app directory: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port`
Monorepo root: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`

YOUR MISSION:
Examine the current codebase in `01_apps/canonical_port`:
1. File structure, Python packages, dependencies (pyproject.toml, uv, requirements), entry points (CLI, TUI, Web).
2. Current architecture of the TUI (Textual/Rich or curses or custom), Web UI (FastAPI/Streamlit/WebSockets/HTML), and state store.
3. State management: How data is currently stored, updated, read, and serialized (JSON, YAML, in-memory models).
4. Identify architectural gaps with respect to:
   - Shared Telemetry Blackboard Pattern (central feed for agents/system).
   - Strict visual and modular separation between TUI and Web UI.
   - Ground-up stability hierarchy navigation and display.
   - Maximalist metric integration (ensuring all monorepo metrics fit cleanly and without clutter or fake data).
5. Existing test infrastructure: pytest setup, existing unit/integration tests, test runner commands.

OUTPUT REQUIREMENTS:
- Write your comprehensive codebase audit to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_canonical_port/canonical_port_survey.md`.
- Write a standard `handoff.md` in `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_canonical_port/handoff.md`.
- Send a completion message back to the orchestrator when finished.
