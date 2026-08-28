## 2026-08-26T06:26:34Z
You are the Movesense Hardware Tether Worker.
Your working directory is: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m3_tether/
You must read:
1. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md
2. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md
3. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/07_docs_and_architecture/MOVESENSE_BLUETOOTH_ARCHITECTURE_DEBATE.md
4. /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/spec_miner_survey_movesense/handoff.md

You exclusively own these files:
- `01_apps/lauburu_compute_hub/services/movesense_ingestion.py`
- `00_core_infrastructure/self_healing_hub/frontend/src/ComputeHubWebView.jsx`

Your objective:
1. Wire "Link to Compute Hub" UI button in `ComputeHubWebView.jsx`:
   - When clicked, trigger backend BLE connection sequence (e.g. `POST /api/movesense/connect` or WebSocket command).
   - Display live connection state, BLE device name, battery status, and streaming status.
   - Support zero-install Web Bluetooth (WebBLE) pairing fallback for direct browser connection to Heart Rate Service (`0x180D`).
2. Upgrade `01_apps/lauburu_compute_hub/services/movesense_ingestion.py`:
   - Implement Bleak Async GATT client targeting genuine 128-bit Movesense MDS Service UUID (`34800001-7185-4d5d-b431-b30e393d9e05`), Data characteristic (`34800002-7185-4d5d-b431-b30e393d9e05`), and standard SIG HRS (`0x180D`).
   - Decode raw 128Hz ECG and 52Hz IMU binary SBEM packets.
   - Apply Kamath 2004 20% clinical RR filter, RMSSD, and 120s rolling DFA-alpha1 Zone 2 DSP.
   - Stream decoded frames via WebSocket `/ws/movesense/stream`.
   - Strict Rule #0 Zero-Mock Compliance: when sensor is disconnected, return explicit `WAITING_FOR_SENSOR` state with null metrics. Absolutely zero fake data or simulated UUIDs.
3. Run python syntax/unit tests to verify decoders and ingestion pipeline execute cleanly without errors.
