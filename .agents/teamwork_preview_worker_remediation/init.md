# Worker Remediation Working Directory
Task: Fix Reviewer 1 findings:
1. Fix `01_apps/port_4000_hub/tests/test_websocket.py` and `01_apps/port_4000_hub/services/telemetry_service.py` to ensure `TelemetryService` dynamically resolves `get_sqlite_manager()` and test fixture correctly binds `telemetry_svc.sqlite_manager = manager` and resets state.
2. Fix `01_apps/lauburu_compute_hub/services/port4000_forwarder.py` and `tests/test_android_build_verification.py` to add `timeout=60` to Gradle subprocess execution and ensure proper WebSocket frame validation.
3. Re-run all test suites (`01_apps/port_4000_hub/tests`, `tests/test_android_build_verification.py`, `tests/e2e/test_canonical_mesh_integration_e2e.py`).
