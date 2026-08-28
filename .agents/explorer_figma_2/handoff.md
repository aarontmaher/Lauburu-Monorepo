# Handoff Report — Rule #0 Zero-Mock AST Linter & Discrimination Rubric

- **Agent**: `explorer_figma_2`
- **Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_figma_2`
- **Deliverables Referenced**:
  - Comprehensive Report: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_figma_2/report.md`
  - Target Python Linter Design: `06_scripts_and_tooling/scripts/figma_zero_mock_linter.py`
  - Target SOP Document Design: `06_scripts_and_tooling/docs/FIGMA_ZERO_MOCK_SOP.md`
- **Timestamp**: 2026-08-26T21:56:30+10:00
- **Type**: Hard Handoff (Task Complete)

---

## 1. Observation

1. **Rule #0 System Mandate (`RULE[user_global]`)**:
   "1. No Fake Data: Never use simulated or mock data. Use real, empirically verified data only. 2. Zero-Tolerance for Hallucinations: Every claim made must be truth-audited. ... 5. Punishment Protocol: Any violation (hallucination, fake data, false claim) will result in the AI being placed into a rigorous training loop until corrected."
2. **Swarm Truth Audit Mandate (`/Users/aaron/.gemini/config/skills/swarm/SKILL.md` lines 240-245)**:
   - "ABSOLUTELY NO SIMULATED DATA. Never use simulated, randomized, or mock arrays for telemetry across any application."
   - "NO FAKE DATA. Every metric displayed in the UI must originate from live hardware, authentic log replays, or display a clean waiting state (`--`)."
3. **Existing Static Judge Capabilities (`tests/zero_mock_judge/zero_mock_static_judge.py` lines 47-60, 348-465)**:
   - Contains `TELEMETRY_KEYS_REGEX`, `LATENCY_STRING_REGEX`, and `JsTsScanner` detecting hardcoded telemetry properties, mock arrays pre-marked `ACTIVE`, synthetic math multipliers, and `Math.random()` in telemetry code.
   - However, existing static judge lacks UI-specific AST awareness (e.g. distinguishing `JSXText` in static table headers `<th>Heart Rate</th>` from hardcoded data in `<span>142 bpm</span>`, or Flutter `Text("Title")` vs `Text("142 bpm")`, and Vue SFC `<template>` / `<script setup>` discrimination).
4. **Authoritative Spec Miner Findings (`.agents/teamwork_preview_spec_miner_survey_2/spec_report.md` lines 95-112)**:
   - Formulates the baseline distinction between Permissible Structural Layout (DOM hierarchy, Flexbox/Grid, design tokens, dynamic state bindings `{val ?? '--'}`) and Forbidden Mock Data (hardcoded literals, synthetic timers, mock arrays).
5. **Telemetry Acceptance Ground Truth (`tests/adversarial_zero_mock_telemetry_audit.py` lines 76-85)**:
   - Validates that uninitialized / disconnected hardware sensors return explicit `None`, `null`, or `'--'` (`assert sensor_state["hr"] == "--"`).

---

## 2. Logic Chain

1. **Step 1 (Grounding in Core Mandates)**:
   Per Observations 1, 2, and 4, the monorepo strictly prohibits synthetic or mock telemetry data in production code while permitting pure structural UI layout and design tokens extracted from Figma.
2. **Step 2 (Identifying the Discrimination Boundary)**:
   Based on Observation 3 and 4, a naive string or regex scanner will produce false positives on static chrome labels (e.g., table headers `<th>Throughput (Mbps)</th>`, navigation buttons `<button>Reconnect</button>`). Therefore, the linter must combine tag whitelist classification (`CHROME_TAGS` vs `DATA_TAGS`) with unit pattern analysis (`TELEMETRY_UNIT_REGEX`) to accurately isolate mock data literals from structural headers.
3. **Step 3 (Multi-Language AST & Syntax Coverage)**:
   Figma design-to-code pipelines generate code targeting React/TSX, Vue, HTML, Flutter/Dart, and Python dashboards. Parsing algorithms must handle JSX AST (`JSXText`, `JSXExpressionContainer`), Vue SFC template interpolations (`{{ val ?? '--' }}`), Flutter widget trees (`Text("...")`), and Python AST (`ast.Dict`, `ast.BinOp`).
4. **Step 4 (Deterministic Pre-Merge Blocking Mechanism)**:
   To prevent mock data from entering git history, the CLI tool must return exit code `1` whenever any mock violation is detected and exit code `0` only when the codebase is 100% Zero-Mock Certified. Git pre-commit and pre-push hooks execute this CLI tool to automatically block non-compliant commits.
5. **Step 5 (Full Implementation Specification)**:
   The complete architecture for `figma_zero_mock_linter.py` and `FIGMA_ZERO_MOCK_SOP.md` is synthesized in `report.md` with complete classes, regexes, visitor rules, CLI interfaces, and automated remediation diff generation.

---

## 3. Caveats

1. **Dynamic Runtime Analysis**:
   Static AST analysis cannot inspect dynamic values fetched over network sockets at runtime; runtime validation remains the responsibility of `ai_claim_verifier.py`, `tests/adversarial_zero_mock_telemetry_audit.py`, and the Tri-Lens Visual Swarm.
2. **Canvas Particle Animations**:
   Visual particle systems and canvas animations frequently utilize `Math.random()`. To prevent false positives while maintaining zero-mock rigor, visual animations must be explicitly annotated with `/* @verified-visual-animation */`.
3. **Test File Scope**:
   Test fixtures and mock unit test suites are intentionally excluded from the production zero-mock gate unless `--include-tests` is passed.

---

## 4. Conclusion

The boundary between Permissible Structural Layout and Forbidden Mock Data has been formally specified into an actionable, multi-language AST discrimination rubric. 

The technical blueprints for `06_scripts_and_tooling/scripts/figma_zero_mock_linter.py` and `06_scripts_and_tooling/docs/FIGMA_ZERO_MOCK_SOP.md` are complete, providing a deterministic pre-merge blocking gate (exit code `1` on mock data, `0` on clean layout) and automated remediation patch generation.

---

## 5. Verification Method

To independently verify the discrimination rubric, linter algorithms, and pre-merge blocking specifications:

1. **Inspect Detailed Specification Report**:
   ```bash
   view_file /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_figma_2/report.md
   ```
2. **Verify Existing Static Judge Baseline**:
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/tests/zero_mock_judge/zero_mock_static_judge.py --target-dir /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling
   ```
3. **Verify Monorepo Telemetry Compliance Harness**:
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/tests/adversarial_zero_mock_telemetry_audit.py
   ```
4. **Verify Swarm Truth Audit Specification**:
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/scripts/ai_claim_verifier.py
   ```
