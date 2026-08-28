## 2026-08-24T12:12:04Z

You are the Project Orchestrator for the Lauburu monorepo.
Your working directory is: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_3
Repository root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo

Read the authoritative user request at: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

Mission & Requirements:
1. R1. Canonical Architecture Consolidation: Integrate Port 4000 Web Hub and lauburu_compute_hub into a single canonical architecture for account management and Bluetooth telemetry ingestion.
2. R2. Pixel Movesense Ingestion & Local Storage: Pull live Movesense telemetry using the Pixel device. Persist raw and processed data locally on the Pixel using SQLite or structured JSONL ledgers for offline/sync capabilities.
3. R3. Aggressive Compute Hub Pruning: Strip lauburu_compute_hub of unnecessary bloat (remove fl_chart and unused charting/plotting libraries, legacy UI tabs, deprecated non-Movesense/Polar sensors) to make it a lean engine dedicated exclusively to pure BLE ingestion and WebRTC/WebSocket forwarding. Ensure `./gradlew assembleDebug` succeeds and forwards BLE stream to Port 4000 hub.
4. R4. Mandatory Global Mesh Invariants: Ensure dynamic RAM ceilings, Antigravity MCP Models Server (164 verified multi-tier tests), Nomad Courier 24/7 background watchdog across ports 3000/4000/18802/50052, and 128Hz Movesense/Polar H10 zero-mock telemetry invariants are preserved.
