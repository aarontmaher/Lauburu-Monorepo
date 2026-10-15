---
title: "Automotive Hub Lauburu — UI/UX Specification & Frontier Review"
tags: [automotive, voice_coding, ast, android_auto, dhu, zero_mock, frontier_review, lora]
date: 2026-10-03
status: PRODUCTION_ACTIVE
---

# 🚗 Automotive Hub Lauburu — UI/UX Specification & Review

## 1. System Overview
**Automotive Hub Lauburu** (`01_apps/automotive/frontend/index.html`) delivers hands-free in-vehicle pair programming and AST-aware voice coding for driving safety.

- **Android Auto DHU Link:** Connects over TCP (`tcp://127.0.0.1:5277`) to projected in-car head unit displays.
- **4-Tier Audio Ducking Priority Matrix:**
  - Level 1: Emergency & Navigation alerts (Immediate AI voice preempt & mute).
  - Level 2: Driver Voice Commands (Ducks media player by -24 dB).
  - Level 3: AI Speech Synthesis (Piper TTS code explanation).
  - Level 4: Road Noise DSP Filter (Pink noise suppression 65 dBA).
- **Region Backspace AST Editor:** Voice-driven semantic syntax editing preventing broken AST nodes.
- **Automotive Safety Standards:** Touch targets strictly adhere to $\ge 48\times 48\text{ px}$ with high-contrast glanceable fonts.
- **Rule 0 Zero-Mock Conformance:** Awaiting streams display explicit indicators (`-- dBA [Awaiting CoreAudio Feed]`, `-- ms [Awaiting Voice Input]`).

---

## 2. Frontier Model Review Summary (Gemini 2.5 Flash Lite)
- **Zero-Mock Truth:** Recommended verifying live CoreAudio inputs and latency thresholds.
- **Audio Ducking:** Commended the 4-tier matrix; recommended tuning threshold hysteresis to prevent jarring audio switching during turbulent driving.
- **WCAG AAA Compliance:** Large typography and high-contrast styling ensure glanceability under variable daylight conditions.

---

## 3. Tri-Vault Synchronization
- **Frontend Code:** [`01_apps/automotive/frontend/index.html`](file:///Volumes/Lauburu-Monorepo/01_apps/automotive/frontend/index.html)
- **Ecosystem Prototype:** [`08_business_and_commerce/prototypes/ecosystem/automotive_voice_hub_preview.html`](file:///Volumes/Lauburu-Monorepo/08_business_and_commerce/prototypes/ecosystem/automotive_voice_hub_preview.html)
- **LoRA Lake:** Triplet appended to `/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl`.
