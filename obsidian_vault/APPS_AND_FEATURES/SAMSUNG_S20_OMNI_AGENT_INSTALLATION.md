---
title: "Omni Agent Lauburu: Samsung Galaxy S20 (Layer 7) Installation & Verification"
tags: [samsung_s20, omni_agent_lauburu, android_installation, adb, mesh_radar, layer7, tri_proof]
date: "2026-09-18"
author: "Antigravity Sovereign Agent"
---

# 📱 Omni Agent Lauburu: Samsung Galaxy S20 (Layer 7) Installation & Verification

- [[Index]]
- [[SOVEREIGN_SINGLE_CHAT_NEXUS_IDE]]
- [[SCREEN_LENS_HUMAN_CLICKTHROUGH_AUDIT]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]

---

## 🏛️ Executive Summary

Under direct directive of Aaron (`install omni agent lauburu too the samsung s20`), the official **Omni Agent Lauburu** package (`com.lauburu.omni_agent_flutter`) was extracted, transmitted, installed, and verified on the physical **Samsung Galaxy S20+ 5G (SM-G986B / Layer 7 Dedicated UI Testing Node)**.

All operations were executed with zero mocks, verified with exact exit codes, and visually recorded using Screen Lens via ADB.

---

## 🔬 Empirical Tri-Proof Matrix

| Check | Target / Artifact | Empirical Result | Verification Status |
| :--- | :--- | :--- | :--- |
| **Hardware Discovery** | GL.iNet Router (`192.168.8.1` / `100.112.203.121`) | Detected `R3CN40CJJ1R` on USB 3.0 Host (`y2sxeea SM_G986B`) | **VERIFIED (Exit 0)** |
| **TCP/IP ADB Bridge** | Samsung S20 (`192.168.8.10:5555` & `100.78.206.96:5555`) | Successfully connected via TCP/IP mode | **VERIFIED (Exit 0)** |
| **Streamed Install** | `01_apps/Omni_Agent_Lauburu.apk` (`50,392,410 bytes`) | SHA256: `86309d022f3a3f799c0f2701d4cc48c5f3cd077d5174400ef0f345d1a560ada9` | **VERIFIED (Success)** |
| **Package Path** | `pm path com.lauburu.omni_agent_flutter` | `/data/app/~~ikVTZfgv1t6axewbzn4Hew==/com.lauburu.omni_agent_flutter-ZX1bBqVHDJB35Cbw9iv1ew==/base.apk` | **VERIFIED (Exit 0)** |
| **Doze Whitelisting** | `dumpsys deviceidle whitelist` & `appops RUN_IN_BACKGROUND` | `user,com.lauburu.omni_agent_flutter,10409` whitelisted for 24/7 background keepalive | **VERIFIED (Exit 0)** |
| **Visual Proof 1** | Mesh Radar View (`screen_lens_samsung_s20_omni_agent.png`) | Displays Mac Mini M4 (-35 dBm), MacBook Pro (-48 dBm), Linux Hub (-62 dBm), Pixel 10 (-72 dBm) | **VERIFIED (311,882 bytes)** |
| **Visual Proof 2** | Mesh Terminal View (`screen_lens_samsung_s20_terminal.png`) | Terminal canvas active with `IDENTIFY`, `TELEMETRY`, `getprop`, `sw_vers`, `uname` | **VERIFIED (148,933 bytes)** |

---

## 👑 Conclusion & Status
**Omni Agent Lauburu** is permanently installed, anti-doze whitelisted, and actively executing on the **Samsung Galaxy S20 (Layer 7)**.
