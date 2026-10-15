---
title: "Zone 2 Lauburu — UI/UX Specification & Frontier Review"
tags: [zone2, cardiovascular, dfa_alpha1, movesense, zero_mock, frontier_review, lora]
date: 2026-10-03
status: PRODUCTION_ACTIVE
---

# 🫀 Zone 2 Lauburu — UI/UX Specification & Review

## 1. System Overview
**Zone 2 Lauburu** (`01_apps/zone_2/frontend/index.html`) is the real-time cardiovascular aerobic threshold and DFA-$\alpha_1$ pacing engine of the Lauburu Ecosystem.

- **Aerobic Pacing Range:** Tracks 132 – 146 BPM target window (60–70% Heart Rate Reserve based on Aaron's resting HR of 52 and maximum HR of 185).
- **DFA-$\alpha_1$ Lactate Proxy:** Detrended Fluctuation Analysis calculates fractal correlation:
  - $\alpha_1 > 1.0$: Zone 1 (Recovery)
  - $0.75 \le \alpha_1 \le 1.00$: Zone 2 (Target Aerobic Base)
  - $\alpha_1 < 0.75$: Zone 3+ (Anaerobic / Lactate Threshold)
- **Movesense Medical 512Hz ECG:** Connects over BLE GATT `0x180D` and PMD `0x0001` with Pan-Tompkins QRS peak detection.
- **Audio Pacing Coach:** Piper TTS voice prompts ("Maintain pace" or "Slow down, exiting aerobic zone") ducking media players by -24 dB.
- **Rule 0 Zero-Mock Conformance:** Awaiting sensors display clean waiting states (`-- BPM`, `-- DFA-α1`, `-- ms RMSSD`).

---

## 2. Frontier Model Review Summary (Gemini 2.5 Flash Lite)
- **Zero-Mock Truth:** Confirmed waiting states avoid synthetic data injection.
- **Sports Science Pacing:** Commended inclusion of both HR and DFA-$\alpha_1$; recommended high-contrast visual cues for outdoor glanceability.
- **WCAG AAA Compliance:** High-contrast emerald (`#10B981`) and large 7xl typography maximize readability during intense running or cycling.

---

## 3. Tri-Vault Synchronization
- **Frontend Code:** [`01_apps/zone_2/frontend/index.html`](file:///Volumes/Lauburu-Monorepo/01_apps/zone_2/frontend/index.html)
- **Ecosystem Prototype:** [`08_business_and_commerce/prototypes/ecosystem/zone2_endurance_preview.html`](file:///Volumes/Lauburu-Monorepo/08_business_and_commerce/prototypes/ecosystem/zone2_endurance_preview.html)
- **LoRA Lake:** Triplet appended to `/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl`.
