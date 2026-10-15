---
title: "Bluetooth Serial Omni Agent Suite: Autonomous Multi-Platform Hardware Identification, Privilege Elevation, AI Mesh Linking & Screen Lens VLA"
tags: [bluetooth_serial, omni_agent, shizuku, smappservice, polkit, ubus, flutter, go_daemon, web_tui, screen_lens, zero_mock]
created: "2026-09-18T03:58:00+10:00"
---

# 🛰️ Bluetooth Serial Omni Agent Suite: Autonomous Multi-Platform Control Plane

The **Bluetooth Serial Omni Agent Suite** delivers an unkillable Layer 0 Bluetooth Serial control plane that automatically identifies connected hardware nodes (Android, macOS, Linux, OpenWrt Router, iOS), activates native privilege elevation bridges, promotes transport to high-speed data planes (TB4 DMA / Wi-Fi 7), and bootstraps the **Screen Lens Sovereign** VLA perception engine.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 BLUETOOTH SERIAL OMNI AGENT ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. TRI-MODAL APPLICATION DELIVERY                                           │
│    • Unified Flutter App (Android APK + macOS Bundle): ANSI xterm, radar.   │
│    • Headless Polyglot Daemon (Go static binary): Darwin, Linux, OpenWrt.    │
│    • Universal Web TUI & PWA (xterm.js + Web Bluetooth NUS API + sw.js).    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. DUAL-TIER DISTRIBUTION ARCHITECTURE                                      │
│    • Tier 1 (Store Compliant): Play Store & App Store sandbox (BLE NUS).    │
│    • Tier 2 (Sovereign Elevation): Shizuku UID 2000, SMAppService, ubus.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. HARDWARE & PRIVILEGE ELEVATION BRIDGES                                   │
│    • Android: Shizuku Binder UID 2000 (`rish -c id`), Doze whitelist.       │
│    • macOS: `launchd` SMAppService privileged helper & ScreenCaptureKit.   │
│    • Linux: Polkit D-Bus rules & ambient capabilities (`cap_net_admin`).     │
│    • OpenWrt: UNIX socket IPC (`/var/run/ubus/ubus.sock`) & Wi-Fi 7 info.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. AI MESH & SCREEN LENS SOVEREIGN VLA INTEGRATION                          │
│    • Rule 8 Latency Gate: RTT ≤ 0.55ms → TB4 DMA (:8082 TP)                 │
│                          RTT ≤ 10.0ms → Wi-Fi 7/Tailscale (:8083 PP)        │
│    • Rule 3 Host Sanctuary: Verified ≥ 4.8 GB free host RAM buffer.         │
│    • Screen Lens VLA: Port 3035 `lauburu-lens` frame capture & OCR loop.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ 1. Tri-Modal Component Matrix

| Component | Target Platforms | Path / Binary | Verification & Tests |
| :--- | :--- | :--- | :--- |
| **Unified Flutter App** | Android, macOS | `apps/omni_agent_flutter` | 24/24 Flutter tests pass, 0 analyze issues |
| **Headless Go Daemon** | Darwin ARM64 | `apps/omni_agent_daemon/bin/omni-daemon-local` | 37/37 Go tests with `-race`, 6.5 MB static ELF |
| **Headless Go Daemon** | Linux x86_64 | `apps/omni_agent_daemon/bin/omni-daemon-linux-amd64` | Cross-compiled static binary, 6.9 MB |
| **Headless Go Daemon** | Linux/OpenWrt ARM64 | `apps/omni_agent_daemon/bin/omni-daemon-linux-arm64` | Cross-compiled static binary, 6.3 MB |
| **Universal Web TUI & PWA** | Web Browsers (Chrome) | `apps/omni_agent_web` | Web Bluetooth NUS, xterm.js, service worker |

---

## 🛡️ 2. Empirical Verification Matrix (Zero-Mock Invariant)

- **Master E2E Test Suite (`tests/runner.py --tier all`)**:
  - Tier 1 (Feature Coverage): 52 / 52 PASSED
  - Tier 2 (Boundary & Corner Cases): 53 / 53 PASSED
  - Tier 3 (Fault Invariants & Recovery): 10 / 10 PASSED
  - Tier 4 (Real-World Workload Scenarios): 5 / 5 PASSED
  - **Total: 120 / 120 PASSED (Exit Code 0, 0.035s)**
- **Adversarial Stress Harness (`tests/adversarial_stress_harness.py`)**:
  - 21 / 21 PASSED (Socket permissions 0600, nonce replay rejection, Rule 3 RAM protection)
- **Protocol Burst & Fuzzing (`tests/adversarial_stress_test.py`)**:
  - 11 / 11 PASSED (1,500 messages, 25,357 MTU chunks, 256/256 HMAC bit-flips detected)

---

## 🔗 Related Architecture & Monorepo Links
- [[Index]]
- [[PROJECT_OVERVIEW]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[APPS_AND_FEATURES/OMNITERMINAL_CROSS_DEVICE_APP_INSTALLATION]]
- [[07_docs_and_architecture/SCREEN_LENS_SOVEREIGN_TUI_AND_NOTEBOOK_IDE_SPEC]]
