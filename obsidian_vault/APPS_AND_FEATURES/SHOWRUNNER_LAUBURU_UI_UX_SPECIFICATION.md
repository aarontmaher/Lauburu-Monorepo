---
title: "Showrunner Lauburu — UI/UX Specification & Frontier Review"
tags: [showrunner, video, ptzt, webrtc, zero_mock, frontier_review, lora]
date: 2026-10-03
status: PRODUCTION_ACTIVE
---

# 📹 Showrunner Lauburu — UI/UX Specification & Review

## 1. System Overview
**Showrunner Lauburu** (`01_apps/lauburu_showrunner/backend/static/index.html`) is the multi-camera automated sports broadcast and video production director of the Lauburu Ecosystem.

- **Multi-Camera Control:** Integrates Pixel 10 Pro XL 8K Digital PTZ camera over 6GHz Wi-Fi 7 (`rtsp://100.73.38.87:8554/live`) alongside host HDMI and USB capture cards.
- **Automated Combat Framing:** Visual tracking centers grappling fighters, detecting rapid positional transitions and zooming dynamically.
- **Vertical 9:16 Social Clip Generator:** Real-time cropping pipeline for automated Instagram Reels / YouTube Shorts export.
- **Technical Commentary Console:** Live transcription and tactical breakdown powered by local Whisper.cpp and local LLM audio ducking.
- **Zero-Mock Data Pipeline:** Replaced simulated match generators with authentic live BLE replay and waiting state flags (`📡 LIVE SENSOR SYNC`).

---

## 2. Frontier Model Review Summary (Gemini 2.5 Flash Lite)
- **Zero-Mock vs Studio Readiness:** Approved prioritizing un-simulated production video streams while maintaining clean waiting indicators during sensor disconnects.
- **Low Latency Switching:** Recommended performance-first event propagation and GPU-accelerated canvas overlays.
- **WCAG AAA Compliance:** High-contrast neon green (`#00FF41`) on dark slate (`#09090B`) ensures full readability in broadcast production environments.

---

## 3. Tri-Vault Synchronization
- **Frontend Code:** [`01_apps/lauburu_showrunner/backend/static/index.html`](file:///Volumes/Lauburu-Monorepo/01_apps/lauburu_showrunner/backend/static/index.html)
- **Ecosystem Prototype:** [`08_business_and_commerce/prototypes/ecosystem/showrunner_lauburu_preview.html`](file:///Volumes/Lauburu-Monorepo/08_business_and_commerce/prototypes/ecosystem/showrunner_lauburu_preview.html)
- **LoRA Lake:** Triplet appended to `/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl`.
