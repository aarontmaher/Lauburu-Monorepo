## 2026-08-27T12:51:37Z

You are Worker 1: Tri-Framework TUI Prototypes Implementer.

Read ORIGINAL_REQUEST.md at:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

Read PROJECT.md at:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_15/PROJECT.md

Read Explorer reports at:
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_survey_1/report.md
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_survey_3/report.md

Your working directory is:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_tui_prototypes_1

Write Ownership:
You exclusively own:
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_tui_prototypes/python_textual/ (app.py, pyproject.toml, requirements.txt)
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_tui_prototypes/go_bubbletea/ (main.go, go.mod, go.sum)
- /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_tui_prototypes/rust_ratatui/ (Cargo.toml, src/main.rs)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Task:
1. Create `01_apps/canonical_tui_prototypes/python_textual/`:
   - Textual TUI reading `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/cloud_api_quota_state.json`.
   - Rich HUD, DataTable, Provider Quota ProgressBars, Latency Counters, Status pills (HEALTHY/DEGRADED/EXHAUSTED), Keybindings (`q` to quit, `r` to force refresh, `p` to pause).
   - Flags: `--state-path`, `--poll-interval`, `--verify` (headless exit code 0 if valid state), `--timeout`.
   - Safe retry backoff on JSON parse error / flock concurrency.
2. Create `01_apps/canonical_tui_prototypes/go_bubbletea/`:
   - Single-file Go application with Bubble Tea, Lip Gloss, Bubbles table/progress.
   - Flags: `-state-path`, `-poll-interval`, `-verify`, `-timeout`.
   - Safe flock/backoff retry, exit 0 on `-verify`.
   - `go mod init canonical_tui_go`, `go mod tidy`. Build and test binary.
3. Create `01_apps/canonical_tui_prototypes/rust_ratatui/`:
   - Ratatui + Crossterm + Serde JSON TUI application.
   - Flags: `--state-path`, `--poll-interval`, `--verify`, `--timeout`.
   - Layout chunks, Table, Gauges, Provider status cards, sub-10ms init.
   - `Cargo.toml` with `ratatui`, `crossterm`, `serde`, `serde_json`, `chrono`, `clap`. Build and test with `cargo build`.
4. Test and verify that all 3 prototypes build, run with `--verify` (exiting 0), and correctly display the real `cloud_api_quota_state.json`.
5. Write your detailed handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_tui_prototypes_1/handoff.md` with build and test command outputs.
6. Send message to parent upon completion.
