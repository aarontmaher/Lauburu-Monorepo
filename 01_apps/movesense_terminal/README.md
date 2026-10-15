# Movesense Terminal Lauburu

An asynchronous TUI for the Lauburu Ecosystem, built with Python and Textual.

## Features

- **Reactive Layouts**: TCSS-powered grid system with separation of concerns.
- **Zero-Mock Telemetry**: Only displays real data. Renders clean `DISCONNECTED` states if offline.
- **AsyncIO Architecture**: Leverages Textual's `@work` for non-blocking I/O event loops.
- **Readiness Display**: Metrics presentation.
- **Trend Analysis**: Sparkline-powered trends.
- **Adversarial Hardening**: Bounded log buffers and exception recovery.

## Remote Rendering / SSH (Edge Devices)

This application natively supports execution in standard SSH sessions.
To render remotely on edge devices (e.g., Pixel / Samsung phones) over SSH:

1. Start an SSH server on the L1 Mac Host or L3 Linux Hub.
2. From the Edge Device, SSH into the Host/Hub:
   ```bash
   ssh aaron@<host-ip>
   ```
3. Navigate to the app directory and run:
   ```bash
   cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/movesense_terminal/
   python app.py
   ```

*Alternatively, if using `textual-serve`, you can expose this app directly as a standalone SSH application without a full login shell.*
