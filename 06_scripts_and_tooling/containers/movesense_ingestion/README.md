# Movesense Sovereign Podman Ingestion Configurations

This directory contains three modular **Podman container configurations** for high-frequency Movesense biometrics (Heart Rate, RR intervals, ECG) and 9-axis IMU kinematic streaming (Linear Acceleration, Gyroscope, Magnetic Field) across the 7-Layer hardware mesh.

Each configuration provides a specialized ingestion topology to bypass desktop/driver limitations, support headless Linux execution (Node L8 `lauburu` / Node L3 `linux-amd-gpu`), and adhere to **Rule 1 (Zero-Mock Truth)**.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       Movesense MD Sensor             |
                      |       (BLE GATT / RFCOMM SPP)         |
                      +---------------------------------------+
                                          |
               +--------------------------+-------------------------+
               |                          |                         |
               v                          v                         v
     [Config 1: Chromium]        [Config 2: Go GATT]       [Config 3: BT Serial]
   +---------------------+    +---------------------+    +---------------------+
   | Headless Chromium   |    | Go BLE / GATT       |    | BlueZ RFCOMM SPP    |
   | Web Bluetooth API   |    | Low-Latency SSE     |    | Serial Terminal     |
   | DevTools CDP :9222  |    | Embedded Dashboard  |    | Port :8089          |
   | Web UI :9223        |    | Port :8084          |    | Telemetry WS Bridge |
   +---------------------+    +---------------------+    +---------------------+
               |                          |                         |
               +--------------------------+-------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |   04_data_and_memory/movesense_parquet|
                      |   - showcase_linear_acceleration      |
                      |   - showcase_angular_velocity         |
                      |   - grappling_imu_telemetry (355k)    |
                      |   - grappling_rr_intervals (91k)      |
                      +---------------------------------------+
```

---

## Configurations

### 1. Headless Chromium Browser (`chromium_web_bluetooth/`)
- **Base Image:** `debian:bookworm-slim`
- **Engine:** Headless Chromium with `--enable-web-bluetooth`, `--headless=new`, and Chrome DevTools Protocol (`:9222`).
- **Telemetry UI:** Responsive HTML5 Web Bluetooth dashboard on port `:9223`.
- **Use Case:** Direct browser-based Web Bluetooth ingestion without native host BLE stack compilation; integrates seamlessly with Screen Lens DevTools automation.
- **Run command:**
  ```bash
  bash chromium_web_bluetooth/run.sh
  ```

### 2. Go GATT Browser (`go_gatt_browser/`)
- **Base Image:** `golang:1.23-bookworm` (Multi-stage build)
- **Engine:** Pure Go HTTP/SSE server with low-latency event broadcasting.
- **Telemetry UI:** Embedded high-speed SVG charting dashboard on port `:8084`.
- **Endpoints:**
  - `GET /`: Real-time browser dashboard
  - `GET /events`: Server-Sent Events (SSE) stream
  - `POST /api/ingest`: JSON ingestion endpoint
  - `GET /api/state`: Snapshot of latest kinematic and cardiac state
- **Run command:**
  ```bash
  bash go_gatt_browser/run.sh
  ```

### 3. Bluetooth Serial / RFCOMM Browser (`bluetooth_serial_rfcomm/`)
- **Base Image:** `debian:bookworm-slim` (BlueZ + Python aiohttp)
- **Engine:** Linux BlueZ RFCOMM Serial Port Profile (SPP) daemon binding to `/dev/rfcomm0`.
- **Telemetry UI:** Interactive dark-mode serial terminal console on port `:8089`.
- **Use Case:** Zero-infrastructure raw serial streaming, debugging raw NMEA/hex frames, and hardware command actuation.
- **Run command:**
  ```bash
  bash bluetooth_serial_rfcomm/run.sh
  ```

---

## Linux Deployment & D-Bus Socket Invariant

All Bluetooth containers running on Linux (L8 `lauburu` over TB `10.0.0.8` or L3 `linux-amd-gpu`) **MUST** mount the host D-Bus system bus socket:

```bash
--net=host \
--privileged \
-v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket:ro \
-v /sys/class/bluetooth:/sys/class/bluetooth:ro
```

*Note: The previous crash of `lauburu-port4000-backend` on L8 was caused by omitting `/run/dbus/system_bus_socket`. These Podman scripts include the volume mount natively.*

---

## Unified Deployment

Launch all three configurations or a single target using the unified orchestrator:

```bash
# Launch a specific configuration:
./deploy_movesense_podman.sh chromium
./deploy_movesense_podman.sh go
./deploy_movesense_podman.sh rfcomm

# Launch all configurations simultaneously:
./deploy_movesense_podman.sh all
```
