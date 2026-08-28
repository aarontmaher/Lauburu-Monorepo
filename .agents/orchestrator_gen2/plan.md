# Orchestration Master Plan — Generation 2

## Mission
Complete Milestones M3, M4, and M5 for the Lauburu Monorepo Unification and Tri-Vault Reconciliation.

## Phases & Milestones

### Phase 1: Milestone M3 Execution & Verification
1. **Quartz Digital Garden Build**:
   - Verify `01_apps/obsidian_web/content` symlink to `../../obsidian_vault` (or canonical vault path).
   - Execute Quartz build using Node v22: `PATH="/Users/aaron/.nvm/versions/node/v22.23.2/bin:$PATH" npx quartz build` inside `01_apps/obsidian_web`.
   - Verify page count in `01_apps/obsidian_web/public/` (must be >= 260 files/pages).
2. **Desktop Obsidian Vault Visibility**:
   - Inspect `.obsidian/` in `obsidian_vault/` and verify `graph.json`, `app.json`, `core-plugins.json`, `workspace.json`.
3. **01_apps/ Subsystem Builds & Compilation**:
   - Verify compilation and test suite for `01_apps/port_4000_hub` (FastAPI).
   - Verify Next.js apps (`01_apps/zone2_endurance`, `01_apps/grapplingmap_web`).
4. **Milestone M3 Review & Gate Verification**:
   - Reviewer, Challenger, and Forensic Auditor verdicts recorded.

### Phase 2: Milestone M4 Execution & Verification
1. **Zero-Mock Biometrics DSP Audit**:
   - Inspect `03_biometrics_and_telemetry/`, `01_apps/movesense_hub`, `01_apps/zone2_endurance`, `whoop-intelligence.js`, and `lauburu_compute_hub`.
   - Verify 100% genuine Pan-Tompkins QRS, Movesense 512Hz ECG, and Whoop intelligence DSP pipelines.
   - Verify strict absence of fake data arrays, synthetic hardcoded sinusoids, or spoofed heart rates.
2. **Hardware Telemetry Fallback Audit**:
   - Verify that disconnected BLE / network sensors return explicit `null` / `--` states.
3. **Milestone M4 Review & Gate Verification**:
   - Reviewer, Challenger, and Forensic Auditor verdicts recorded.

### Phase 3: Milestone M5 Execution, Adversarial Hardening & Victory Audit
1. **133-Test E2E Test Suite Run**:
   - Run `python3 tests/e2e/run_all_e2e.py --all --json-output reports/e2e_test_report.json`.
   - Verify 100% pass rate across Tiers 1-4.
2. **Tier 5 Adversarial Stress Testing**:
   - Execute adversarial tests: edge-case symlinks, corrupted JSONL injection containment, memory pressure, zero-mock heuristic scanning.
3. **Comprehensive Forensic Victory Audit**:
   - Execute full forensic audit across all 16 features and all constraints.
4. **Final Comprehensive Handoff & Escalation**:
   - Write `handoff.md`.
   - Send final comprehensive completion report to parent (`80a05411-f980-4869-aaee-433e701a845e`).
