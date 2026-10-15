---
title: "Sales-Ready Cross-Device App Architecture, Modular Client Gate & Non-Saturating ELO Arena"
tags: [ai_training, sales_ready_app, combat_lab_lauburu, spatial_grappling, benchmark, elo_accuracy, multi_device]
date: "2026-09-16"
status: "ADVERSARIALLY_HARDENED"
---

# 🥋 Sales-Ready App Architecture, Modular Client Gate & Non-Saturating ELO Arena

## 1. Architectural Realignment: Modular App Gate vs. Monolith Clumping

In accordance with Aaron's architectural directive:
* **The Anti-Pattern (Monolithic Clumping):** `Spatial Grappling 3D` (955-node OPML kinematic tree, joint torque physics, submission counter routes) must **NEVER** be cramped as a minor sub-tab inside `Combat Lab Lauburu`.
* **The Correct Architecture (Dedicated Specialized Apps):** `Spatial Grappling Lauburu` is an independent, specialized application featured prominently in the **Client App Gate**, allowing each app to maximize its device-specific strengths.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             LAUBURU MODULAR CLIENT APP ECOSYSTEM                                 │
├──────────────────────────┬──────────────────────────┬────────────────────────────────────────────┤
│ APPLICATION              │ TARGET HARDWARE          │ SPECIALIZED CAPABILITY & STACK             │
├──────────────────────────┼──────────────────────────┼────────────────────────────────────────────┤
│ 1. Combat Pulse Lauburu  │ iPhone (iOS) &           │ Swift CoreBluetooth & Kotlin BLE GATT.     │
│    (Formerly Movesense)  │ Android (Pixel / Galaxy) │ Multi-device wearable sync, Zone 2 lock-   │
│                          │                          │ screen Live Activities, audio pacing.      │
├──────────────────────────┼──────────────────────────┼────────────────────────────────────────────┤
│ 2. Spatial Grappling     │ Desktop Mac (Metal) &    │ WebGL, Three.js, Wasm & Python kinematics. │
│    Lauburu               │ Linux Head Node / WebGL  │ 955-node OPML tree, 3D joint torque (28Nm),│
│                          │                          │ submission defense routes & tatami physics.│
├──────────────────────────┼──────────────────────────┼────────────────────────────────────────────┤
│ 3. Combat Lab Lauburu    │ macOS (Apple Silicon M4) │ Metal GPU & responsive customer UI.        │
│    (Flagship Hub)        │ & Responsive Web         │ Live ECG & PPG, Medical Specialist AI,     │
│                          │                          │ Universal Device Connector, compute tokens.│
├──────────────────────────┼──────────────────────────┼────────────────────────────────────────────┤
│ 4. Screen Lens Lauburu   │ Pixel 10 (Tensor G5)     │ Tensor G5 Edge TPU, 8K PTZ gym camera      │
│                          │ & Darwin Host            │ stream, autonomous OCR, technique vision.  │
└──────────────────────────┴──────────────────────────┴────────────────────────────────────────────┘
```

---

## 2. Customer Purity, Specialist Routing & 5-Minute Phone PPG Test

In accordance with Aaron's directives:
1. **Customer-Facing Purity (Zero Internal Developer Mesh Jargon):**
   - Customer-facing interfaces must **never** leak internal developer infrastructure (e.g., "L1-M4 MESH: 0.27ms", "Port 8082", "40Gbps TB4 DMA Bridge", or raw IP addresses).
   - Sensor connection state is strictly consumer-friendly: `● CONNECTED` vs. `○ STANDBY (CONNECT DEVICE)`.
2. **Medical Specialist AI Routing (Cardio-DSP Diagnostic Agent):**
   - Health analysis, HRV recovery, and blood pressure feedback are strictly routed to the **Medical Specialist AI / Cardio-DSP Specialist Model**.
   - Qwen 3.8 Max remains the Sovereign Master Local Orchestrator of system consensus, but **NEVER** dispenses medical diagnoses directly.
3. **5-Minute Phone Camera Optical PPG & PTT Blood Pressure Test:**
   - Requires zero external hardware. Uses the rear phone camera and flash over the fingertip capillary bed.
   - Measures the mechanical capillary pulse wave and arterial dicrotic notch.
   - Synchronizes ventricular electrical depolarization (ECG R-wave) with peripheral arterial arrival (PPG peak) to compute **Pulse Transit Time (PTT)** for cuffless Systolic and Diastolic Blood Pressure.
4. **Universal Health Metric Device Connector:**
   - Direct support for open standards across all major athletic wearables:
     - **Polar H10 / H9:** Chest strap ECG (BLE GATT `0x180D`).
     - **Polar Verity Sense / OH1:** Optical PPG armband for grappling.
     - **Whoop 4.0:** Cardiovascular strain and nocturnal recovery sync.
     - **Apple Watch & Wear OS:** Native HealthKit / Health Connect SDK.
     - **Precision Clinical ECG Sensor:** 512Hz raw ECG with 9-DOF IMU.
     - **Phone Camera PPG:** Built-in zero-hardware 5-minute test.
5. **Vendor Simplification:**
   - Deprecated bulky vendor naming (`Movesense Hub Lauburu` $\rightarrow$ `Combat Pulse Lauburu`).

---

## 3. The ELO Accuracy Paradox & Benchmark Saturation Invariant

### Why Reliable 100/100 Scores Invalidate ELO Accuracy
When models reliably achieve perfect 100/100 scores:
1. **Ceiling Saturation:** The benchmark is measuring baseline checklist compliance rather than real-world fitness.
2. **False Parity:** Bradley-Terry ELO assumes probabilistic skill variance. If both models score 100/100, the calculated delta is 0, but awarding points creates artificial ELO inflation without exposing edge-case failures.
3. **Hidden Runtime Failures:** A static 100% score often hides real physical bugs:
   - **Customer Mesh Leaks:** Leaking developer debug stats into customer apps.
   - **Faked Data (Rule 0 Violations):** Loading hardcoded fake telemetry (`148 BPM`) on startup before any sensor connects.
   - **Dynamic Island / Notch Collisions:** Mobile headers clipping into camera status bars.
   - **Unbounded Memory Leaks:** 512Hz canvas array appends lacking circular ring buffers crashing mobile Safari in 15 minutes.

### Adversarial Hardening (The Non-Saturating Arena Results)
The enhanced arena ([`sales_ready_app_arena.py`](file:///Volumes/Lauburu-Monorepo/08_business_and_commerce/benchmarks/sales_ready_app_arena.py)) enforces **Hard Adversarial Stress Audits**:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                         NON-SATURATING ADVERSARIAL ARENA AUDIT RESULTS                           │
├───────────────────────────────┬───────────────────────────────┬──────────────────────────────────┤
│ TEAM 1: LOCAL SOVEREIGN       │ TEAM 2: CLOUD FRONTIER        │ FLAGSHIP: COMBAT LAB LAUBURU     │
│ Score: 77 / 100 (FAILED)      │ Score: 89 / 100 (PASSED)      │ Score: 100 / 100 (PERFECT PASS)  │
├───────────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ [-6] Leaked mesh debug status │ [-5] Missing Universal Health │ [+] Zero developer mesh leaks    │
│ [-5] Missing Universal Health │      Device Connector         │ [+] 100% Rule 0 clean waiting    │
│      Device Connector         │ [-6] Missing 5-Min Phone PPG  │     states ("-- BPM", flatline)  │
│ [-6] Rule 0: Faked 148 BPM    │      & PTT Blood Pressure     │ [+] 5-Min Phone Optical PPG Test │
│      loaded before connection │                               │ [+] Universal Device Connector   │
│ [-6] Missing 5-Min Phone PPG  │                               │ [+] Medical Specialist AI        │
│      & PTT Blood Pressure     │                               │ [+] 4 Platform Binary Gate       │
└───────────────────────────────┴───────────────────────────────┴──────────────────────────────────┘
```

