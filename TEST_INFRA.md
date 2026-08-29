# Unified Lauburu Front-Facing App Architecture & Multi-Mode Game Arena — 4-Tier Test Infrastructure Specification

**Document Version:** 4.0.0-CANONICAL  
**Date:** 2026-08-29T19:15:00Z  
**Author:** E2E Testing Specialist / Test Architect Lead (`teamwork_preview_test_writer`)  
**Target System:** Unified Lauburu Front-Facing App Architecture & Multi-Mode Game Arena (`ORIGINAL_REQUEST.md`, `PROJECT.md`)  
**Repository:** `Lauburu-Monorepo`  
**Test Suite:** `tests/e2e/test_tier1_feature_coverage.py`, `tests/e2e/test_tier2_boundary_corner.py`, `tests/e2e/test_tier3_pairwise_combinations.py`, `tests/e2e/test_tier4_real_world_scenarios.py`  
**Master Runner:** `python3 tests/e2e/run_all_e2e_tests.py --all` / `python3 -m pytest tests/e2e/test_tier*.py`

---

## 1. Executive Test Strategy & Opaque-Box Methodology

The **Unified Lauburu Front-Facing App Architecture & Multi-Mode Game Arena** implements a strict architectural division:
1. **Cloud-Assisted Frontend PWA & 3D Tatami Visualization:** Delivers responsive TailwindCSS components, offline ServiceWorker caching, Three.js 955+ node OPML grappling kinematics mapping, and WebGPU WGSL shaders.
2. **100% Local Physiological Biometrics Airgap:** Locks all raw Movesense 512Hz ECG streams, optical PPG waveforms, microsecond R-R intervals, Pan-Tompkins DSP, Pulse Transit Time (PTT) continuous blood pressure inversion, overnight sleep staging (Deep, REM, Light, Awake), and cardiorespiratory thresholds (LT1, LT2, VO2max) to local Apple Silicon Metal GPU and mesh hardware (`127.0.0.1`).
3. **SmolAgents Autonomous Python Code-Execution Arena & 4-Mode TUI Engine:** Faction leaders (Hermes 3 Red Lead, LuCI OpenWrt Blue Lead) write and execute sandboxed Python code across 4 selectable game modes with active Telemetry HUD Tactical Objective Summaries.

