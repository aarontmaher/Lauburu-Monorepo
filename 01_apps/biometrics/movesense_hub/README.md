# Movesense Medical-Grade Bluetooth Hub

Dedicated Bluetooth Low Energy (BLE) background service capturing 128Hz raw ECG and 9-DoF IMU telemetry from Movesense sensors.

- Ingestion: BLE GATT Services
- Distribution: Local WebSockets (`ws://localhost:8088`), IPC broadcast to all monorepo apps.
