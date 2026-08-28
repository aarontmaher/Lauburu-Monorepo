# Worker Remediation Dispatch

## 2026-08-25T00:14:47Z

Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_remediation
Repository root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo

WRITE OWNERSHIP:
- `01_apps/port_4000_hub/tests/test_websocket.py`
- `01_apps/port_4000_hub/services/telemetry_service.py`
- `tests/test_android_build_verification.py`
- `01_apps/lauburu_compute_hub/services/port4000_forwarder.py`

Remediation Tasks:
1. Fix `01_apps/port_4000_hub/tests/test_websocket.py:16-29`:
   - In `override_sqlite_db` fixture, properly wire the test database manager to the global telemetry service:
     ```python
     telemetry_svc = get_telemetry_service()
     telemetry_svc.sqlite_manager = manager
     telemetry_svc.reset()
     ```
   - In `01_apps/port_4000_hub/services/telemetry_service.py`, ensure `TelemetryService` dynamically uses `get_sqlite_manager()` if `self.sqlite_manager` is None, and gracefully handles test isolation.
2. Fix `tests/test_android_build_verification.py` & `01_apps/lauburu_compute_hub/services/port4000_forwarder.py`:
   - In `tests/test_android_build_verification.py:155`, add `timeout=60` to `subprocess.run(["./gradlew", "tasks", "--dry-run"], ...)` to prevent indefinite hangs.
   - In `port4000_forwarder.py`, ensure `forward_ws_async` returns a clean status or warning if websockets dependency is not present, and ensure `test_port4000_http_and_ws_telemetry_forwarding` tests the WebSocket channel cleanly with mock/real websockets.
3. Run the verification test commands:
   - `uv run --with pytest --with pytest-asyncio --with httpx --with fastapi --with uvicorn --with websockets pytest 01_apps/port_4000_hub/tests -v`
   - `uv run --with pytest --with pytest-asyncio --with aiohttp --with websockets pytest tests/test_android_build_verification.py -v`
   - `uv run --with pytest --with pytest-asyncio pytest tests/e2e/test_canonical_mesh_integration_e2e.py -v`
4. Write a complete handoff report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_remediation/handoff.md`. Send a completion message when done.