To ensure empirical validity, strict zero-simulated data compliance (Rule #0), mathematical rigor across signal processing equations, and rock-solid airgap boundaries, this test infrastructure enforces an exhaustive **4-Tier Opaque-Box Testing Hierarchy** (184 total tests).

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│               UNIFIED LAUBURU FRONT-FACING & GAME ARENA — 4-TIER E2E TEST HIERARCHY                    │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                        │
│   TIER 1: FEATURE COVERAGE (5 Tests per Feature across F01 - F16 = 80 Total Tests)                     │
│   • F01: Frontend PWA Scaffolding & Manifest (Manifest schema, standalone display, SW offline caching) │
│   • F02: Three.js 3D Tatami & Kinematics Graph (955+ OPML nodes, 3D mapping, raycasting selection)     │
│   • F03: TailwindCSS & Cross-Platform UI (WCAG 2.1 AA 4.5:1 contrast, dark tokens, ARIA labels)        │
│   • F04: Strict 100% Local Airgap Protection (Cloudflare zero-biometrics firewall, egress inspection)  │
│   • F05: Bicep ECG 512Hz Pan-Tompkins DSP (Butterworth 0.5-40Hz, 5-pt derivative, 150ms MWI, peaks)    │
│   • F06: Kamath 20% Artifact Filter & RMSSD Math (Ectopic filter, microsecond resolution, RMSSD)       │
│   • F07: Pulse Transit Time (PTT) Continuous BP (Hemodynamic SBP/DBP/MAP inversion, arterial bounds)   │
│   • F08: Overnight PPG Sleep Staging & Score (Deep/REM/Light/Awake 100% sum, 0-100 score, dipping)     │
│   • F09: Auto Workout Detect & LT1/LT2 / VO2max (HRmax zones, DFA-a1 0.75/0.50, Uth-Sørensen VO2max)   │
│   • F10: Rule #0 Zero-Mock Enforcement (WAITING_FOR_SENSOR, null state offline, zero synthetic arrays) │
│   • F11: SmolAgents Sandboxed Python Duel (Red exploit & Blue shield Python execution, isolated scope)│
│   • F12: Canonical 4 Selectable Game Modes (Classic, Duel, Genetic MoE Swarm, Cloud Chaos)             │
│   • F13: Telemetry HUD Tactical Objective Summaries (Plain-language intents, biological state string)  │
│   • F14: Standalone & Embedded TUI Synchronization (LiveArenaDevScreen, Rich panels, 1-key actions)    │
│   • F15: 100% E2E Test Suite Pass (Multi-tier execution harness, JSON report, fast-path health check)  │
│   • F16: Tier 5 Adversarial Coverage Hardening (NaN/Inf floats, corrupted JSONL, 64MB burst bounds)    │
│                                                                                                        │
│   TIER 2: BOUNDARY VALUE ANALYSIS & CORNER CASES (5 Tests per Feature = 80 Total Tests)               │
│   • F01 - F16 Boundaries: Isoelectric ECG flatlines, zero/extreme PTT, HR bounds (25-240 BPM),         │
│     WCAG contrast limits (21:1 to 1:1), 0-node OPML, NaN floats, rapid mode cycling, empty buffers     │
│                                                                                                        │
│   TIER 3: CROSS-FEATURE PAIRWISE COMBINATIONS (16 Combinatorial Tests)                                 │
│   • P01 - P16: PWA x Airgap, OPML x Tailwind, Pan-Tompkins x Kamath, Kamath x PTT BP, PTT BP x Sleep, │
│     Sleep x Workout, DFA-a1 x Rule #0, SmolAgents x 4 Modes, 4 Modes x Tactical HUD, etc.              │
│                                                                                                        │
│   TIER 4: REAL-WORLD APPLICATION SCENARIOS (8 Comprehensive Workload Scenarios)                        │
│   • S1: End-to-End 512Hz ECG Ingestion -> Pan-Tompkins -> Kamath -> RMSSD -> Zone 2 Feedback           │
│   • S2: Overnight Sleep Staging -> Autonomic Recovery Score -> LoRA Dataset Export                     │
│   • S3: High-Intensity Threshold Workout -> DFA-a1 -> Hemodynamic PTT BP Inversion                     │
│   • S4: Real-time SmolAgents Red vs. Blue Sandboxed Python Duel -> TUI HUD Sync                        │
│   • S5: Hardware Disconnection & Rule #0 Zero-Mock Fallback & Clean Resumption                         │
│   • S6: Mode 3 Genetic MoE AI Router Dynamic Evolution & Local Model Routing                           │
│   • S7: Full WebApp Frontend Lifecycle: PWA Manifest -> 955+ OPML Kinematics -> Tailwind UI           │
│   • S8: Strict Cloudflare Worker Zero-Biometric Egress Isolation & Redaction Audit                     │
│                                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Requirement & Test Matrix Breakdown

### Tier 1: Feature Coverage (Category-Partition Testing across F01–F16)

Every feature in `PROJECT.md` is covered by exactly 5 distinct, rigorously verified test cases (80 total tests):

| Feature ID | Feature Name & Scope | Minimum Tests | Implemented Tests | Primary Verification Objective |
| :--- | :--- | :--- | :--- | :--- |
| **F01** | Frontend PWA Scaffolding & Manifest | ≥5 | 5 | Validates W3C Web App Manifest schema, standalone display mode, theme colors, icon sizes (>=192px), and ServiceWorker offline caching. |
| **F02** | Three.js 3D Tatami & Kinematics Graph | ≥5 | 5 | Validates $\ge 955$ node OPML martial arts tree parsing, 3D coordinate spherical projection bounds, raycasting intersection hit detection, and WebGPU WGSL canvas coexistence. |
| **F03** | TailwindCSS & Cross-Platform UI | ≥5 | 5 | Validates Tailwind theme tokens, WCAG 2.1 AA text contrast ($\ge 4.5:1$), UI component contrast ($\ge 3.0:1$), semantic ARIA tags, and responsive breakpoints. |
| **F04** | Strict 100% Local Airgap Protection | ≥5 | 5 | Validates Cloudflare Worker zero-biometrics firewall, egress payload sanitization (detects and strips raw ECG/PPG/RR arrays), and 127.0.0.1 airgap binding. |
| **F05** | Bicep ECG 512Hz Pan-Tompkins DSP | ≥5 | 5 | Validates Butterworth 0.5-40Hz bandpass filtering, 5-point derivative slope operator, squaring energy transform, 150ms MWI window, and adaptive dual-threshold R-peak detection. |
| **F06** | Kamath 20% Artifact Filter & RMSSD | ≥5 | 5 | Validates Kamath 2004 clinical 20% RR filter ($\frac{\|RR_i - RR_{i-1}\|}{RR_{i-1}} \le 0.20$), ectopic burst interpolation, exact RMSSD math, and microsecond precision. |
| **F07** | Pulse Transit Time (PTT) Continuous BP | ≥5 | 5 | Validates Hemodynamic PTT BP inversion formula ($SBP = 120 + 0.45(200-PTT) + 0.15(HR-70)$, $DBP = 80 + 0.25(200-PTT) + 0.08(HR-70)$, $MAP = \frac{SBP + 2DBP}{3}$), bounds, and null safety. |
| **F08** | Overnight PPG Sleep Staging & Score | ≥5 | 5 | Validates 0-100 composite sleep score from nocturnal RMSSD + HR, recovery classification (Green/Yellow/Red), and Deep/REM/Light/Awake stage proportions summing to 100.0%. |
| **F09** | Auto Workout Detect & LT1/LT2 / VO2max | ≥5 | 5 | Validates training zones by % HRmax, DFA-alpha1 LT1 (0.75) and LT2 (0.50) domains, and Uth-Sørensen VO2max estimation ($15.3 \times \frac{HR_{max}}{HR_{rest}}$). |
| **F10** | Rule #0 Zero-Mock Enforcement | ≥5 | 5 | Validates clean `WAITING_FOR_SENSOR` status and null metrics when sensor is disconnected; enforces zero fake or hardcoded arrays. |
| **F11** | SmolAgents Sandboxed Python Duel | ≥5 | 5 | Validates Hermes 3 Red exploit generation, LuCI Blue defense shield generation, isolated execution scope, and result structure preservation. |
| **F12** | Canonical 4 Selectable Game Modes | ≥5 | 5 | Validates Classic, Python Duel, Genetic MoE Swarm, and Airgap vs. Cloud Chaos mode transitions, router prompt routing, and state persistence. |
| **F13** | Telemetry HUD Tactical Objective Summaries | ≥5 | 5 | Validates `tactical_intent_summary` schema conformance (`red_faction_intent`, `blue_faction_intent`, `user_biological_state`, `combat_narrative`) in plain language. |
| **F14** | Standalone & Embedded TUI Synchronization | ≥5 | 5 | Validates shared `smolagents_arena_state.json` file synchronization, Red/Blue graphical map panels, dynamic power bar, and 1-key interactive bindings. |
| **F15** | 100% E2E Test Suite Pass | ≥5 | 5 | Validates test suite discovery, multi-tier execution harness, structured JSON export, exit code 0 enforcement, and fast-path storage health check. |
| **F16** | Tier 5 Adversarial Coverage Hardening | ≥5 | 5 | Validates resilience to NaN/Inf floats, corrupted JSON state recovery, extreme clipping, rapid 50-cycle mode switching, and atomic LoRA dataset logging. |
| **TOTAL** | **Tier 1 Feature Tests** | **≥80** | **80** | **Full Feature Coverage Across All 16 Features** |

---

## 3. Tier 2: Boundary Value Analysis & Corner Cases (80 Tests)

Validates extreme limits, mathematical edge conditions, corrupted formats, and hardware singularities (5 tests x 16 features = 80 tests):

- **F01 Boundaries:** Empty manifest dict `{}`, empty icons list `[]`, missing file path, relative `start_url`, invalid display mode fallback.
- **F02 Boundaries:** Single root OPML node, empty `<body>` (0 nodes), depth=15 coordinate scaling, raycasting complete miss, XML entity escaping (`&amp;`, `&lt;`).
- **F03 Boundaries:** Maximal 21.0:1 contrast (#000 vs #FFF), minimal 1.0:1 contrast, 3-digit shorthand hex (#FFF), missing ARIA label fallback, ultra-narrow 320px viewport scaling.
- **F04 Boundaries:** Large raw numeric arrays (>20 floats) heuristic catch, nested list of dicts with raw keys, mixed-case forbidden keys (`RAW_ECG`), scalar metrics allowed, empty dict safe pass.
- **F05 Boundaries:** Isoelectric flatline (0.0uV) detects 0 peaks, buffer <0.5s returns empty arrays, DC bias (+10,000uV) baseline removal, 50Hz sample rate bound, 2048Hz sample rate bound.
- **F06 Boundaries:** Single RR interval ($n=1$) returns 0 artifacts, zero/negative interval detection, constant identical intervals (RMSSD = 0.0ms), 100% corrupted alternating burst, $n=2$ minimal valid calculation.
- **F07 Boundaries:** Zero/negative PTT returns None, prolonged PTT (1000ms) clamps SBP $\ge 80$, shortened PTT (10ms) clamps SBP $\le 220$, bradycardia HR=25 BPM, tachycardia HR=240 BPM.
- **F08 Boundaries:** High stress sleep score clamped to 0, peak recovery sleep score clamped to 100, score 75 boundary transition, negative RMSSD clamped $\ge 0$, sleeping HR variation scaling.
- **F09 Boundaries:** HR=0 BPM maps to Rest, HR > HRmax maps to Maximal Effort, series <4 points DFA returns None, constant series bounded [0.4, 1.5], hr_rest $\le 40$ clamped in VO2max.
- **F10 Boundaries:** Empty JSON file string handling, non-dict JSON stream handling, missing telemetry file fallback, partial keys null fill, `connected=False` overrides stale telemetry.
- **F11 Boundaries:** Empty code string execution, syntax error in agent code isolated, division by zero isolated, special characters in target node, complex nested dict return structure.
- **F12 Boundaries:** Unrecognized mode string rejected, empty mode string rejected, None mode value rejected, unseen prompt domain routes to valid expert, routing weights normalized to 1.0.
- **F13 Boundaries:** Missing intent key fails schema, empty whitespace intent string fails, non-string narrative type fails, unicode emojis (🔴, 🛡️) pass schema, 5,000 char long narrative preserved.
- **F14 Boundaries:** Graphical map renders at HR=0, graphical map renders at HR=200, 0% Red power bar, 100% Red power bar, unknown 1-key input command ignored.
- **F15 Boundaries:** Empty test case class handling, JSON report creates missing parent directories, simulated 0 GB disk space fails health check, missing vault fails health check, microsecond timer resolution.
- **F16 Boundaries:** Signal with all NaN floats handled safely, signal with all Inf floats handled safely, corrupted binary state recovery, 64MB burst bounds, malformed JSONL line skipped.

---

## 4. Tier 3: Cross-Feature Pairwise Combinations (16 Tests)

Validates multi-module integration contracts across the front-facing and backend pipelines:

1. **P01 (F01 x F04):** Offline PWA ServiceWorker serves cached UI bundle while strict airgap firewall intercepts and strips outbound raw physiological arrays.
2. **P02 (F02 x F03):** 955+ Node OPML Grappling Kinematics tree is colored using WCAG 2.1 AA compliant tokens (Guard: #38BDF8, Mount: #34D399, Back: #F87171).
3. **P03 (F05 x F06):** 512Hz raw ECG stream processed through Pan-Tompkins QRS detector generates R-peaks that pass cleanly through the Kamath 20% clinical artifact filter.
4. **P04 (F06 x F07):** Kamath-filtered RR intervals calculate RMSSD, which directly drives the PTT continuous blood pressure inversion formula.
5. **P05 (F07 x F08):** Nocturnal PTT blood pressure dipping is evaluated alongside the overnight sleep staging and recovery score model.
6. **P06 (F08 x F09):** Morning sleep recovery score (Green vs. Red) modulates aerobic workout readiness and LT1/LT2 training boundaries.
7. **P07 (F09 x F10):** Real-time DFA-alpha1 workout detection cleanly transitions to `WAITING_FOR_SENSOR` null state upon sensor disconnection.
8. **P08 (F11 x F12):** Autonomous SmolAgents Python code duel executes across all 4 canonical game modes without scope pollution.
9. **P09 (F12 x F13):** Dynamic switching between the 4 game modes updates the Telemetry HUD Tactical Objective intent statements.
10. **P10 (F13 x F14):** Shared arena state JSON synchronizes tactical intent summaries between the standalone TUI and embedded Screen.
11. **P11 (F04 x F10):** Strict airgap egress firewall and Rule #0 zero-mock offline null states operate simultaneously without leakage.
12. **P12 (F05 x F09):** Pan-Tompkins R-peak detection computes instantaneous heart rate, which feeds the Uth-Sørensen cardiorespiratory VO2max model.
13. **P13 (F11 x F13):** Python code generated by Red and Blue Smolagents is embedded verbatim in the Tactical Objective Summary payload.
14. **P14 (F12 x F14):** Mode 3 Genetic MoE AI Router weight mutations serialize and render dynamically on the TUI dashboard.
15. **P15 (F06 x F08 x F13):** Tri-feature pipeline: Kamath RMSSD drives sleep score, which populates the HUD biological state string.
16. **P16 (F07 x F09 x F11):** Tri-feature pipeline: Zone 4 workout intensity and elevated blood pressure modulate SmolAgents defense shield deployment.

---

## 5. Tier 4: Real-World Application Workload Scenarios (8 Scenarios)

Validates complex, multi-stage operational workflows from hardware ingestion to cloud isolation:

- **Scenario 1:** Bicep 512Hz ECG Ingestion -> Pan-Tompkins QRS Detection -> Kamath 20% Artifact Filtering -> RMSSD Computation -> Zone 2 Aerobic Feedback.
- **Scenario 2:** Overnight Wearable Sleep Tracking -> Staging Breakdown (Deep/REM/Light/Awake) -> Morning Autonomic Recovery Score -> 24/7 LoRA Training Dataset Emission.
- **Scenario 3:** High-Intensity Cardiorespiratory Workout -> Real-time DFA-alpha1 LT1 (0.75) and LT2 (0.50) Tracking -> Hemodynamic PTT Blood Pressure Inversion.
- **Scenario 4:** Real-time SmolAgents Autonomous Code Duel -> Hermes 3 Red Exploit & LuCI Blue Shield Generation -> TUI Tactical Intent Summary State Sync.
- **Scenario 5:** Live Movesense Hardware Disconnection -> Instant Transition to `WAITING_FOR_SENSOR` Null State -> Verification of Zero Fabricated Arrays -> Reconnection Resumption.
- **Scenario 6:** Mode 3 Genetic MoE AI Router Dynamic Evolution -> Multi-Specialist Prompt Routing across 5 Local Models -> Weight Normalization & Fitness Scoring.
- **Scenario 7:** Full WebApp Frontend Lifecycle -> PWA Manifest & ServiceWorker Offline Caching -> 955+ OPML Kinematics Tree Raycasting -> WCAG 2.1 AA Tailwind UI Badging.
- **Scenario 8:** Cloudflare Worker Zero-Biometric Egress Isolation -> Interception of Raw Physiological Data -> Redaction & Sanitization -> 100% Local Airgap Verification.

---

## 6. Mathematical & Clinical Physiological Formulas

### 6.1 Pan-Tompkins (1985) QRS Detection
1. **Butterworth 4th-Order Bandpass (0.5–40 Hz):**
   $$H(s) = \frac{s^2}{(s^2 + \sqrt{2}\omega_L s + \omega_L^2)(s^2 + \sqrt{2}\omega_H s + \omega_H^2)}$$
2. **5-Point Derivative Filter:**
   $$d[n] = \frac{1}{8T} (-x[n-2] - 2x[n-1] + 2x[n+1] + x[n+2])$$
3. **Squaring Transform:**
   $$s[n] = (d[n])^2$$
4. **Moving Window Integrator (150ms window, $N = 0.150 \times f_s$):**
   $$y[n] = \frac{1}{N} \sum_{i=0}^{N-1} s[n-i]$$

### 6.2 Kamath et al. (2004) 20% Clinical RR Artifact Filter
$$\frac{|RR_i - RR_{i-1}|}{RR_{i-1}} \le 0.20$$
Beats exceeding 20% variation are flagged as ectopic artifacts and interpolated using surrounding baseline beats.

### 6.3 Heart Rate Variability RMSSD
$$RMSSD = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N-1} (RR_{i+1} - RR_i)^2}$$

### 6.4 Pulse Transit Time (PTT) Continuous Blood Pressure Inversion
$$\begin{aligned}
SBP &= \text{clamp}\left(120.0 + 0.45 \times (200 - PTT) + 0.15 \times (HR - 70), [80, 220]\right) \\
DBP &= \text{clamp}\left(80.0 + 0.25 \times (200 - PTT) + 0.08 \times (HR - 70), [50, 130]\right) \\
MAP &= \frac{SBP + 2 \times DBP}{3.0}
\end{aligned}$$

### 6.5 Cardiorespiratory Thresholds & Uth-Sørensen VO2max
- **LT1 Aerobic Threshold:** $DFA\text{-}\alpha_1 = 0.75$ ($\approx HR_{rest} + 0.60 \times (HR_{max} - HR_{rest})$)
- **LT2 Anaerobic Threshold:** $DFA\text{-}\alpha_1 = 0.50$ ($\approx HR_{rest} + 0.85 \times (HR_{max} - HR_{rest})$)
- **Uth-Sørensen VO2max Estimation:**
  $$VO_2\text{max} = 15.3 \times \frac{HR_{max}}{HR_{rest}} \quad [\text{ml/kg/min}]$$

---

## 7. How to Run the Tests

```bash
# Option 1: Run Master E2E Runner across All 4 Tiers (184 Tests)
python3 tests/e2e/run_all_e2e_tests.py --all

# Option 2: Run via Pytest
python3 -m pytest tests/e2e/test_tier1_feature_coverage.py tests/e2e/test_tier2_boundary_corner.py tests/e2e/test_tier3_pairwise_combinations.py tests/e2e/test_tier4_real_world_scenarios.py -v

# Option 3: Run Specific Tiers via Standalone Runner
python3 tests/e2e/run_all_e2e_tests.py --tier 1  # Tier 1: Feature Coverage (80 tests)
python3 tests/e2e/run_all_e2e_tests.py --tier 2  # Tier 2: Boundary & Corner Cases (80 tests)
python3 tests/e2e/run_all_e2e_tests.py --tier 3  # Tier 3: Pairwise Combinations (16 tests)
python3 tests/e2e/run_all_e2e_tests.py --tier 4  # Tier 4: Real-World Scenarios (8 tests)

# Option 4: Export Structured JSON Test Report
python3 tests/e2e/run_all_e2e_tests.py --all --json-output reports/e2e_test_report.json
```

---

## 8. Canonical Compliance Certifications

- ✅ **Rule #0 Zero-Mock Certification:** Zero fabricated or hardcoded metric arrays. When sensors are offline or disconnected, all interfaces return clean `WAITING_FOR_SENSOR` null states.
- ✅ **Strict 100% Local Airgap Certification:** Outbound payloads through Cloudflare Workers and external endpoints are strictly inspected and redacted; 100% of raw 512Hz ECG, optical PPG, and blood pressure streams execute locally on Apple Silicon and mesh hardware (`127.0.0.1`).
- ✅ **Mathematical & Clinical DSP Certification:** Pan-Tompkins 1985, Kamath 2004 20% RR filter, RMSSD, DFA-alpha1, Hughes-Bramwell PTT BP inversion, and Uth-Sørensen VO2max formulas are validated against exact mathematical definitions.
- ✅ **Tri-Vault Persistence Certification:** Full synchronization verified across (1) Obsidian Vault health graphs, (2) PySpark 24/7 LoRA datasets, and (3) GitHub worktree.
