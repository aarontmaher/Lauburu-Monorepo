# Dead Ends: Lauburu Mesh Fallback Terminal

Append-only log of invalidated approaches to prevent oscillation.

| Iteration | Approach Tried | Why It Failed | Files Touched |
|-----------|---------------|---------------|---------------|
| Exp 1 / 3 | `while True: time.sleep(0.5)` in Textual `@work(thread=True)` | Thread loop never checks `self.is_running`, preventing Textual worker manager teardown and hanging async pilot tests | `src/bluetooth_terminal_app.py` |
| Exp 1 | Creating new `asyncio` event loop per thread for `BleakClient` operations | `BleakClient` futures are bound to originating event loop; cross-loop writes violate CoreBluetooth/BlueZ threading contracts | `src/bluetooth_terminal_app.py` |
| Exp 3 | Relying on `which mosh` without fallback | `mosh` binary is not installed by default on host Mac; requires adaptive fallback to `/usr/bin/ssh` | `src/mesh_healer/session_spawner.py` |
| Exp 3 | Using synchronous ICMP subprocess `ping` in UI thread | Blocks Textual UI event loop, causing framerate stutter and input latency | `src/mesh_healer/outage_detector.py` |
