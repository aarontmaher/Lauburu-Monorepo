# Project: Unified Lauburu Front-Facing App Architecture & Multi-Mode Game Arena

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 100% LOCAL BIOMETRICS AIRGAP BOUNDARY                           │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Movesense HR+ 512Hz / 128Hz BLE]  ──(GATT 0x2A37 / MDS 2.0)──►  [Apple Silicon Metal GPU / CPU]│
│                                                                                                 │
│  LOCAL DSP PIPELINE (127.0.0.1:8000 / 127.0.0.1:4000 / 127.0.0.1:5001):                        │
│  1. 4th-Order Butterworth 0.5–40 Hz Bandpass Filter                                             │
│  2. 5-Point Derivative Filter & Non-linear Squaring (Pan-Tompkins 1985)                        │
│  3. 150ms Moving Window Integrator (MWI) & Dual-Threshold Adaptive Peak Searchback              │
│  4. Kamath et al. 2004 20% Clinical RR Artifact Filter (|RR_i - RR_{i-1}| / RR_{i-1} <= 0.20)  │
│  5. Root Mean Square of Successive Differences (RMSSD) Math                                     │
│  6. 120s Rolling Detrended Fluctuation Analysis (DFA-alpha1, LT1 @ 0.75, LT2 @ 0.50)           │
│  7. Pulse Transit Time (PTT) Continuous Hemodynamic Blood Pressure Inversion:                  │
│     • SBP = 120.0 + 0.45 * (200 - PTT) + 0.15 * (HR - 70)                                       │
│     • DBP = 80.0 + 0.25 * (200 - PTT) + 0.08 * (HR - 70)                                        │
│     • MAP = (SBP + 2 * DBP) / 3.0                                                               │
│  8. Overnight Optical PPG Sleep Staging (Deep, REM, Light, Awake) & Sleep Score (0-100)        │
│  9. Uth-Sørensen VO2max Estimation: 15.3 * (HR_max / HR_rest)                                  │
│                                                                                                 │
│  LOCAL PERSISTENCE ONLY:                                                                        │
│  • PySpark JSONL & Delta Lake Parquet (/Users/aaron/DFS_UNIFIED/lora_datasets/)                 │
│  • Obsidian Vault Health Graph (/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/)      │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                  STRICT ISOLATION FIREWALL                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│  CLOUD AI & EDGE WORKERS (Cloudflare Workers AI, Gemini 3.7 Flash, Supabase, Railway):         │
│  • STRICTLY ZERO RAW BIOMETRIC DATA ALLOWED.                                                    │
│  • Redacts all raw athlete physiological metrics before egress.                                 │
│  • Handles UI scaffolding, PWA asset delivery, WebGPU WGSL shaders, and Three.js 3D Tatami.    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Frontend PWA Scaffolding & Manifest | Offline ServiceWorker caching, responsive PWA manifests for mobile/desktop | M1 | Survey R1 |
| 2 | Three.js 3D Tatami & Kinematics Graph | 955+ OPML nodes interactive 3D map, WebGPU/WebGL renderers, raycasting | M1 | Survey R1 |
| 3 | TailwindCSS & Cross-Platform UI | Responsive Tailwind UI components, WCAG 2.1 AA accessible charts, Flutter templates | M1 | Survey R1 |
| 4 | Strict 100% Local Airgap Protection | Strict zero-biometrics firewall on Cloudflare/external endpoints, 127.0.0.1 airgap | M1 | Survey R1 |
| 5 | Bicep ECG 512Hz Pan-Tompkins DSP | Butterworth bandpass, 5-pt derivative, 150ms MWI, dual-threshold peak search | M2 | Survey R2 |
| 6 | Kamath 20% Artifact Filter & RMSSD | Kamath 2004 20% RR interval filter, microsecond precision, RMSSD calculation | M2 | Survey R2 |
| 7 | Pulse Transit Time (PTT) Continuous BP | Hemodynamic PTT inversion model calculating SBP, DBP, MAP in real time | M2 | Survey R2 |
| 8 | Overnight PPG Sleep Staging & Score | Deep, REM, Light, Awake staging, 0-100 recovery score, nocturnal dipping | M2 | Survey R2 |
| 9 | Auto Workout Detect & LT1/LT2 / VO2max | Real-time DFA-a1 LT1 (0.75), LT2 (0.50), HR ratio VO2max (15.3 * HR_max / HR_rest) | M2 | Survey R2 |
| 10 | Rule #0 Zero-Mock Enforcement | Zero fake arrays; clean WAITING_FOR_SENSOR / null states when offline | M2 | Survey R2 |
| 11 | SmolAgents Sandboxed Python Duel | Faction leaders (Hermes 3 / Qwen Red, LuCI / Sentinel Blue) write & run Python code | M3 | Survey R3 |
| 12 | Canonical 4 Selectable Game Modes | EDGE_ORCHESTRATOR_CLASSIC, SMOLAGENTS_PYTHON_DUEL, MULTI_MODEL_AGI_SWARM, AIRGAP_MESH_VS_CLOUD_CHAOS | M3 | Survey R3 |
| 13 | Telemetry HUD Tactical Objective Summaries | Active plain-language statements: "What is each team currently trying to do?" | M3 | Survey R3 |
| 14 | Standalone & Embedded TUI Synchronization | Sync standalone tui_live_arena_dev.py with Canonical LiveArenaDevScreen 4-mode engine | M3 | Survey R3 |
| 15 | 100% E2E Test Suite Pass | Opaque-box E2E test verification across all 14 features (Tiers 1-4) | M4 | Dual Track |
| 16 | Tier 5 Adversarial Coverage Hardening | White-box stress testing, chaos injections, and forensic audit verification | M4 | Final Milestone |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Frontend PWA, 3D Tatami & Airgap Scaffolding | Frontend PWA scaffolding, Three.js 3D Tatami, TailwindCSS tokens, 100% local airgap policy | None | PLANNED |
| M2 | Movesense Physiological Readiness & 512Hz DSP | 512Hz Pan-Tompkins QRS, Kamath RR filter, RMSSD, PTT BP inversion, Sleep staging, LT1/LT2, VO2max | None | PLANNED |
| M3 | SmolAgents Autonomous Arena & 4-Mode TUI Engine | Sandboxed Python code execution for Red/Blue leads, 4 game modes, TUI Tactical Objective HUD | None | PLANNED |
| M4 | Final Milestone: 100% E2E Pass & Tier 5 Hardening | Execute full E2E Test Suite (Tiers 1-4) + Tier 5 Adversarial Coverage Hardening + Forensic Audit | M1, M2, M3, E2E Track | PLANNED |

