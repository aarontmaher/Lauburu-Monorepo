# Project: Lauburu Monorepo Application Portfolio Build-Out

## Architecture

The Lauburu Monorepo application ecosystem is structurally partitioned into two isolated domain tiers, a universal 120 FPS Web-TUI portal, an automated free-tier AI scaffolding engine with fail-closed biometric airgapping, and an integrated Tri-Vault storage system.

```
Lauburu-Monorepo/
├── 01_apps/
│   ├── biometrics/movesense_hub/     # Flagship Movesense Physiological Readiness Suite
│   │   ├── core/                     # State store, event bus, configuration
│   │   ├── dsp/                      # 512Hz Pan-Tompkins ECG, Kamath filter, PTT BP, sleep score, LT1/LT2
│   │   ├── presentation/             # Textual TUI, Web-TUI bridge, Canvas oscilloscope PWA, Flutter
│   │   └── transport/                # Bleak GATT daemon (Movesense 261030002013), Web Bluetooth bridge
│   ├── user_facing_and_scaling/      # Domain 1: User & Scaling Consumer/Pro Applications
│   │   ├── movesense_readiness_hub/  # Symlink/Package root for Movesense Suite
│   │   ├── spatial_grappling_3d/     # 3,044 OPML Tree & MediaPipe 33-landmark 3D kinematic skeleton
│   │   ├── combat_arena/             # Hermes vs LuCI Combat Arena (120 FPS power bar, pulse gauge)
│   │   └── shopify_storefront/       # Headless Shopify Storefront ($9/$29/$99/mo tiers, sensor bundles)
│   ├── operator_and_dev/             # Domain 2: Operator & Developer Cockpits
│   │   ├── canonical_port/           # 9-Screen Stability NOC (7 physical nodes, 108GB RAM pool)
│   │   ├── smolagents_duel_sandbox/  # Python Duel Sandbox (Code-as-action tool registry)
│   │   └── qwen_math_trend_optimizer/# Standalone Math Optimizer (Latency proofs, LoRA SFT/DPO logging)
│   └── web_tui_portal/               # Port 8088 FastAPI + WebSocket 120 FPS PTY Portal
├── 00_core_infrastructure/           # Cloudflare Worker Airgap Firewall, Self-Healing Hub (Port 18802)
├── 03_biometrics_and_telemetry/      # Shared local high-performance DSP math libraries (Zero Cloud Leak)
├── 04_data_and_memory/               # PySpark Data Lake, 24/7 LoRA Datasets, Qdrant Vector DB
├── 06_scripts_and_tooling/           # Automated Free-Tier AI Scaffolder (Gemini Flash / Cloudflare Workers AI)
├── obsidian_vault/                   # Obsidian Knowledge Core (Index.md master Wikilinks)
└── tests/e2e/                        # Comprehensive 4-Tier Opaque-Box E2E Test Suite
```

---

## Feature Inventory

