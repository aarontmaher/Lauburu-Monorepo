# 5-Component Handoff Report: Swarm Rule #0, Tri-Lens Visual Swarm & Figma MCP Zero-Mock Guardrail Specification

- **Author:** `teamwork_preview_spec_miner_survey_2`
- **Working Directory:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_spec_miner_survey_2`
- **Target File:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_spec_miner_survey_2/handoff.md`
- **Timestamp:** 2026-08-26T02:26:30Z
- **Integrity Mode:** Benchmark / Strict Rule #0 Zero-Mock Specification Mining

---

## 1. Observation

Direct empirical observations from inspecting the codebase, skills, configuration files, and external MCP specifications:

### 1.1 Swarm Rule #0 Infrastructure & Definitions
- **System Prompt & Global Rules:** `RULE[user_global]` establishes the 5 core tenets of Rule #0 (No Fake Data, Zero-Tolerance for Hallucinations, Verification First, End-to-End Visual Audit, Punishment Protocol).
- **Swarm Skill Specification:** `/Users/aaron/.gemini/config/skills/swarm/SKILL.md` (lines 240-286) codifies:
  - Section 4.1: "Zero-Mock / Zero-Simulated Data Mandate (Global Rule #0)" — every metric displayed in UI must originate from live hardware, authentic log replays, or display a clean waiting state (`--`).
  - Section 4.2: Auditor Fleet — Cloud AI (Gemini 3.7 Flash, Gemini 1.5 Pro, Claude 3.5 Sonnet, GPT-4o) and Local AI (`LocalVisionVLMAgent`, Qwen3-VL-32B, Llama-3.2-11B-Vision).
  - Section 4.3: 4-Phase Audit Workflow (Intent Comprehension $\rightarrow$ OpenClaw Multi-Frame Sequential Click-Through $\rightarrow$ Zero-Tolerance Truth Analysis $\rightarrow$ LoRA Memory Ledger Logging).
  - Section 4.4: Mandatory Swarm Gate Invocation before declaring task completion.
- **Automated Verification Script:** `06_scripts_and_tooling/scripts/ai_claim_verifier.py` (lines 1-207) enforces **Rule #0.1** via live TCP socket probing across ports (`8265`, `8888`, `8087`, `8000`, `11434`), file byte count checks, and **Rule #0.3** automated remediation with Gemini Spark scoring.
- **Frontend Authenticity Audit:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_zero_mock_rep/handoff.md` identified that 73.3% of UI views are 100% authentic, but isolated synthetic mocks (`AITrainingHub.jsx` `setTimeout`, `ConsensusSpecialistSkillsDashboard.jsx` hardcoded GPU metrics) violate Rule #0 and require remediation.

### 1.2 Tri-Lens Visual Swarm Architecture
- **Lens 1 (Chromium CDP):** `chrome-devtools-mcp` (29 tools: `navigate_page`, `take_screenshot`, `take_snapshot`, `click`, `fill`, `evaluate_script`, `lighthouse_audit`).
- **Lens 2 (Gecko Marionette):** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_marionette_1/report.md` details `marionette-mcp` Node.js stdio server providing 1-to-1 parity with Chrome DevTools tools for Gecko/Firefox layout rendering and cross-browser visual diffing over Tailscale.
- **Lens 3 (Native Android/Termux):** `survey_explorer_e2e_infra_1/report.md` documents Shizuku-controlled Android 15 (Pixel 10 Pro XL) and Android 14 (Samsung Galaxy S20+) mobile visual streams, Doze mode bypass, and `termux-wake-lock`.
- **Cross-Browser Test Harness:** `tests/e2e/test_tier4_real_world_scenarios.py` (lines 180-206) implements `test_scenario_04_tri_lens_cross_browser_visual_parity_audit` verifying AX tree structural parity between Firefox and reference DOM trees.