## Interface Contracts
### Frontend UI (`01_apps/`, `webapp/`) ↔ Local Biometrics Airgap (`03_biometrics_and_telemetry/`)
- Endpoint: `http://127.0.0.1:8000/api/movesense/telemetry` & `ws://127.0.0.1:8000/ws/ingest`
- Input: Request for live telemetry / readiness score
- Response Schema:
  ```json
  {
    "status": "STREAMING" | "WAITING_FOR_SENSOR",
    "heart_rate_bpm": float | null,
    "rmssd_ms": float | null,
    "dfa_alpha1": float | null,
    "ptt_blood_pressure": {
      "systolic_bp_mmhg": float | null,
      "diastolic_bp_mmhg": float | null,
      "map_mmhg": float | null
    },
    "sleep_recovery": {
      "sleep_score_pct": int | null,
      "deep_sleep_pct": float | null,
      "rem_sleep_pct": float | null
    },
    "cardiorespiratory": {
      "lt1_threshold_bpm": float | null,
      "lt2_threshold_bpm": float | null,
      "vo2max_estimate": float | null,
      "activity_state": string | null
    }
  }
  ```

### SmolAgents Arena Engine (`05_agents_and_swarms/`) ↔ Canonical TUI HUD (`01_apps/canonical_port/tui/`)
- Module: `SmolAgentsArenaHub` in `smolagents_engine/smolagents_arena_hub.py`
- Methods:
  - `run_arena_tick(active_mode: str) -> dict`
  - `tactical_intent_summary` output schema:
    ```json
    {
      "red_faction_intent": string,
      "blue_faction_intent": string,
      "user_biological_state": string,
      "combat_narrative": string
    }
    ```

## Code Layout
- `01_apps/biometrics/zone2_endurance/` — Next.js 14 Web Bluetooth Zone 2 App
- `webapp/` — Three.js 3D Tatami Grappling Map PWA
- `00_core_infrastructure/self_healing_hub/frontend/` — WebGPU WGSL Tatami Particle Visualizer
- `00_core_infrastructure/cloudflare_worker/src/worker.ts` — Zero-Biometric Cloud Isolation Worker
- `03_biometrics_and_telemetry/pan_tompkins_dsp.py` — 512Hz Pan-Tompkins QRS, Kamath filter, RMSSD, DFA-a1, PTT BP
- `03_biometrics_and_telemetry/movesense_readiness_suite.py` — Readiness, Sleep Staging, LT1/LT2, VO2max
- `05_agents_and_swarms/smolagents_engine/smolagents_arena_hub.py` — SmolAgents Arena Hub & 4 Game Modes
- `01_apps/canonical_port/tui/screens/live_arena_dev_screen.py` — Canonical TUI Live Arena Dev Screen
- `01_apps/canonical_port/tui/tui_live_arena_dev.py` — Standalone Live Arena TUI script
- `05_agents_and_swarms/genetic_moe/genetic_moe_ai_router.py` — Mode 3 Genetic MoE AI Router
- `tests/e2e/` — Opaque-box E2E Test Suite (Tiers 1-4)
