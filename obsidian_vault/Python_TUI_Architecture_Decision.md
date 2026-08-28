---
title: "Python TUI Architecture & Framework Decision"
tags: [tui, python, textual, bleak, asyncio, dsp, tailscale]
---
# Python TUI Ecosystem & Architectural Rationale

This document establishes Python as the canonical language and ecosystem for the Lauburu TUI control planes, overriding alternatives like Rust (Ratatui) or Go (Bubbletea) due to Python's unmatched synergy across asynchronous I/O, DSP, and AI.

## Core Framework: Textual
- **Architecture:** Modern, async-first, retained-mode framework built on `Rich`.
- **Advantage:** Runs natively on `asyncio`. Allows high-frequency Bluetooth (`bleak`), background processes, and network socket listeners to share the same event loop without complex multi-threading locks. 
- **Reactive Repainting:** A Movesense ECG notification triggers an `asyncio` callback that immediately updates a reactive variable in a Textual widget, repainting the frame instantly without thread locks.

## Embedded Digital Signal Processing (DSP)
- **Tooling:** `NumPy` and `SciPy` (`scipy.signal.butter`, `scipy.signal.lfilter`).
- **Use Case:** Processing raw biopotential vectors streaming from BLE. Calculating Pan-Tompkins QRS integration, optical PPG pulse oximetry ($SpO_2$), and real-time Heart Rate Variability (SDNN, RMSSD) via lightweight background async tasks.

## Tailscale & Unix Domain Sockets
- **Integration:** Interacting with local system daemons (e.g., `tailscaled` via `/var/run/tailscale/tailscaled.sock`) is mandated using `aiohttp` with a custom `UnixConnector`. This bypasses external network dependencies.

## Process Control & Orchestration
- **Mechanism:** `asyncio.create_subprocess_exec` is mandated for spawning background microservices (like local AI inference engines), non-blockingly capturing stdout/stderr streams, and applying regex log parsing.
