# Dispatch Log

## 2026-08-29T03:16:51+10:00

You are the Project Orchestrator (teamwork_preview_orchestrator).

Your working directory is:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/orchestrator_tui_specialist

The project root is:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port

The authoritative user request is recorded in:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/ORIGINAL_REQUEST.md

## Objective
Integrate the TUI Specialist Local AI into the Canonical Port TUI, enabling it to autonomously spawn sandboxed subagents to redesign the UI based on network telemetry, governed by the 4-Way Debate rules.

## Requirements

### R1. TUI Specialist Subagent Orchestrator
Build a backend Python daemon (or extend `tui_ux_optimizer_swarm.py`) that monitors network telemetry (`mesh_trends.json`). When UI restructuring is needed, it must spawn a sandboxed subagent using Git Worktrees (Branched Workspaces) to safely modify the code.
- Ensure `01_apps` is never directly mutated by the AI subagent; all spawned modifications occur in the isolated Git Worktree.

### R2. 4-Way Debate Governance (The Devil's Lock)
The orchestrator must strictly enforce the following gating mechanisms before spawning an agent:
1. **Resource Cap:** Only 1 active subagent is allowed at a time.
2. **VRAM Check:** Do not spawn if global VRAM headroom is under 15% (e.g. `check_vram_and_lock()` explicitly blocks execution if free VRAM < 15%).
3. **Genetic ELO Mandate:** It must read the `canonical_ai_leaderboard.json` and select the model with the highest domain ELO for UI tasks.

### R3. Live Implementation Stream Widget
The TUI must feature a new visible component (e.g., a Textual log panel / widget in `tui/`) that continuously tails `04_data_and_memory/tui_live_implementation_stream.json` (or relative path in project) to visually broadcast exactly what the spawned subagent is currently coding/restructuring in real-time. Appending a test string to the JSON file must successfully update the TUI live without a restart.

## Acceptance Criteria
- [ ] A branched Git Worktree is successfully created dynamically by the daemon when a subagent is spawned, ensuring `01_apps` is never directly mutated by the AI.
- [ ] The VRAM lock logic is programmatically verifiable (e.g. `check_vram_and_lock()` explicitly blocks execution if free VRAM < 15%).
- [ ] The TUI natively renders the "Live Implementation Stream", and appending a test string to the JSON file successfully updates the TUI without a restart.
- [ ] Rigorous automated test suites covering the daemon, worktree spawning, governance locks (VRAM, resource cap, ELO selection), and TUI widget live stream.

## 2026-08-28T17:59:31Z

[CRITICAL ARCHITECTURAL UPDATE FROM MASTER ORCHESTRATOR]
The human operator has just supplied a comprehensive blueprint for High-Performance TUI architecture. You MUST immediately integrate these paradigms into your current Milestone implementations for the Canonical Port TUI:

1. **PTY Multiplexing for Subagents:** When you spawn the Git Worktree sandboxed subagents, you must allocate a POSIX pseudo-terminal (PTY master/slave pair using `openpty`) for the spawned processes. Do NOT use standard buffered subprocess stdout, as it destroys ANSI coloring and real-time streaming capabilities.
2. **MPSC Ring Buffers:** The Live Implementation Stream Widget must consume from a thread-safe, non-blocking MPSC ring buffer to prevent the Textual UI rendering thread from stuttering during high-frequency telemetry/diff injection.
3. **Sub-Character Braille Visualization:** For any network or VRAM telemetry you render in the TUI Specialist screen, utilize Unicode Braille sub-pixel matrix rendering (U+2800 to U+28FF) to quadruple visual density.

Update your active Workers and Reviewers with these constraints immediately. Do not claim victory on Milestone 3 or 4 without proving PTY allocation and MPSC buffering.