Every feature identified during requirements analysis and codebase survey is inventoried below with its assigned milestone:

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | 512Hz Pan-Tompkins ECG DSP | 4th-order Butterworth (0.5-40Hz), 5-pt derivative, squaring, 150ms MWI, dual-adaptive threshold QRS detector with 200ms refractory lockout | M1 | ORIGINAL_REQUEST §R1 |
| F02 | Kamath 20% RR Filter | Strict 20% clinical RR outlier filter for beat-to-beat validation | M1 | ORIGINAL_REQUEST §R1 |
| F03 | Continuous PTT Blood Pressure | Hughes-Bramwell arterial wave inversion model estimating SBP/DBP/MAP from Pulse Transit Time | M1 | ORIGINAL_REQUEST §R1 |
| F04 | Overnight Sleep Staging & Score | 30s epoch staging (`AWAKE`, `DEEP`, `REM`, `LIGHT`), nocturnal dipping %, and 0-100 composite recovery score | M1 | ORIGINAL_REQUEST §R1 |
| F05 | Zone 2 Cardio Coaching | DFA-alpha1 ($s \in [4, 16]$ beats), LT1 (0.75) / LT2 (0.50) thresholds, and Uth-Sørensen VO2max pacing | M1 | ORIGINAL_REQUEST §R1 |
| F06 | Movesense BLE GATT Ingestion | Bleak Python & Web Bluetooth ingestion for Movesense sensor `261030002013` (MDS 2.0 & SIG HRS) | M1 | ORIGINAL_REQUEST §R1 |
| F07 | Multi-Platform Readiness Clients | Native Textual TUI, Web-TUI `/readiness` adapter, Next.js Canvas oscilloscope PWA, Flutter mobile client | M1 | ORIGINAL_REQUEST §R1 |
| F08 | Movesense Hub Modular Package | Standardized subpackages (`core/`, `dsp/`, `presentation/`, `transport/`) in `01_apps/biometrics/movesense_hub` | M1 | ORIGINAL_REQUEST §R1 |
| F09 | 3D Spatial Grappling Kinematics | 3,044-node OPML mindmap tree mapped to 10m x 10m tatami grid with MediaPipe 33-landmark 3D skeleton | M2 | ORIGINAL_REQUEST §R2 |
| F10 | Gamified Combat Arena | 4 game modes, animated 120 FPS compute power bar, live Movesense pulse gauge, RAG voice TTS | M2 | ORIGINAL_REQUEST §R2 |
| F11 | Headless Shopify Storefront | $9 Athlete, $29 Pro, $99 Gym Team/mo tiers, Movesense HR+ hardware bundles, GraphQL client | M2 | ORIGINAL_REQUEST §R2 |
| F12 | Canonical Port 9-Screen NOC | 9-screen stability hierarchy monitoring 7 physical nodes, 108GB RAM pool, model mesh, AI debate | M3 | ORIGINAL_REQUEST §R2 |
| F13 | SmolAgents Python Duel Sandbox | Python code-as-action tool sandbox executing network probes, latency telemetry, and filter benchmarks | M3 | ORIGINAL_REQUEST §R2 |
| F14 | Standalone Qwen Math Optimizer | Autonomous background analytics computing latency proofs, BQL depths, cardiac coherence, LoRA datasets | M3 | ORIGINAL_REQUEST §R2 |
| F15 | Universal Web-TUI Portal (Port 8088) | FastAPI + WebSocket async PTY engine rendering all 7 apps at 120 FPS via xterm.js WebGL | M4 | ORIGINAL_REQUEST §R2 |
| F16 | Automated Free-Tier Cloud AI Scaffolder | Gemini 2.5 Flash Free Tier & Cloudflare Workers AI code generation daemon for tests, UI boilerplate, docs | M5 | ORIGINAL_REQUEST §R3 |
| F17 | Strict Fail-Closed Airgap Sentinel | Perimeter and local firewall ensuring 0% biometric data or sensor packets leave local hardware | M5 | ORIGINAL_REQUEST §R3 |
| F18 | Tri-Vault Storage Invariant Health | Healthy Obsidian Vault (`Index.md`), PySpark Data Lake ($\ge 10.0$ GB free), clean Git repository | M6 | RULE[user_global] §6 |
| F19 | 100% 4-Tier E2E Test Suite Pass | Opaque-box E2E test harness running Tiers 1-4 with zero failures | M6 | Acceptance Criteria |
| F20 | Tier 5 Adversarial Coverage Hardening | White-box adversarial testing, edge-case probing, and zero-mock Rule #0 compliance audit | M6 | Acceptance Criteria |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Master 4-tier E2E test suite (Tiers 1-4), harness runner, `TEST_READY.md` | none | DONE (184/184 tests passing) |
| M1 | Flagship Movesense Physiological Readiness Suite | Modularize `01_apps/biometrics/movesense_hub` into `core/`, `dsp/`, `presentation/`, `transport/`; integrate 512Hz ECG, PTT BP, sleep staging, Zone 2 coaching, and multi-platform clients | none | DONE (102 biometrics tests passing, gate certified) |
| M2 | User & Scaling Apps Portfolio Separation | Restructure and verify `01_apps/user_facing_and_scaling/` (Movesense Hub, 3D Spatial Grappling, Combat Arena, Shopify Storefront) | M1 | PLANNED |
| M3 | Operator & Dev Cockpits Portfolio Separation | Restructure and verify `01_apps/operator_and_dev/` (Canonical Port 9-Screen NOC, SmolAgents Duel Sandbox, Qwen Math Optimizer) | none | PLANNED |
| M4 | Universal Web-TUI Portal (Port 8088) | Implement `01_apps/web_tui_portal/serve_portal.py` serving all 7 apps at 120 FPS with auto-reclaim and PTY process isolation | M1, M2, M3 | PLANNED |
| M5 | Free-Tier AI Scaffolder & Airgap Engine | Deploy Gemini 2.5 Flash / Cloudflare Workers AI scaffolding daemon with strict fail-closed airgap filter | none | PLANNED |
| M6 | Final Verification, Adversarial Hardening & Audit | 100% E2E Pass across Tiers 1-4, Tier 5 Adversarial Hardening via Challengers, Forensic Integrity Audit, and Tri-Vault Verification | M1, M2, M3, M4, M5, E2E | PLANNED |

---

## Interface Contracts

