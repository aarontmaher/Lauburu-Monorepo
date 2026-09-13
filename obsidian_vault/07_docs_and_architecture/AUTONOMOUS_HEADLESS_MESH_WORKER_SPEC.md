---
title: "Autonomous Headless Mesh Worker Specification: Movesense Connectivity & IP-Less Bluetooth Terminal"
tags: [opencode, go, daemon, movesense, bluetooth, tcp_bridge, layer0, tri_proof]
generated: 2026-09-13 12:58 AEST
---

# ⚡ Autonomous Headless Mesh Worker Architecture (2026)

## 🏛️ 1. Executive Summary

This architecture establishes a universal, cross-platform, autonomous background mesh worker built on the **OpenCode Go daemon substrate** (`06_scripts_and_tooling/lauburu-opencode-cli`).

It operates silently as a system service (`launchd` on macOS, `systemd` on Linux, and `termux-wake-lock` on Android), fulfilling three core architectural mandates:
1. **Full Project & Network Dependencies:** Integrates 7-layer mesh topology monitoring, local AI routing to **Qwen 3.8 Max** (`:8082`), and bi-directional TCP/WebSocket streaming to **Port 4050 / 4051**.
2. **Movesense BLE Connectivity:** Hardware BLE 0x180D scanner and continuous 512Hz Pan-Tompkins QRS DSP telemetry ingestion (heart rate BPM, RMSSD, DFA-\alpha_1 Zone 2 threshold, and battery level).
3. **IP-less Movesense Bluetooth Terminal:** Operates over Layer 0 raw Bluetooth radio MAC (`0.0.0.0` / zero IP stack dependency) via Nordic UART Service (NUS) and RFCOMM SPP, enforcing strict Kai Morich anti-staircasing CRLF (`\r\n`) formatting and M1–M10 macro shortcuts.

---

## 🏗️ 2. Subsystem Topology & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 AUTONOMOUS HEADLESS MESH WORKER TOPOLOGY                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. LAYER 0: PHYSICAL BLE & SERIAL HARDWARE                                  │
│    • Nordic UART Service (NUS): UUID 6E400001-B5A3-F393-E0A9-E50E24DCCA9E   │
│    • Movesense BLE Sensor: Heart Rate Service (0x180D) & 512Hz ECG stream   │
│    • RFCOMM Classic SPP: /dev/tty.Bluetooth-Incoming-Port (115200 8N1)      │
│    • Out-of-Band Unix Pipes: /tmp/bluetooth_terminal_stream.ansi            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. BIOMETRICS & PAN-TOMPKINS DSP BUFFER                                     │
│    • TelemetryBuffer: Live R-R intervals, RMSSD HRV, DFA-alpha1 Zone 2      │
│    • MeshStreamWatcher: /tmp/movesense_live_stream.json syncer              │
│    • Rule #0 Truth Audit: Clean standby state when physical sensor idle     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. PIPING & NETWORK DAEMON (TCP :4050 / :4051 & TAILSCALE)                 │
│    • TCPBridge: Listens on 0.0.0.0:4050 (or :4051 fallback)                │
│    • WebSocket Client Bridge: Piped into Port 4050 Terminal IDE             │
│    • Kai Morich Macro Dispatch: M1 (status), M2 (telemetry), M3 (ram),      │
│      M4 (movesense/bicep), M5 (reconnect), M6 (clear), M7 (voice), M8 (help)│
│    • Local AI Orchestrator: Direct streaming REST to Qwen 3.8 Max (:8082)   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. SERVICE INTEGRATION & BACKGROUND KEEPALIVE                               │
│    • macOS Darwin: ~/Library/LaunchAgents/com.lauburu.mesh-worker.plist     │
│    • Linux: /etc/systemd/system/lauburu-mesh-worker.service                 │
│    • Android Termux: start_mesh_worker_android.sh (termux-wake-lock)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 3. Tri-Proof Verification Receipts

| Verification Gate | Method / Target | Result | Empirical Proof Reference |
| :--- | :--- | :--- | :--- |
| **Proof 1 (Actuation)** | Go Unit Test Suite (`terminal_test.go`, `tcp_bridge_test.go`) | **13/13 PASSED** | Exit Code 0 in 1.005s |
| **Proof 1 (E2E Test)** | `tests/test_headless_mesh_worker.py` | **5/5 PASSED** | Exit Code 0 in 2.490s |
| **Proof 2 (Line-by-Line)** | Darwin Binary (`lauburu`) | **31,983,522 Bytes** | `2d23d0c5817d708de1e66a49b503bd12dbbb4d770e7cb5a9eadd49f5d8d85e5d` |
| **Proof 2 (Android PIE)** | Android Binary (`lauburu_android`) | **32,506,137 Bytes** | `7f2ecf944bfe5acef7c37649377fd24f97461d483ced384ebdd7c9538294c6c0` |
| **Proof 3 (TCP Pipe)** | TCP Bridge Port 4051 | **Verified Live** | Banner received, M1..M4 commands executed |
| **Rule #3 Sanctuary** | Darwin Mach vm_stat Headroom | **5.75 GB Free/Inactive** | Requirement $\ge 4.8\text{ GB}$ preserved |

## 🏛️ Tri-Vault Wikilinks
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[OPENCODE_GO_BLUETOOTH_TERMINAL_UPDATE]]
- [[SCREEN_LENS_LIVE_OBSERVATIONS]]
