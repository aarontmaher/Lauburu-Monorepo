---
title: "Nordic Semiconductor MCP — Deep Research, OSS Scout & Reverse Engineering"
tags: [lauburu, mcp, nordic, reverse_engineering, zephyr, embedded, rtt, ble]
created: 2026-09-30
---

# 📡 Nordic Semiconductor Model Context Protocol (MCP) Analysis

This document synthesizes the empirical findings, clean-room protocol extraction, open-source scouting, and installation architecture for Nordic Semiconductor's AI-assisted development tools across the Lauburu Mesh.

---

## 🏛️ 1. Architecture Overview: Dual-Plane MCP Topology

Nordic Semiconductor decouples its AI tooling into two distinct architectural planes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NORDIC MCP DUAL-PLANE ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. REMOTE KNOWLEDGE PLANE: "nordic-mcp"                                     │
│    • Endpoint: https://aidev.nordicsemi.com/mcp                             │
│    • Transport: HTTP/2 Streamable MCP (POST + DELETE), SSE                  │
│    • Auth: OAuth 2.0 PKCE (S256), Bearer Token, Scope: "Read"              │
│    • Content: nRF Connect SDK (NCS) Docs, DevAcademy, DevZone Q&A, API Ref  │
│    • Context Injection: Propagates x-nordic-tools header map to scope       │
│      answers to local workspace and connected development kit hardware.     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. LOCAL WORKSPACE & HARDWARE PLANE: "nrfConnect"                            │
│    • Endpoint: http://127.0.0.1:60219/mcp (Default port: 60219)             │
│    • Transport: HTTP/SSE Streamable MCP (stateless mode)                  │
│    • Auth: Localhost loopback (127.0.0.1)                                   │
│    • Content: 21 workspace, compilation, flashing, RTT, and serial tools   │
│    • Host Integration: Zephyr 'west', SEGGER J-Link RTT, UART Serial, CMake │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🕵️‍♂️ 2. Closed-Source Reverse Engineering Results (Rule 4 Sandbox)

- **Target Disassembled:** `nordic-semiconductor.nrf-connect-2026.9.2823-darwin-arm64/dist/extension.js`
- **Target SHA256:** `fc36caf91faa2ca48b420717ce2107b400c5a38786668ce6eacb16e83c0ef720`
- **Formal Spec Created:** `[[SPEC_NORDIC_MCP]]` at `01_apps/screen_lens/sandbox_evolution/reverse_engineering/specs/SPEC_NORDIC_MCP.md`
- **Clean-Room Implementation:** `01_apps/screen_lens/sandbox_evolution/reverse_engineering/clean_room_impl/nordic_mcp/nordic_mcp_standalone_server.py`
- **Empirical Test Verification:** Passed all 4 test suites with **Exit Code 0** (`test_nordic_mcp_cleanroom.py`).

### The 21 Local Tools Catalog
1. `nrfconnect_build_source` — CMake/Ninja build
2. `nrfconnect_get_build_result` — Compiler diagnostics
3. `nrfconnect_list_applications` — Scan workspace applications
4. `nrfconnect_open_application` — Activate project root
5. `nrfconnect_search_board_targets` — Hardware board discovery
6. `nrfconnect_create_build` — Pristine build directory setup
7. `nrfconnect_debug_device` — J-Link GDB debugging
8. `nrfconnect_list_builds` — Build configurations
9. `nrfconnect_describe_build` — Kconfig & DeviceTree inspection
10. `nrfconnect_flash_device` — West flash / J-Link programming
11. `nrfconnect_get_flash_result` — Verification outcome
12. `nrfconnect_get_terminal_env` — West environment export
13. `nrfconnect_install_sdk` — NCS toolchain installer
14. `nrfconnect_get_install_sdk_result` — Toolchain extraction progress
15. `nrfconnect_list_connected_devices` — Probes & serial ports
16. `nrfconnect_list_installed_sdks` — Local SDK installations
17. `nrfconnect_reset_device` — Hardware pin/soft reset
18. `nrfconnect_get_serial_output` — UART CDC-ACM stream
19. `nrfconnect_send_serial_input` — UART command transmission
20. `nrfconnect_get_rtt_output` — SEGGER RTT Channel 0 reader
21. `nrfconnect_send_rtt_input` — SEGGER RTT Channel 0 writer

---

## 🔍 3. Open-Source Software Scout: Top 3 Alternatives

| Tool | Ecosystem / Language | License | Telemetry | Mesh Feasibility | Key Differentiator |
|---|---|---|---|---|---|
| **probe-rs** | Embedded Rust (`probe-rs-tools`) | Apache 2.0 / MIT | Zero | High (macOS M4, Linux AMD64/ARM64, Android NDK) | Non-blocking RTT logging; vendor-agnostic CMSIS-DAP & J-Link support without proprietary licensing. |
| **west** | Zephyr Project / Python | Apache 2.0 | Zero | Universal (Runs anywhere Python 3 exists) | Canonical meta-tool for multi-repo Zephyr & NCS management, pristine builds, and flashing. |
| **pyOCD** | Python / CMSIS-DAP | Apache 2.0 | Zero | Universal | Native SWD/JTAG debugger & flash programming library with GDB server. |

---

## 🔬 4. Empirical Benchmarks & Hardware Economics (Rule #0)

- **Network Telemetry to `aidev.nordicsemi.com`:**
  - DNS Lookup: `0.0239s`
  - TCP Handshake: `1.204s`
  - TLS Handshake (TLSv1.3 CHACHA20-POLY1305): `1.823s`
  - TTFB: `3.283s`
  - Total Round-Trip: `3.283s`
- **Live Australian Spot Pricing (Rule #0 Zero-Mock):**
  - **nRF52840-DK:** **$77.22 AUD** (element14 Australia, inc. GST; $70.20 ex. GST).
  - Hardware capabilities: Bluetooth 5.4, Bluetooth Mesh, Thread, Zigbee, NFC-A, onboard SEGGER J-Link debugger.

---

## ⚙️ 5. Monorepo Installation & Active Configuration

Both Nordic MCP servers have been registered in:
- `/Users/aaron/.gemini/config/mcp_config.json`
- `/Users/aaron/.gemini/antigravity-cli/mcp_config.json`

```json
{
  "mcpServers": {
    "nordic-mcp": {
      "headers": {
        "Accept": "application/json, text/event-stream"
      },
      "serverUrl": "https://aidev.nordicsemi.com/mcp"
    },
    "nrfconnect": {
      "headers": {
        "Accept": "application/json, text/event-stream",
        "x-nordic-client": "nrf-connect-vscode"
      },
      "serverUrl": "http://127.0.0.1:60219/mcp"
    }
  }
}
```
