# App Name: Movesense Biometrics Dashboard

## 1. Global Theming & Tokens
- **Primary Color:** `#00FFAA` (Cyber Green)
- **Typography:** `Fira Code`, `Inter`
- **Component Standard:** Python Textual

## 2. Multi-Screen Flow (Infinite Canvas)

### Screen: `BiometricsDashboard`
- **Route:** `/dashboard`
- **Purpose:** Central hub for real-time live 512Hz ECG & Blood Pressure streaming.
- **State/Props:** `ecgStream`, `bloodPressureData`, `heartRate`, `connectionStatus`
- **Layout:**
  - Header: System Status, Connection indicator, Patient/Session ID
  - Main Area:
    - Top Panel: Real-time 512Hz ECG Waveform Chart (high-frequency plot)
    - Bottom Left: Blood Pressure (Systolic/Diastolic) numerical display
    - Bottom Right: Heart Rate (BPM) numerical display and historical trend sparkline
  - Footer: Control actions (Start/Stop Stream, Export Data, Auto-Scale)

### Screen: `SettingsScreen`
- **Route:** `/settings`
- **Purpose:** Configuration of Movesense sensor MAC, telemetry bounds, and display options.
- **State/Props:** `macAddress`, `samplingRate`, `theme`
- **Layout:**
  - Header: Back button, Title
  - Main Area: Configuration forms for sensor MAC, logging directory, alerts threshold
  - Footer: Save and Apply settings
