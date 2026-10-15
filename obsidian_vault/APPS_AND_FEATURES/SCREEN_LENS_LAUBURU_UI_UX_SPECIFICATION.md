---
title: "Screen Lens Lauburu — UI/UX Specification & Frontier Review"
tags: [screen_lens, vla, mjpeg_15fps, coregraphics, vision_ocr, tinylm, zero_mock, frontier_review, lora]
date: 2026-10-03
status: PRODUCTION_ACTIVE
---

# 👁️ Screen Lens Lauburu — UI/UX Specification & Review

## 1. System Overview
**Screen Lens Lauburu** (`01_apps/screen_lens/frontend/index.html`) is the multimodal Vision-Language-Action (VLA) companion, live screen broadcaster, and desktop automation engine of the Lauburu Ecosystem.

- **15 FPS Live Screen HUD Stream (Port 4003):**
  - Delivers low-latency ($<25\text{ ms}$) multipart MJPEG broadcast (`http://127.0.0.1:4003/stream.mjpg`).
  - **Rule 7 & Rule 0 Enforcement:** Strictly bars frozen or simulated static screenshots; if the daemon drops, the UI immediately surfaces an explicit fallback waiting banner (`[AWAITING LIVE 15 FPS MJPEG STREAM :4003]`).
- **Vision OCR & TinyLM Telemetry Fusion:**
  - Live Apple Vision Framework OCR running on Port 3035.
  - Sub-2ms edge-native TinyLM classifier fusing visual cues with raw terminal outputs (`08_business_and_commerce/tinylm_latest_metrics.json`).
  - Human action triggers: automatically launches proactive audits whenever mouse or keyboard activity is registered.
- **VLA CoreGraphics C Actuation Engine (Port 4006):**
  - Dispatches zero-lock synthetic mouse clicks and keystrokes via pure C CoreGraphics APIs (`CGEventCreateMouseEvent`), eliminating WindowServer hangs.
- **Layer 0 Bluetooth Serial Terminal (Port 4005):**
  - Persistent RFCOMM serial bridge for zero-infrastructure out-of-band debugging.

---

## 2. Practical Backend Development Path & Full Functionality Roadmap

### Architecture & Endpoints
- **Capture Daemon:** Python/C capture service in `01_apps/screen_lens/capture_daemon/` broadcasting on `http://127.0.0.1:4003/stream.mjpg`.
- **OCR Service:** Port 3035 exposing `/ocr_results` and bounding boxes.
- **Actuation Service:** Port 4006 handling `POST /api/actuate`.
- **Life Companion Agent:** `screen_life_companion.py` on Port 3036 logging observations to `obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md`.

### Requirements for 100% Launch
1. **OS Permissions:** Screen Recording and Accessibility permissions enabled for Terminal/Python in macOS System Settings.
2. **Rule 3 Host Sanctuary:** UI automation and heavy AppleScripts must be offloaded to Node L2 (MacBook Pro) or Linux Hub (L3) to preserve Mac Mini (L1) RAM headroom $\ge 4.8\text{ GB}$.
3. **LaunchAgent Daemons:** Anchor `ai.lauburu.screen-lens-stream.plist` and `com.lauburu.screen-life-companion.plist` in `~/Library/LaunchAgents/`.

---

## 3. Frontier Model Review Summary (Gemini 2.5 Flash Lite)
- **Zero-Mock & Live Screen Truth Enforcement:** **92/100** — Authentic 15 FPS MJPEG stream error handling and fallback overlay without synthetic mock frames.
- **Multimodal VLA Architecture:** **88/100** — Integrated live stream viewport, OCR token density, sub-2ms TinyLM latency, and CoreGraphics C API console.
- **Backend Development Path Clarity:** **90/100** — Practical breakdown across capture, OCR, actuation, and companion services with macOS permission blueprints.
- **WCAG AAA Compliance:** **85/100** — High-contrast dark mode readability, monospaced coordinate badges, and accessible keyboard focus states.

---

## 4. Tri-Vault Synchronization
- **Frontend Code:** [`01_apps/screen_lens/frontend/index.html`](file:///Volumes/Lauburu-Monorepo/01_apps/screen_lens/frontend/index.html)
- **Ecosystem Prototype:** [`08_business_and_commerce/prototypes/ecosystem/screen_lens_preview.html`](file:///Volumes/Lauburu-Monorepo/08_business_and_commerce/prototypes/ecosystem/screen_lens_preview.html)
- **LoRA Lake:** Triplet appended to `/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl`.
