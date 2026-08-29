# Execution Plan: Lauburu Monorepo Application Portfolio Build-Out

## Strategic Objectives
1. Build out every user-facing and commercial application across the entire Lauburu Monorepo to production completeness.
2. Prioritize Flagship Movesense Physiological Readiness App (`01_apps/biometrics/movesense_hub` with `core/`, `dsp/`, `presentation/`, `transport/`).
3. Partition and implement User & Scaling Apps (`01_apps/user_facing_and_scaling/`) and Operator & Dev Cockpits (`01_apps/operator_and_dev/`).
4. Implement Web-TUI Portal on Port 8088 rendering all apps at 120 FPS.
5. Deploy automated Free-Tier Cloud AI Scaffolder (Gemini 2.5 Flash / Cloudflare Workers AI) with strict zero-leak biometric airgap enforcement.
6. Verify Tri-Vault storage health (Obsidian, PySpark data lake, Git) and achieve 100% E2E test suite pass rate without mock data.

## Phase Breakdown

### Phase 0: Survey & Scope Mapping
- Spawn 3 parallel Explorers:
  - Explorer 1 (Biometrics & Movesense): Survey `01_apps/biometrics`, `03_biometrics_and_telemetry`, BLE GATT streams (`261030002013`), Pan-Tompkins DSP, PTT, sleep scoring, LT1/LT2 algorithms.
  - Explorer 2 (App Portfolio & Web-TUI): Survey `01_apps/`, user-facing apps, operator cockpits, Textual TUI setups, Port 8088 portal architecture.
  - Explorer 3 (Scaffolder, Infra & Testability): Survey AI code scaffolding tools, Cloudflare/Gemini APIs, Tri-Vault storage state, testing frameworks.
- Synthesize findings into master `PROJECT.md` with Feature Inventory and Interface Contracts.

### Phase 1: Dual Track Execution
- **Track A (E2E Testing Track)**:
  - Spawn E2E Testing Orchestrator.
  - Establish test framework, harness, runner, and 4-tier test cases (Feature, Boundary, Pairwise, Real-World Workload).
  - Publish `TEST_READY.md`.
- **Track B (Implementation Track)**:
  - **Milestone M1**: Flagship Movesense Hub (`01_apps/biometrics/movesense_hub`)
    - Sub-packages: `core/`, `dsp/`, `presentation/`, `transport/`.
    - 512Hz ECG, Pan-Tompkins, continuous PTT blood pressure, overnight PPG sleep staging, workout classifier, Zone 2 coaching (LT1/LT2 & VO2max).
    - Native Textual TUI + Web-TUI (`/readiness`) + PWA scaffold.
  - **Milestone M2**: User & Scaling Apps Portfolio (`01_apps/user_facing_and_scaling/`)
    - 3D Spatial Grappling (3,044 OPML Tree & MediaPipe 33-landmark skeleton).
    - Gamified Combat Arena.
    - Headless Shopify Storefront ($9/$29/$99/mo subscription & merchandise tiers).
  - **Milestone M3**: Operator & Dev Cockpits (`01_apps/operator_and_dev/`)
    - Canonical Port 9-Screen NOC.
    - SmolAgents Python Duel Sandbox.
    - Standalone Qwen Math Trend Optimizer.
  - **Milestone M4**: Universal Web-TUI Portal (Port 8088)
    - FastAPI + WebSocket server rendering `/readiness`, `/grappling`, `/arena`, `/store`, `/canonical`, `/smolagents`, `/math` at 120 FPS.
  - **Milestone M5**: Free-Tier Cloud AI Scaffolder & Airgap Engine
    - Code generation daemon (Gemini 2.5 Flash Free Tier, Cloudflare Workers AI Free Tier).
    - Fail-closed airgap filter preventing biometric data leakage.

### Phase 2: Final Verification, Adversarial Hardening & Gate
- Phase 2.1: Run 100% E2E test suite across Tiers 1-4.
- Phase 2.2: Tier 5 Adversarial Coverage Hardening via Challengers.
- Phase 2.3: Forensic Auditor integrity audit (zero mock data, strict zero-leak airgap).
- Phase 2.4: Tri-Vault storage verification and final Handoff Report.
