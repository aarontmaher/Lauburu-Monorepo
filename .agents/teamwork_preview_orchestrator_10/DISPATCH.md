## 2026-08-26T01:06:06Z

<USER_REQUEST>
You are the Project Orchestrator (teamwork_preview_orchestrator).

## Identity & Workspace
- Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_10
- Project root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
- Authoritative User Request: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

## Completed Survey Findings Available
The Step 0 Survey phase has already completed! Read the completed handoffs before proceeding to Step 1:
1. Marionette MCP Architecture: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_marionette_1/handoff.md`
2. Shizuku Network Healing & AI Debate: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_spec_miner_shizuku_1/handoff.md`
3. E2E Testbed & Infra: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_e2e_infra_1/handoff.md`

## Mission & Requirements
1. **R1. Marionette MCP Server (Tri-Lens Swarm)**:
   - Develop a Node.js stdio MCP server (`marionette-mcp`) that utilizes GeckoDriver to control a headless Firefox instance.
   - Expose MCP tools (e.g., `navigate`, `screenshot`, `get_ax_tree`) that match the `chrome-devtools-mcp` API.

2. **R2. Shizuku Network Healing App Integration (Android)**:
   - Integrate and verify the existing Shizuku Network Healing App (as specified in LAUBURU_APP_ECOSYSTEM).
   - Leverage elevated ADB privileges to autonomously execute Swarm Self-Healing Pathways (restart `com.tailscale.ipn`, toggle Wi-Fi, keep OpenClaw ADB server alive) to bypass Android Doze mode without a permanent PC tether.

3. **R3. AI Debate on Android Execution**:
   - Execute a Tri-Orchestrator debate on the optimal Shizuku implementation path (native Kotlin Android app vs Termux `shizuku-runner` bash daemon).

## Acceptance Criteria
- [ ] Programmatic test verifies `marionette-mcp` server launches Firefox, navigates to a local URL, and returns valid base64 screenshot via MCP tool call.
- [ ] Tri-Orchestrator debate artifact definitively selects the most resilient Shizuku execution architecture.
- [ ] Shizuku payload executes privileged system command (like restarting Tailscale VPN) on Android testbed, proving untethered ADB access.

## Operating Rules
- Strictly adhere to Rule #0 Zero-Mock truth & verification rules (no fake data, real tests, empirical verification).
- Create `BRIEFING.md`, `PROJECT.md`, `plan.md`, and maintain `progress.md` in your working directory (`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_10`).
- Decompose and dispatch workers across Implementation & E2E Testing tracks.
- When all criteria are met and verified, report completion to the Sentinel.
</USER_REQUEST>
