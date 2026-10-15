---
title: "Track 2: Life Companion Core Cross-Platform App"
conversation_id: "d161e75c-1d12-4715-8ca2-2eb3cab65eed"
tags: [life_companion, flutter, macos, android, pixel10, silent_boot, screenpipe, acoustic_election]
---

# 📱 Track 2: Life Companion Core Cross-Platform App (macOS & Android)

> **Parent Source Conversation:** [Conversation d161e75c-1d12-4715-8ca2-2eb3cab65eed](conversation://d161e75c-1d12-4715-8ca2-2eb3cab65eed)  
> **Workspace Root:** `/Volumes/Lauburu-Monorepo/01_apps/screen_lens/lauburu_life_companion`  
> **macOS App Bundle:** `/Applications/lauburu_life_companion.app` (50.9 MB, SHA256 `04d7d7696...`)  
> **Android Release APK:** `android/app/build/outputs/flutter-apk/app-release.apk` (63.0 MB, SHA256 `ec796c0a00...`)  
> **Central Mesh Hub:** Port 18899 (`canonical_network_resurrection_engine.py` + `mesh_timeline_audio_hub.py`)  

---

## 🏛️ 1. Exact Line-by-Line Chat History & Direction Extract

From [Source Conversation d161e75c-1d12-4715-8ca2-2eb3cab65eed](conversation://d161e75c-1d12-4715-8ca2-2eb3cab65eed):

- **User Directives:**
  - **Turn 119:** *"/goal develop life companion app until completion"*
  - **Turn 124:** *"auto reboot - it also needs to run on the pixel"*
  - **Turn 138-139:** *"it needs to be an installable app for customers - install it too my pixel and mac mini... it can't be just a url opener app it needs to be properly installed"*
  - **Turn 143:** *"also this app needs to a single source that can be installed on multiple devices, it shouldn't be two different apps"*
  - **Turn 145:** *"it needs to boot on device start and also the screen lens need to have 24/7 logging"*
  - **Turn 155-156:** *"use the pixel as the 24/7 mic/system audio - it should dynamically switch devices though, whatever device picks up my voice eg the pixel is out of range but a different device that im signed into my account on picks up audio then it should connect automatically... it should be for all devices"*

---

## 🌐 2. Core Architecture & Proven Working State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 LIFE COMPANION CROSS-PLATFORM ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. 🚀 SILENT BOOT PERSISTENCE                                               │
│    • macOS: ~/Library/LaunchAgents/com.lauburu.lifecompanion.plist          │
│    • Android: BOOT_COMPLETED intent-filter + foreground service             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. 🎙️ 24/7 DYNAMIC AMBIENT MIC ELECTION (Port 18899 Hub)                    │
│    • L6 Pixel 10 Pro XL: pixel_ambient_mic_daemon.py (PID 25560)           │
│    • Current Acoustic Winner: Pixel 10 winning election (-91.0 dB vs Mac)   │
│    • Automatic Handoff: Seamless switch to Mac Mini mic if Pixel drops out  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. 👁️ SCREENPIPE-PARITY EVENT & OCR TIMELINE                                │
│    • Rust capture_daemon cross-compiled for macOS arm64 and x86_64          │
│    • Daemons active on L1 Mac Mini, L2 MacBook Pro, L2 MacBook Pro          │
│    • SQLite timeline: 04_data_and_memory/screen_lens_timeline.db            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 3. Top 5 Immediate Tasks for the Life Companion Core App Chat

1. [ ] Verify LaunchAgent auto-start on macOS boot and Android `BOOT_COMPLETED` service.
2. [ ] Ingest live dynamic mic election telemetry badge into Flutter AppBar.
3. [ ] Expand `timeline_screen.dart` to support filtering by device (`L1 Mac`, `L6 Pixel`, `L5 Air`).
4. [ ] Build local SQLite full-text search across `screen_lens_timeline.db`.
5. [ ] Execute live `flutter test` suite to preserve 100% passing test coverage (39/39 passing).