---

## 4. Suggested Hardware Integration: 4-Tier Movesense Pricing Matrix & Scientific Comparison

While Combat Lab Lauburu supports open universal connectivity across third-party wearables (Polar H10, Polar Verity, Whoop, Apple Watch, Wear OS), **Movesense MD+ is established as the officially suggested and certified hardware partner**.

### 4.1 "Buy a Movesense" Pop-Up Modal (`#buyMovesenseModal`)
Accessible directly via the top actions, hero banner, device card, or the Salesman RAG chat:
1. **Movesense MD+ Sensor Only ($170 AUD):** Single-lead 512Hz clinical ECG, 9-DOF IMU, IP68 waterproof (30m), user-replaceable CR2025 coin cell, unlocked open BLE GATT API.
2. **Movesense Combat Kit ($210 AUD - Most Popular):** Includes MD+ Sensor + anti-chafing neoprene bicep band with dual silver-chloride textile electrodes (zero wrist displacement or grip entanglement).
3. **All-In-One Starter Bundle ($249 AUD - Save $70 AUD):** Includes MD+ Sensor + Combat Bicep Band + 3 Months Pro Lab Membership ($297 value) + PTT Blood Pressure calibration.
4. **Academy Coach & Sparring Dual Pack ($360 AUD - Save $60 AUD):** 2x Movesense MD+ Sensors + 2x Combat Neoprene Bicep Bands + multi-athlete corner pacing sync + dual sensor hard travel case.
- **Logistics & Solvency:** Dispatched within 24h from Altona North, Victoria via Australia Post Express (free shipping) with physical wholesale COGS ($125 AUD) locked in escrow.