### 1.3 Figma MCP Tooling & Verification Protocols
- **MCP Server Packaging:** Official server `@modelcontextprotocol/server-figma` via `npx` or remote endpoint `https://mcp.figma.com/mcp`.
- **Configuration Format:** Registered in `~/.gemini/settings.json` under `mcpServers.figma` with `trust: true` and `FIGMA_ACCESS_TOKEN`.
- **Tool Catalog:** `get_file` (document tree), `get_file_nodes` (granular AutoLayout/geometry AST), `get_image` (rendered node raster/SVG), `get_comments` (designer annotations).
- **Zero-Mock Design-to-Code Gate:** Distinguishes permissible structural layouts (flexbox/grid, CSS tokens, `{prop ?? '--'}`) from strictly forbidden mock data (hardcoded strings `<span>120 bpm</span>`, mock arrays `[{ id: 1 }]`, client-side `setTimeout` simulations).

---

## 2. Logic Chain

1. **Rule #0 Requires Pre-Merge Automated Gates:**
   - Because manual audits can overlook subtle hardcoded strings, an automated AST/regex linter must run in the CI/CD pipeline before any Figma-generated UI component can be merged.
   - The linter inspects code AST: allows structural HTML/CSS/flex containers and fallback expressions (`{data?.val ?? '--'}`), but throws non-zero exit code (blocking merge) on hardcoded mock payloads.

2. **Tri-Lens Visual Parity Validates Design Faithfulness without Compromising Data Integrity:**
   - Figma `get_image` provides the visual design reference.
   - Headless Chromium (Lens 1) and Headless Firefox (Lens 2) render the generated component in clean uninitialized/live state.
   - Perceptual image diffing (SSIM $\ge 0.95$) confirms geometric layout fidelity while ensuring zero hardcoded text strings are used.

3. **Multi-Model Consensus Guarantees Objective Audit Verdicts:**
   - Combining Cloud AI (Gemini 3.7 Flash for deep visual reasoning) and Local AI (`LocalVisionVLMAgent` / Qwen3-VL-32B for continuous local frame inspection) eliminates single-model bias and verifies compliance with monorepo contracts.

---

## 3. Caveats

1. **Figma Authentication Scope:** Official Figma OAuth scopes (`mcp:connect`) require active browser login or a Personal Access Token (`figd_*`). For headless CI/CD, `FIGMA_ACCESS_TOKEN` must be provisioned in the environment.
2. **Animation Clock Freezing:** Pages with continuous CSS/WebGL animations may fail strict pixel diffing; the test harness must disable animations or inject `@media (prefers-reduced-motion)` during visual parity capture.
3. **Read-Only Investigation:** As a Specification Miner, no source code, configuration files, or daemon environments were modified during this turn.

---

## 4. Conclusion

- The specifications, interface contracts, error behaviors, and edge cases for Swarm Rule #0, Tri-Lens Visual Swarm auditing, and Figma MCP verification have been mined, synthesized, and documented in `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_spec_miner_survey_2/spec_report.md`.
- All requirements and acceptance criteria from `ORIGINAL_REQUEST.md` have been mapped to concrete verification steps and pre-merge blocking mechanisms.
- Downstream workers (`worker_m1`, `worker_m2`, `test_writer`) have a complete, authoritative reference to implement the Figma MCP registration, Rule #0 verification SOP, and automated zero-mock test harness.

---

## 5. Verification Method

To independently verify these findings:

1. **Inspect Specification Report:**
   ```bash
   view_file /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_spec_miner_survey_2/spec_report.md
   ```
2. **Run Empirical Claim Verifier:**
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/scripts/ai_claim_verifier.py
   ```
3. **Verify Swarm Truth Audit Rules:**
   ```bash
   grep -n "Zero-Mock" /Users/aaron/.gemini/config/skills/swarm/SKILL.md
   ```
4. **Inspect Tri-Lens E2E Scenarios:**
   ```bash
   python3 -m unittest /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/tests/e2e/test_tier4_real_world_scenarios.py
   ```

---
*Handoff certified by `teamwork_preview_spec_miner_survey_2` under Rule #0 Data Authenticity Protocol.*
