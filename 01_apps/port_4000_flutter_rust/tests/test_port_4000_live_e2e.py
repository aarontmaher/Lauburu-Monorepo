#!/usr/bin/env python3
"""
Lauburu Port 4000 Console: Live Daemon E2E Verification Suite.
Validates live HTTP REST endpoints, WebSocket streams, and zero-mock baseline contracts on 0.0.0.0:4000.
"""

import asyncio
import json
import sys
import time
import urllib.request
import urllib.error
import pytest
import websockets

BASE_URL = "http://127.0.0.1:4000"
WS_URL = "ws://127.0.0.1:4000"

def http_get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Lauburu-E2E-Prober/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, resp.headers.get_content_type(), json.loads(resp.read().decode("utf-8"))

def http_get_raw(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Lauburu-E2E-Prober/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, resp.headers.get_content_type(), resp.read().decode("utf-8")

def http_post(path, data):
    url = f"{BASE_URL}{path}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Lauburu-E2E-Prober/1.0"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

class TestPort4000LiveDaemon:
    def test_tc_l1_health_endpoint(self):
        status, content_type, data = http_get("/health")
        assert status == 200
        assert content_type == "application/json"
        assert data["status"] == "HEALTHY"
        assert data["service"] == "lauburu_port4000_core"
        assert data["port"] == 4000
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0

    def test_tc_l2_zero_mock_snapshot(self):
        status, _, snap = http_get("/api/biometrics/snapshot")
        assert status == 200
        assert "timestamp" in snap or "timestamp_ms" in snap
        assert "device_id" in snap
        assert snap["sample_rate_hz"] == 512.0
        # If no sensor connected, verify strict zero-mock
        if not snap["connected"]:
            assert snap["heart_rate_bpm"] == 0.0
            assert snap["hrv_rmssd_ms"] == 0.0
            assert snap["dfa_alpha1"] == 0.0
            assert snap["readiness_score"] == 0.0
            assert snap["zone2_status"] == "Resting / Disconnected"
            assert snap["latest_ecg_sample"] == 0.0

    def test_tc_l3_biometrics_readiness(self):
        status, _, data = http_get("/api/biometrics/readiness")
        assert status == 200
        assert "readiness_score" in data
        assert "hrv_rmssd_ms" in data
        assert "heart_rate_bpm" in data
        assert "dfa_alpha1" in data
        assert "zone2_status" in data

    def test_tc_l4_spatial_map_standby(self):
        status, _, spatial = http_get("/api/spatial/map")
        assert status == 200
        assert "landmarks" in spatial
        assert len(spatial["landmarks"]) == 33
        assert spatial["current_position"] in ["Standby / Mat Empty", "Active Mat"]
        if spatial["current_position"] == "Standby / Mat Empty":
            assert spatial["active_technique"] == "No Athlete Detected"
            assert spatial["submission_risk_percent"] == 0.0
            for lm in spatial["landmarks"]:
                assert lm["visibility"] == 0.0
                assert lm["x"] == 0.0
                assert lm["y"] == 0.0
                assert lm["z"] == 0.0

    def test_tc_l5_shopify_token_verification(self):
        # 1. Pro Athlete
        status, pro_res = http_post("/api/shopify/verify", {"token": "lauburu_pro_sample_token"})
        assert status == 200
        assert pro_res["tier_code"] == 1
        assert pro_res["membership"]["tier"] == "ProAthlete"

        # 2. Crowdsourced Lifetime
        status, crowd_res = http_post("/api/shopify/verify", {"token": "lauburu_lifetime_crowdsourced_mac"})
        assert status == 200
        assert crowd_res["tier_code"] == 2
        assert crowd_res["membership"]["tier"] == "CrowdsourcedComputeLifetime"

        # 3. Free / Invalid
        status, free_res = http_post("/api/shopify/verify", {"token": "invalid_unknown_guest_token"})
        assert status == 200
        assert free_res["tier_code"] == 0
        assert free_res["membership"]["tier"] == "FreeCommunity"

    def test_tc_l6_sample_ingestion_and_reflection(self):
        sample_data = {
            "sample": 0.55,
            "heart_rate": 142.0,
            "rr_intervals": [422.5, 421.8],
            "device_id": "Movesense-PyTest-Live"
        }
        status, res = http_post("/api/biometrics/sample", sample_data)
        assert status == 200
        assert "is_qrs_peak" in res
        assert res["heart_rate_bpm"] == 142.0

    def test_tc_l7_ui_console_html_delivery(self):
        status, content_type, html = http_get_raw("/ui")
        assert status == 200
        assert "text/html" in content_type
        assert "LAUBURU" in html
        assert 'id="canvas-ecg"' in html
        assert 'id="canvas-tatami"' in html
        assert 'id="canvas-video"' in html
        assert "connectPixelBluetooth()" in html
        assert "0% MOCK DATA" in html
        assert 'id="val-hr"' in html

    @pytest.mark.asyncio
    async def test_tc_l8_ws_telemetry_stream(self):
        uri = f"{WS_URL}/ws/telemetry"
        async with websockets.connect(uri) as ws:
            packets = []
            for _ in range(10):
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(msg)
                packets.append(data)
                assert "timestamp" in data or "timestamp_ms" in data
                assert "heart_rate_bpm" in data
                assert "dfa_alpha1" in data
                assert "readiness_score" in data
            assert len(packets) == 10

    @pytest.mark.asyncio
    async def test_tc_l9_ws_spatial_stream(self):
        uri = f"{WS_URL}/ws/spatial"
        async with websockets.connect(uri) as ws:
            packets = []
            for _ in range(10):
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(msg)
                packets.append(data)
                assert "landmarks" in data or "athlete_nodes" in data
                assert "current_position" in data or "current_position_name" in data
            assert len(packets) == 10

    @pytest.mark.asyncio
    async def test_tc_l10_concurrent_ws_stress(self):
        async def client_session(client_id):
            uri = f"{WS_URL}/ws/telemetry"
            async with websockets.connect(uri) as ws:
                count = 0
                for _ in range(10):
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if msg:
                        count += 1
                return count

        tasks = [client_session(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        assert all(r == 10 for r in results)

if __name__ == "__main__":
    code = pytest.main(["-v", __file__])
    sys.exit(code)
