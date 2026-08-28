## 2026-08-26T01:10:00Z

Survey and audit the codebase design history specifically focusing on:
1. 01_apps (all applications including Port 4000 Hub, Movesense Hub, Zone 2, Shopify AI, 3D Grappling, Termux Edge Daemon, reconnect_project history, etc.)
2. 03_biometrics_and_telemetry (ECG, PTT BP, DFA-alpha1, Polysomnography, Movesense BLE sensor ingestion)
3. Key specific applications and daemons:
   - Movesense Biometrics Hub (Bluetooth daemon for ECG, Heart Rate, and LUDS Phone UI physical stress/readiness algorithm)
   - The Main Hub (`localhost:3000` / `localhost:4000`): Central commander UI consuming SSE telemetry from edge services
   - The Scout-to-Commander SSE Data Flow protocol and edge daemon broadcasting mechanisms preventing battery drain (The Brain Stem)

Explore actual files in the monorepo root and subfolders using native tools. Gather concrete code paths, UI components, REST/SSE endpoints, BLE GATT characteristics, mathematical stress formulas, and architecture blueprints.
