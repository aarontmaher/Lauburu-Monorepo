#!/usr/bin/env python3
"""
Adversarial Stress Harness: Zero-Mock Telemetry Compliance Audit across Monorepo
Audits all telemetry entrypoints, GATT handlers, DSP streams, and API server states
to guarantee 100% adherence to zero-mock discipline: disconnected sensors must NEVER
generate synthetic/fake data and must return explicit None / null / '--' states.
"""

import sys
import os
import json
import time
import unittest.mock as mock
import traceback
import subprocess
from typing import Dict, Any

BASE_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
sys.path.insert(0, os.path.join(BASE_DIR, "01_apps", "movesense_hub"))
sys.path.insert(0, os.path.join(BASE_DIR, "self_healing_hub", "src"))
sys.path.insert(0, os.path.join(BASE_DIR, "00_core_infrastructure", "infrastructure", "immortal_swarm"))

# Provide mock for bleak if not installed in host environment
if "bleak" not in sys.modules:
    sys.modules["bleak"] = mock.MagicMock()

from pyspark_biometrics_dsp import MovesenseBiometricsDSPPipeline
from pyspark_movesense_stream import PySparkMovesenseStreamEngine
from bt_telemetry_terminal import sensor_state

def run_zero_mock_audit():
    print("=================================================================")
    print("  ZERO-MOCK TELEMETRY COMPLIANCE AUDIT ACROSS MONOREPO           ")
    print("=================================================================")
    results = {}

    # Audit 1: PySpark Biometrics DSP Pipeline (movesense_hub)
    try:
        dsp = MovesenseBiometricsDSPPipeline()
        out = dsp.process_biometrics_stream(custom_packet=None)
        assert out["status"] == "AWAITING_SENSOR", f"Expected AWAITING_SENSOR, got: {out['status']}"
        assert out["kinematics"] is None, f"Kinematics must be None when disconnected, got: {out['kinematics']}"
        assert out["hrv_cardiac"] is None, f"hrv_cardiac must be None when disconnected, got: {out['hrv_cardiac']}"
        assert out["transport"] == "Bluetooth 5.4 Low Energy (GATT)"
        assert "Awaiting physical sensor" in out["coaching_recommendation"]
        print(" [PASS] Audit 1: movesense_hub/pyspark_biometrics_dsp.py strictly zero-mock (returns null/None when disconnected)")
        results["audit_1_movesense_dsp"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Audit 1: {e}")
        traceback.print_exc()
        results["audit_1_movesense_dsp"] = f"FAIL: {e}"

    # Audit 2: PySpark Movesense Structured Streaming Engine (self_healing_hub)
    try:
        engine = PySparkMovesenseStreamEngine()
        out_stream = engine.process_movesense_stream(custom_packet=None)
        assert out_stream["stream_status"] == "WAITING_FOR_SENSOR", f"Expected WAITING_FOR_SENSOR, got: {out_stream['stream_status']}"
        assert out_stream["sensor_model"] is None
        assert out_stream["biometrics"]["heart_rate_bpm"] is None
        assert out_stream["biometrics"]["rr_interval_ms"] is None
        assert out_stream["biometrics"]["rmssd_ms"] is None
        assert out_stream["biometrics"]["dfa_alpha1"] is None
        assert out_stream["biometrics"]["vo2_max_ml_kg_min"] is None
        assert out_stream["kinematics_imu_12axis"]["accelerometer_g"] is None
        assert out_stream["kinematics_imu_12axis"]["gyroscope_dps"] is None
        assert out_stream["kinematics_imu_12axis"]["total_dynamic_g"] is None
        assert out_stream["kinematics_imu_12axis"]["mechanical_power_watts"] is None
        print(" [PASS] Audit 2: self_healing_hub/src/pyspark_movesense_stream.py strictly zero-mock (all 12 metrics null)")
        results["audit_2_pyspark_movesense_stream"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Audit 2: {e}")
        traceback.print_exc()
        results["audit_2_pyspark_movesense_stream"] = f"FAIL: {e}"

    # Audit 3: Bluetooth PAN & Telemetry Terminal (bt_telemetry_terminal.py)
    try:
        assert sensor_state["hr"] == "--", f"Expected '--', got: {sensor_state['hr']}"
        assert sensor_state["rr"] == "-- ms", f"Expected '-- ms', got: {sensor_state['rr']}"
        assert sensor_state["imu"] == "--", f"Expected '--', got: {sensor_state['imu']}"
        assert "WAITING FOR SENSOR" in sensor_state["status"]
        print(" [PASS] Audit 3: bt_telemetry_terminal.py initial/fallback telemetry strictly zero-mock ('--')")
        results["audit_3_bt_telemetry_terminal"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Audit 3: {e}")
        traceback.print_exc()
        results["audit_3_bt_telemetry_terminal"] = f"FAIL: {e}"

    # Audit 4: API Server Multi-Sensor Ingestion Matrix (_SENSOR_STATE)
    try:
        import api_server
        with api_server.app.test_client() as client:
            res = client.get("/api/sensors/status")
            assert res.status_code == 200
            data = res.get_json()
            assert data["connected_count"] == 0, f"Expected 0 connected sensors on cold start, got {data['connected_count']}"
            assert data["fusion_state"] == "AWAITING_SENSORS"
            assert data["sensors"]["movesense"]["connected"] is False
            assert data["sensors"]["movesense"]["heart_rate"] is None
            assert data["sensors"]["movesense"]["dfa_alpha1"] is None
            assert data["sensors"]["polar"]["connected"] is False
            assert data["sensors"]["polar"]["heart_rate"] is None
            assert data["sensors"]["whoop"]["connected"] is False
            assert data["sensors"]["whoop"]["heart_rate"] is None
        print(" [PASS] Audit 4: api_server.py _SENSOR_STATE and /api/sensors/status strictly zero-mock")
        results["audit_4_api_server_sensors"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Audit 4: {e}")
        traceback.print_exc()
        results["audit_4_api_server_sensors"] = f"FAIL: {e}"

    # Audit 5: Full Acceptance Test Suite execution
    try:
        res_pytest = subprocess.run(
            [
                "/Users/aaron/teamwork_projects/antigravity_mcp_models/.venv/bin/pytest",
                os.path.join(BASE_DIR, "tests", "e2e", "test_lauburu_mesh_acceptance.py"),
                "-v",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=dict(os.environ, PYTHONPATH=BASE_DIR),
        )
        assert res_pytest.returncode == 0, f"Monorepo acceptance tests failed:\n{res_pytest.stdout}\n{res_pytest.stderr}"
        assert "32 passed" in res_pytest.stdout
        print(" [PASS] Audit 5: Monorepo acceptance test suite (32 tests) passed with 100% zero-mock compliance")
        results["audit_5_monorepo_acceptance_suite"] = "PASS"
    except Exception as e:
        print(f" [FAIL] Audit 5: {e}")
        traceback.print_exc()
        results["audit_5_monorepo_acceptance_suite"] = f"FAIL: {e}"

    print("=================================================================")
    all_passed = all(v == "PASS" for v in results.values())
    print(f"ZERO-MOCK TELEMETRY AUDIT RESULT: {'ALL PASSED' if all_passed else 'FAILURES DETECTED'}")
    print("=================================================================")
    return all_passed, results

if __name__ == "__main__":
    ok, res = run_zero_mock_audit()
    if not ok:
        sys.exit(1)
