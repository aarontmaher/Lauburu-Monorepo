# Orchestration Plan: Marionette MCP, Shizuku Network Healing & AI Debate

## Objective
Deliver full production implementations and verified empirical test suites for:
1. `marionette-mcp` stdio MCP server matching `chrome-devtools-mcp` (Lens 2 Firefox)
2. Shizuku Network Healing Subsystem (privileged untethered Android self-healing)
3. Tri-Orchestrator AI Debate on Android Execution (Candidate C Hybrid consensus accord)
4. 4-Tier Opaque-Box E2E Testing Suite (100% pass across 49 tests + adversarial coverage)

## Execution Tracks & Milestones

### Track 1: Implementation Track
- **Milestone 1: Marionette MCP Server (`marionette-mcp`)**
  - Worker scaffolds package under `00_core_infrastructure/mcp_servers/marionette-mcp`
  - Implement stdio MCP server, GeckoDriver driver supervisor, 29 tools matching `chrome-devtools-mcp`
  - Implement base64 screenshot capture, DOM AX tree builder with `uid` tagging, DOM interaction handlers
  - Reviewer, Challenger, and Auditor verification loop
- **Milestone 2: Shizuku Network Healing Subsystem**
  - Worker implements `shizuku_network_healer.sh`, `setup_rish.sh`, Python controllers, and tests
  - Verify Doze bypass (`dumpsys deviceidle whitelist`), Phantom process disable, Wireless ADB (5555), Tailscale restart
  - Reviewer, Challenger, and Auditor verification loop
- **Milestone 3: Tri-Orchestrator AI Debate on Android Execution**
  - Worker executes 4-turn debate protocol (Cloud, Local Mesh, Genetic Evolution)
  - Generate debate transcript, consensus accord (Candidate C Hybrid >= 90%), LoRA JSONL record, ELO leaderboard update
  - Reviewer, Challenger, and Auditor verification loop

### Track 2: E2E Testing Track (Parallel)
- **Milestone 4: 4-Tier E2E Testing Suite (`tests/e2e/`)**
  - Test Writer / Worker builds unified test runner `run_all_e2e.py`
  - Implement Marionette MCP suite (19 tests across Tiers 1-4)
  - Implement Shizuku Healing suite (15 tests across Tiers 1-4)
  - Implement AI Debate suite (15 tests across Tiers 1-4)
  - Implement synthetic mocks and live hardware detection
  - Publish `TEST_READY.md`
- **Final Milestone: Pass 100% of E2E Test Suite & Adversarial Hardening (Tier 5)**
  - Execute full E2E suite and verify 100% passing rate
  - Execute Tier 5 adversarial challenge hardening
