# Port 4000 Canonical Web & Compute Hub

Canonical high-performance FastAPI/ASGI application serving unified user authentication, Shopify subscription tier verification, 128Hz Movesense/Polar BLE telemetry ingestion, real-time DSP signal processing, and WebSocket streaming.

- **Port**: `4000` (`0.0.0.0:4000`)
- **Backend Architecture**: FastAPI / Uvicorn / SQLite in WAL Mode
- **Core Storage**: `01_apps/port_4000_hub/data/port_4000_hub.db` (`users`, `sessions`, `telemetry_ticks`, `trend_insights`)
- **Authentication**: PBKDF2-HMAC-SHA256 salted password hashing, 64-char session tokens, and Shopify Customer Account GraphQL API integration.
- **Telemetry Ingestion**: 128Hz Movesense ECG/IMU & Polar H10 HRS, Kamath et al. (2004) 20% clinical artifact filtering, RMSSD, DFA-α1 aerobic threshold classification (Zone 2), and PTT blood pressure estimation.
- **Zero-Mock Rule #0**: Disconnected sensors strictly report `connected: false` and `heart_rate: null`.
- **Live Streaming**: Bidirectional WebSockets on `/ws/telemetry`.
- **Monorepo Registry**: 17 registered applications exposed on `GET /api/apps`.

