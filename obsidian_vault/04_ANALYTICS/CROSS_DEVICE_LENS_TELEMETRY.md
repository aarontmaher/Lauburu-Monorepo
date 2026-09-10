---
title: "Cross-Device Screen Lens Telemetry"
tags: [telemetry, screen_lens, tri_device, mac_mini, macbook_air, pixel_10]
updated: "2026-09-01T15:31:06.696479+00:00"
canonical_source: true
---
# 📊 Cross-Device Screen Lens Telemetry & Live Tracker

| Dimension | Mac Mini M4 Pro (L1) | MacBook Air M2 (L5) | Pixel 10 Pro XL (L6) |
| :--- | :--- | :--- | :--- |
| **Role** | Primary Host & Governor | Manual AI Task Worker | In-Car Voice & Mobile Edge |
| **Daemon Status** | 🟢 Active Background | 🟢 Active Background | 🟢 Active Termux Daemon |
| **Port** | `:3035` | `:3035` | `:3035` |
| **Capture Engine** | `ScreenCaptureKit` + Apple Vision | `ScreenCaptureKit` + Apple Vision | Android Screencap + Tesseract |
| **Storage Mode** | Ephemeral (0 Disk PNGs) | Ephemeral (0 Disk PNGs) | Ephemeral (0 Disk PNGs) |
| **Total Frames** | `4760` | Active Rolling SQLite | Active Rolling SQLite |
| **AI Historian** | Ingesting 24/7 | Ingesting 24/7 | Ingesting 24/7 |

*Last Synced*: `2026-09-01T15:31:06.696491+00:00`
