---
title: "Session Archive & Technical Handoff: Pixel 10 Pro XL Sovereign Terminal & Port 4000/4005 PTY Architecture"
date: "2026-09-07"
tags: [archive, handoff, pixel_10_pro_xl, terminal, movesense, npu, port_4000, port_4005, screen_lens, axum, rust]
---

# 🏛️ Session Archive & Technical Handoff: Sovereign Terminal & Mesh Console

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[CANONICAL_APPS_OVERVIEW]]
- [[07_HANDOFFS/2026-09-02_CANONICAL_NOTEBOOK_AND_TUI_PROJECT_HANDOFF]]

---

## 1. Executive Summary of Session Accomplishments

This session addressed the complete end-to-end operationalization of the **Sovereign Console & Terminal** on Aaron's **Google Pixel 10 Pro XL** (`192.168.8.145:36815` / Tailscale: `100.73.38.87`), bridging physical BLE biometrics, native Rust Axum WebSockets, and Linux/Darwin PTY login shells.

### Key Milestones Delivered:
1. **Multi-Gigabit & Switch Hardware Scouting:** Formulated buyable multi-gigabit switch and cabling architectures for St Kilda Melbourne via JB Hi-Fi and local retail channels.
2. **FastAPI PTY Subprocess Fix:** Resolved Darwin `os.fork()` crashes on macOS Sequoia by adopting thread-safe `pty.openpty()` and `subprocess.Popen([shell, "-l"])`.
3. **Port 4000 Launchd Daemon Upgrade (Rust Axum):**
   - Discovered that launchd service `com.lauburu.sovereign` (`/Users/aaron/.local/bin/lauburu-sovereign`) bound port 4000.
   - Upgraded `01_apps/port_4000_flutter_rust/rust_backend/src/server.rs` with `tower_http::services::ServeDir` for `/terminal/` static files (`HTTP 200 OK`).
   - Replaced dummy `/ws/terminal` echo stub with an asynchronous bidirectional bridge to the live `bluetooth_serial_terminal_daemon.py` on TCP 4005.
4. **Sovereign Console UI Integration:**
   - Added **`📶 Bluetooth Serial Terminal`** tab to `flutter_ui/build/index.html`.
   - Wired live WebSocket telemetry with ANSI code filtering, 10 instant macros (M1–M10), command input field, and mobile soft-keys.
5. **Mobile Launcher & Screen Lens Diagnosis:**
   - Diagnosed why Aaron reported *"its not there"*: Android NexusLauncher pinned the Chrome PWA shortcut to **Page 2** (Row 2, Column 3) rather than the default Page 1 wake screen.
   - Confirmed `com.lauburu.sovereign` (native APK) and `de.kai_morich.serial_bluetooth_terminal` are installed and operational on the device.

---

## 2. Network & Port Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   SOVEREIGN TERMINAL PORT & DAEMON FLOW                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Bluetooth Serial Daemon (Port 4005 & /dev/tty.Bluetooth-Incoming-Port)   │
│    • PID: 58425 (python3.11 06_scripts_and_tooling/bluetooth_serial_...)    │
│    • Spawns dedicated PTY login shell per client (RFCOMM + TCP 4005).       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Sovereign Rust Server (Port 4000)                                        │
│    • PID: 63962 (/Users/aaron/.local/bin/lauburu-sovereign via launchd)      │
│    • Serves Multi-Tab HUD (Biometrics, NPU, Terminal, Mesh, Spatial).       │
│    • /terminal/ -> Serves static Omni Terminal PWA.                         │
│    • /ws/terminal -> Asynchronously bridges WebSocket to TCP 127.0.0.1:4005.│
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Client Surfaces on Google Pixel 10 Pro XL                                │
│    • Native App: com.lauburu.sovereign (Loads http://100.119.199.76:4000)   │
│    • Standalone PWA: http://192.168.8.155:4000/terminal/                   │
│    • SPP Serial App: de.kai_morich.serial_bluetooth_terminal (TCP 4005/RFCOMM│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Empirical Verification Evidence (Rule 1 & Rule 5 Compliance)

- **HTTP 200 Verification:**
  `curl -i http://127.0.0.1:4000/terminal/ | grep "HTTP/1.1 200 OK"` (Exit Code 0, Content-Length: 14902)
- **WebSocket Echo Verification:**
  Python websockets client test to `ws://127.0.0.1:4000/ws/terminal` received banner + echo in 18ms.
- **Physical Sensor Data Stream:**
  Movesense BLE `Movesense-261030002013` connected: Heart Rate 82 BPM, HRV 491.3 ms, DFA-alpha1 0.82, Readiness 67.
- **Physical Device Screen Captures Saved:**
  - `home_fresh.png`: Confirms `Omniter...` on Page 2 at bounds `[560,483][776,745]`.
  - `omni_opened.png`: Confirms live 512Hz oscilloscope and biometrics in Sovereign Console.
  - `sovereign_reloaded.png`: Device screen state under biometric keyguard.

---

## 4. Instructions for Resuming / Subsequent Sessions

When starting a new session:
1. All changes are committed to the code repository and mirrored in the Tri-Vault.
2. The Port 4000 Rust server and Port 4005 Bluetooth daemon remain alive under launchd (`com.lauburu.sovereign.plist` and background processes).
3. To open the terminal on the Pixel, simply launch `Sovereign` and tap the **📶 Bluetooth Serial Terminal** tab, or open `http://192.168.8.155:4000/terminal/` in Chrome.
