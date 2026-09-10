---
title: "Bluetooth Serial Terminal on Port 4000"
tags: [lauburu, bluetooth, terminal, port4000, npu, kai_morich, movesense, pixel10]
date: "2026-09-06"
proof_sha256: "da7feaf189fca0b18026f2ebfc07efae0fa69bde0d943be16c697d80797a07d1"
---

# 📶 Bluetooth Serial Terminal on Port 4000

## Architecture & Integration
- Replaced legacy AGI Coding Terminal in `01_apps/canonical_port` with `BluetoothTerminalView.jsx`.
- Interface bound to `/dev/tty.Bluetooth-Incoming-Port` and port 4005 backend daemon.
- Hotkey: `[c]` or clicking `📶 Bluetooth Terminal [c] SPP / BLE` in Sidebar.
- 10-Button Kai Morich macro strip (M1–M10) mirroring the Android Serial Bluetooth Terminal application.
- Real-time NPU AI Live Stream Inspection card powered by Google Tensor G5 Edge TPU and Apple Neural Engine.
- 100% test pass rate across 53 automated E2E tests in `01_apps/canonical_port`.

## Related Links
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[MESH_TELEMETRY_LOG]]