### 4.2 "Why Movesense is Superior" Comparison Modal (`#whyMovesenseModal`)
Provides an empirical, scientific comparison against commercial fitness trackers:
* **512Hz Clinical Sample Rate vs 1–25Hz Commercial Optical:** Commercial watches (Apple Watch, Whoop) only emit 25Hz optical PPG with $\pm 40\text{ ms}$ jitter. Movesense samples raw single-lead ECG at 512Hz (1.95ms resolution), providing the exact ventricular depolarization timestamp needed for sub-millisecond Pulse Transit Time (PTT) cuffless blood pressure.
* **Combat Mat Ergonomics (Zero Wrist Occlusion):** Bicep/chest strap placement prevents the displacement and wrist injuries common when wearing smartwatches during wrestling tie-ups or spider guard grips.
* **9-DOF Inertial Motion Kinematics:** 9-axis IMU streams acceleration, rotational angular velocity, and magnetic heading for 3D strike speed, scramble intensity, and takedown impact detection.
* **Zero-Subscription Data Sovereignty:** Direct GATT streaming to local device with zero cloud latency, zero proprietary paywalls ($30/mo subscription eliminated), and 100% data ownership.

---

## 5. Unified Biometrics View & Tri-Mode Local AI Advisor Council

### 5.1 PPG Consolidation & Rule 0 Authentic Run Replay
1. **Consolidated Live Biometrics Tab:** Rather than separating cardiac monitoring across disjointed tabs, the 5-Minute Phone Camera PPG test lives directly inside the primary Biometrics screen via a segmented pill subnav (`🫀 LIVE CARDIAC ECG` vs. `📱 5-MIN PHONE CAMERA PPG & BP`).
2. **Rule 0 Authentic Run Replay (`▶ LOAD 512Hz SPARRING DEMO`):** Under Rule 0 Zero-Mock testing, simulated arrays are strictly forbidden. The demo button streams an authentic recorded 512Hz clinical ECG sparring session from disk so athletes and gym owners can inspect real-time Pan-Tompkins QRS peak detection, RMSSD heart rate variability, and PTT blood pressure synchronization without needing physical sensors connected.

### 5.2 Tri-Mode Local AI Advisor (`setAiAgentMode`)
The right-hand coach card integrates three autonomous local personas with quick suggestion chips:
1. **🩺 Medical Specialist AI:** Cardio-DSP diagnostic model analyzing RMSSD recovery, parasympathetic tone, DFA-$\alpha 1$ aerobic threshold, and PTT arterial compliance.
2. **🛒 Local AI Salesman (RAG):** Grounded commercial concierge answering product queries, transparent pricing ($170, $210, $249, $360 AUD), 24h Altona North dispatch, 30-day mat guarantee, and Whoop cost-of-ownership comparisons ($360/yr savings).
3. **⚖️ /ai-debate Consensus:** Multi-agent deliberative council (Medical Specialist + Salesman RAG + Adversarial Red Team) providing rigorous consensus verdicts on training protocols, hardware investments, and athlete recovery trade-offs.

- [[Index]]
- [[SHOPIFY_SWE_BENCH_REPORT]]
- [[SHOPIFY_APP_MEMBERSHIPS_AND_COMPUTE_BILLING_SPEC]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
