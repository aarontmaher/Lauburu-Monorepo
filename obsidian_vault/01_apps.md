---
title: "01_apps — Production Client Applications & Universal Edge AI"
updated: "2026-08-27"
tags: [apps, frontend, movesense_hub, zone2, grapplingmap, quartz, port_4000_hub, spec-01]
---

# 01_apps — Production Client Applications & Universal Edge AI

## 📋 Scope & Architecture
Contains all user-facing client applications, web dashboards, and mobile user interfaces across the Lauburu ecosystem. Every application embeds or connects to the **Universal On-Device Edge Specialist AI** for real-time intelligence.

## 📱 Application Registry
1. **`port_4000_hub` (FastAPI / Next.js):**
   - Central command bridge and live telemetry hub on Port 4000.
   - Aggregates multi-node health, biometrics streams, and AI inference latency.
2. **`movesense_hub` (Flutter / Dart BLoC):**
   - High-throughput BLE data acquisition interface for Movesense HR+ sensors (512Hz raw ECG, 9-axis IMU).
3. **`zone2_endurance` (Next.js 14 / TailwindCSS):**
   - Cardiovascular endurance and aerobic threshold training dashboard computing real-time $\text{DFA}-\alpha_1$ and ventilatory thresholds.
4. **`grapplingmap_web` (Three.js / WebGL):**
   - Interactive 3D spatial visualization of the 955-node OPML grappling knowledge tree and kinematic transitions.
5. **`obsidian_web` (Quartz Digital Garden):**
   - Fast static digital garden site generator compiling the markdown knowledge graph into searchable web pages (>= 260 pages emitted).
6. **`chat_app` (FastAPI / WebSockets / React):**
   - Real-time peer-to-peer chat interface for human-agent collaboration and live debate monitoring.
7. **`openclaw_ui_automator` (Python / ADB):**
   - Automated UI testing harness executing live visual accessibility audits and app interactions.
8. **`voice_coder` (Python / Whisper):**
   - Hands-free voice pair-programming interface for in-vehicle and remote development.

## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-01-apps-ecosystem`
- **Focus Areas:** Cross-platform UI/UX, responsive layouts, WebSocket synchronization, Quartz static compilation.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Deep Architecture:** [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- **Connected Modules:** [[00_core_infrastructure]], [[03_biometrics_and_telemetry]], [[10_spatial_grappling_kinematics]]
