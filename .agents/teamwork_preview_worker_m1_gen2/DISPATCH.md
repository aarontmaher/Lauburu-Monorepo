## 2026-08-24T12:40:52Z

You are Worker M1 Gen 2 for Milestone 1: Canonical Port 4000 Hub Consolidation.
Your working directory is: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m1_gen2
Repository root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo

MANDATORY FIRST STEP: Read the authoritative user request at:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

Also read the Project blueprint at:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md
And Explorer 1 survey report at:
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_1/handoff.md

WRITE OWNERSHIP:
You have EXCLUSIVE write ownership of `01_apps/port_4000_hub/` (including `server.py`, `storage/`, `services/`, `data/`, `tests/`). Do NOT modify files outside your ownership boundary.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Milestone 1 Objectives:
1. Create `01_apps/port_4000_hub/storage/sqlite_manager.py` with SQLite WAL mode schema:
   - `users`: (id PK TEXT, email TEXT UNIQUE, name TEXT, role TEXT, password_hash TEXT, shopify_customer_id TEXT, membership_tier TEXT, is_paid_subscriber INTEGER, created_at_epoch INTEGER, installed_apps TEXT, paired_devices TEXT)
   - `sessions`: (session_token PK TEXT, user_id TEXT, created_at_epoch_ms INTEGER, updated_at_epoch_ms INTEGER, expires_at_epoch INTEGER, duration_sec INTEGER, total_ticks INTEGER, mean_sbp REAL, mean_dbp REAL, mean_map REAL, mean_hr REAL, mean_rmssd REAL, cardiac_drift_detected INTEGER, zone2_compliance_ratio REAL, status TEXT)
   - `telemetry_ticks`: (id INTEGER PRIMARY KEY AUTOINCREMENT, session_token TEXT, tick_epoch_ms INTEGER, delta_time_ms INTEGER, sensor_type TEXT, ptt_ms REAL, hr_bpm REAL, rr_ms REAL, rmssd_ms REAL, dfa_alpha1 REAL, ecg_mv REAL, imu_acc_g REAL, sbp_calc REAL, dbp_calc REAL, map_calc REAL, confidence_score REAL)
   - `trend_insights`: (id INTEGER PRIMARY KEY AUTOINCREMENT, session_token TEXT, timestamp_epoch_ms INTEGER, window_size_sec INTEGER, arterial_stiffness_drift_pct REAL, vascular_fatigue_index REAL, cardiac_drift_detected INTEGER, endothelial_reserve_status TEXT, zone2_compliance TEXT)
2. Create `01_apps/port_4000_hub/services/shopify_service.py` with Shopify Customer Account GraphQL verification and dev token fallback (`tok_dev_...`).
3. Create `01_apps/port_4000_hub/services/telemetry_service.py` with Movesense 128Hz / Polar H10 signal processing, Kamath 20% RR filter, and Zone 2 aerobic threshold classification.
4. Implement `01_apps/port_4000_hub/server.py` as a standalone FastAPI/Uvicorn application on port 4000:
   - `POST /api/auth/register` (PBKDF2 salted hash, creates user and session in SQLite, returns token and user)
   - `POST /api/auth/login` (verifies hash, creates session)
   - `POST /api/auth/shopify-login` (verifies Shopify token / dev token, issues session token)
   - `GET /api/auth/me` (session validation)
   - `POST /api/sensors/ingest` (stores telemetry tick in SQLite, associates with session, updates live state)
   - `GET /api/sensors/status` (zero-mock status probe: connected=False & heart_rate=null when disconnected, never fake data)
   - `WebSocket /ws/telemetry` (live bidirectional streaming)
   - `GET /api/apps` (returns catalog registry)
5. Create `01_apps/port_4000_hub/tests/test_port_4000_hub.py` and run tests via `pytest` to verify 100% passing.
6. Write a complete handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m1_gen2/handoff.md`. Send a completion message when done.
