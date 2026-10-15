---
title: "Screen Life Companion — Operational User Guide & Architecture"
tags: [screen_lens, life_companion, ocr, vla, mesh, obsidian]
date: 2026-10-02
status: ACTIVE
---

# 👁️ Screen Life Companion — Operational User Guide

The **Lauburu Screen Life Companion** provides real-time sovereign visual perception, automated OCR semantic search across 28,000+ authentic screen captures, 7-layer physical mesh telemetry, and actionable ROI task extraction.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SCREEN LIFE COMPANION SYSTEM ARCHITECTURE                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Native Capture Layer (Port 3035)                                         │
│    • Engine: Swift Core ScreenCaptureKit (`lauburu-lens`)                   │
│    • Storage: /Users/aaron/.lauburu/screen_lens.sqlite (28,000+ captures)   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Intelligence & Control Plane (Port 3036)                                 │
│    • Engine: Python 3.14 Flask REST Backend (`screen_life_companion.py`)    │
│    • Managed via: `screen_life_daemon.sh {start|stop|restart|status}`       │
│    • Endpoints: /api/live_timeline, /api/search, /api/mesh_nodes,           │
│                 /api/live_stats, /api/priorities, /api/roi_tasks            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Live Screen Preview Stream (Port 4003)                                   │
│    • Protocol: HTTP Multipart MJPEG at 15 FPS                               │
│    • URL: http://127.0.0.1:4003/stream.mjpg                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Frontends:                                                               │
│    • Web Dashboard: http://127.0.0.1:3036 (Local) / http://100.119.199.76:3036│
│    • Native Flutter App: 01_apps/screen_lens/lauburu_life_companion         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 How to Access & Use

### 1. Web Dashboard (macOS & Mobile)
- **Local Access:** [http://127.0.0.1:3036](http://127.0.0.1:3036)
- **Tailscale Access (Phone / Remote):** [http://100.119.199.76:3036](http://100.119.199.76:3036)
- **Features:**
  - **Instant OCR Search:** Search 28,000+ real screen frames by keyword (e.g. `IBJJF`, `Subliminator`, `Terminal`, `Chrome`).
  - **Quick Filter Chips:** Instant single-click filtering for core projects.
  - **Live Screen Viewport:** Embedded 15 FPS stream from Port 4003 with pause/resume and full-window controls.
  - **7-Layer Mesh Topology:** Real-time status, local IPs, and Tailscale overlay IPs for all 8 physical nodes.
  - **Project Priorities & ROI Tasks:** Bidirectionally synced with `PROJECT_PRIORITIES.md` and `life_memories`.
  - **Live Capture Timeline:** Auto-updates every 5 seconds as you interact with your Mac.

### 2. Service Management
```bash
# Check service status
bash 01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh status

# Restart service
bash 01_apps/screen_lens/screen_life_companion/screen_life_daemon.sh restart

# Open Web Dashboard in default browser
open "http://127.0.0.1:3036"
```

### 3. Native Flutter Life Companion App
- Path: `01_apps/screen_lens/lauburu_life_companion`
- Target Nodes (Rule 20):
  - **Desktop testing:** MacBook Pro (Node L2) (L5)
  - **Mobile testing:** Samsung Galaxy S20+ (L7) via `adb install`
- Verified: `flutter analyze` passes with 0 errors / 0 warnings.
- Screen Modules:
  - `OmniInboxScreen`: Unified inbox combining Personal/Business Gmail, SMS, Instagram, and Gumtree.
  - `EcommerceHubScreen`: Live rashguard and hardware sales metrics.
  - `TimelineScreen`: Real-time Screen Lens OCR captures from Port 3036 and mesh audio telemetry.

---

## 🏛️ Tri-Vault Synchronization
- **Obsidian Vault:** `obsidian_vault/APPS_AND_FEATURES/SCREEN_LIFE_COMPANION_USER_GUIDE.md` & `obsidian_vault/PROJECT_PRIORITIES.md`
- **PySpark Lake:** Actionable task traces extracted from `life_memories` table.
- **Git Worktree:** Production-grade daemon script and frontend templates committed to tree.