### 1. Movesense BLE GATT & DSP Pipeline Contract
- **GATT Characteristics**: `0x2A37` (SIG Heart Rate Measurement), `34800001-7185-4d5d-b431-b30e393d9e05` (Movesense MDS 2.0 Whiteboard).
- **Data Types**:
  - `RawEcgFrame`: `(timestamp_us: int, sample_rate_hz: int, samples_mv: List[float])`
  - `QrsDetectionResult`: `(r_peaks: List[int], rr_intervals_ms: List[float], filtered_rr_ms: List[float], hr_bpm: float, rmssd_ms: float)`
  - `PttBloodPressure`: `(sbp_mmhg: float, dbp_mmhg: float, map_mmhg: float, ptt_ms: float)`
  - `SleepStagingResult`: `(epoch_stages: List[str], sleep_score_100: int, deep_pct: float, rem_pct: float, efficiency_pct: float, dip_pct: float)`
  - `Zone2CardioResult`: `(dfa_alpha1: float, current_zone: str, lt1_hr: float, lt2_hr: float, vo2max_ml_kg_min: float)`
- **Rule #0 Guarantee**: In disconnected state, emits `WAITING_FOR_SENSOR` and `null` values. Zero mock arrays.

### 2. Two-Domain Applications Contract
- **User & Scaling Apps (`01_apps/user_facing_and_scaling/`)**:
  - `movesense_readiness_hub`: Entrypoint `movesense_readiness_hub.presentation.tui:run_app`
  - `spatial_grappling_3d`: Entrypoint `spatial_grappling_3d.presentation.engine:SpatialGrapplingMapEngine`
  - `combat_arena`: Entrypoint `combat_arena.presentation.arena:run_arena`
  - `shopify_storefront`: Entrypoint `shopify_storefront.presentation.store:run_storefront`
- **Operator & Dev Cockpits (`01_apps/operator_and_dev/`)**:
  - `canonical_port`: Entrypoint `canonical_port.views.dashboard:run_canonical`
  - `smolagents_duel_sandbox`: Entrypoint `smolagents_duel_sandbox.presentation.sandbox:run_sandbox`
  - `qwen_math_trend_optimizer`: Entrypoint `qwen_math_trend_optimizer.presentation.optimizer:run_optimizer`

### 3. Web-TUI Portal Contract (Port 8088)
- **Routes**:
  - `/` -> Landing page with visual app grid and 120 FPS WebGL launch cards
  - `/readiness` -> WebSocket PTY bridge to Movesense Readiness Hub
  - `/grappling` -> WebSocket PTY bridge to 3D Spatial Grappling Map
  - `/arena` -> WebSocket PTY bridge to Combat Arena
  - `/store` -> WebSocket PTY bridge to Shopify Storefront
  - `/canonical` -> WebSocket PTY bridge to Canonical 9-Screen NOC
  - `/smolagents` -> WebSocket PTY bridge to SmolAgents Sandbox
  - `/math` -> WebSocket PTY bridge to Qwen Math Optimizer
- **WebSocket Protocol**: Binary PTY stream over `ws://127.0.0.1:8088/ws/{app_name}`.

### 4. Cloud AI Scaffolder & Airgap Sentinel Contract
- **Providers**: `gemini_free` (1,500 RPD), `cloudflare_ai` (1,000 RPD), `julien_ai` (300 RPD), `local_mesh` (Sovereign fallback).
- **Airgap Filter**: Fail-closed regex intercepting all requests matching `/^\/(?:api|v1|ws)\/(?:biometrics|movesense|ecg|ptt|ppg|sleep_staging|raw_rr|heart_rate_raw)(?:\/.*)?$/i` and headers `x-lauburu-biometrics-egress`. Redacts any biometric keys to `[AIRGAP_REDACTED: LOCAL_HARDWARE_ONLY]`.

---

## Code Layout

```
Lauburu-Monorepo/
├── 01_apps/
│   ├── biometrics/movesense_hub/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── models.py
│   │   ├── dsp/
│   │   │   ├── __init__.py
│   │   │   ├── pan_tompkins.py
│   │   │   ├── hemodynamics_bp.py
│   │   │   ├── sleep_scoring.py
│   │   │   └── zone2_coaching.py
│   │   ├── presentation/
│   │   │   ├── __init__.py
│   │   │   ├── tui.py
│   │   │   └── web_adapter.py
│   │   └── transport/
│   │       ├── __init__.py
│   │       ├── bleak_daemon.py
│   │       └── web_ble_bridge.py
│   ├── user_facing_and_scaling/
│   │   ├── movesense_readiness_hub/
│   │   ├── spatial_grappling_3d/
│   │   ├── combat_arena/
│   │   └── shopify_storefront/
│   ├── operator_and_dev/
│   │   ├── canonical_port/
│   │   ├── smolagents_duel_sandbox/
│   │   └── qwen_math_trend_optimizer/
│   └── web_tui_portal/
│       ├── __init__.py
│       └── serve_portal.py
```
