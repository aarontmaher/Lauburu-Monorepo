# Execution Plan: Marionette MCP, Shizuku Network Healing & AI Debate

## Objective
Deliver complete, fully functional, and empirically verified implementations of:
1. `marionette-mcp` (Node.js stdio MCP server controlling Firefox with 29-tool parity, screenshot base64, AX tree serializer).
2. Shizuku Network Healing subsystem (privileged shell scripts, Tailscale VPN restarter, Port 5555 persistence, Doze bypass).
3. Tri-Orchestrator AI Debate module (consensus accord on Shizuku architecture, LoRA dataset generation, canonical ELO ledger update).
4. 4-Tier E2E Test Suite (`run_all_e2e.py` covering feature, boundary, cross-feature, and real-world workloads).

## Phases & Milestones

### Track A: Implementation Track
- **M1: Marionette MCP Server**
  - Worker writes Node.js stdio server wrapping GeckoDriver/Firefox.
  - Verification: Launch server, navigate to local URL, call `take_screenshot` & `take_snapshot`, verify base64 image and AX tree.
- **M2: Shizuku Network Healing Subsystem**
  - Worker writes shell and Python scripts for privileged execution (`rish`/`adb`), Tailscale daemon restart, Wi-Fi bouncing, TCP 5555 persistence, Doze whitelisting.
  - Verification: Execute privileged system commands on testbed / mock environment, confirm exit code 0 and proper execution logs.
- **M3: Tri-Orchestrator AI Debate**
  - Worker executes debate between Cloud (Gemini 3.1 Pro), Local Mesh (Qwen 3.8B), and Genetic Evolution (Kimi Tandem).
  - Synthesize mathematical accord (Candidate C Hybrid architecture), output LoRA JSONL dataset, update canonical ELO leaderboard.
  - Verification: Verify generated debate markdown, JSONL format, and ELO ledger math.

### Track B: E2E Testing Track
- **M4: 4-Tier E2E Testing Suite**
  - Test writer / Worker creates comprehensive opaque-box test suite (`tests/e2e/run_all_e2e.py` + tier modules).
  - Tiers: Tier 1 (Feature Coverage), Tier 2 (Boundary & Error), Tier 3 (Cross-Feature Pairwise), Tier 4 (Real-World Application).
  - Verification: 100% pass across all 4 tiers, followed by Tier 5 adversarial review.

### Review & Verification Gate
- For all milestones: Reviewer approval, Challenger stress-testing, Forensic Auditor clean verdict.
