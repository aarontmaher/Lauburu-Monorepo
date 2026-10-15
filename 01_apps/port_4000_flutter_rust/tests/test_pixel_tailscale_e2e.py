#!/usr/bin/env python3
"""
Lauburu Port 4000 Console: Pixel 10 Pro XL Tailscale E2E Live Verification Suite.
Executes remote verification over Tailscale WireGuard mesh from Google Pixel 10 Pro XL (100.73.38.87).
"""

import base64
import json
import subprocess
import sys
import time
import pytest

PIXEL_IP = "100.73.38.87"
PIXEL_SSH_PORT = "8022"
PIXEL_USER = "u0_a363"
HOST_IP = "100.119.199.76"
HOST_PORT = "4000"

def run_local_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def run_remote_pixel_cmd(remote_cmd):
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        "-p", PIXEL_SSH_PORT,
        PIXEL_IP,
        remote_cmd
    ]
    res = subprocess.run(ssh_cmd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()

class TestPixelTailscaleE2E:
    def test_tc_px1_tailscale_ping(self):
        code, stdout, _ = run_local_cmd(f"ping -c 5 -W 2 {PIXEL_IP}")
        assert code == 0, f"Ping to Pixel ({PIXEL_IP}) failed"
        assert "0.0% packet loss" in stdout or "0% packet loss" in stdout

    def test_tc_px2_termux_ssh_environment(self):
        code, stdout, stderr = run_remote_pixel_cmd("uname -m && uname -s")
        assert code == 0, f"SSH to Pixel failed: {stderr}"
        assert "aarch64" in stdout
        assert "Linux" in stdout

    def test_tc_px3_remote_health_probe(self):
        remote_curl = f"curl --retry 3 --retry-connrefused -s http://{HOST_IP}:{HOST_PORT}/health"
        code, stdout, stderr = run_remote_pixel_cmd(remote_curl)
        assert code == 0, f"Remote curl failed: {stderr}"
        body_json = json.loads(stdout)
        assert body_json["status"] == "HEALTHY"
        assert body_json["service"] == "lauburu_port4000_core"
        assert body_json["port"] == 4000

    def test_tc_px4_remote_zero_mock_snapshot(self):
        remote_curl = f"curl --retry 3 --retry-connrefused -s http://{HOST_IP}:{HOST_PORT}/api/biometrics/snapshot"
        code, stdout, stderr = run_remote_pixel_cmd(remote_curl)
        assert code == 0, f"Remote snapshot curl failed: {stderr}"
        snap = json.loads(stdout)
        assert "device_id" in snap
        assert snap["sample_rate_hz"] == 512.0
        if not snap["connected"]:
            assert snap["heart_rate_bpm"] == 0.0
            assert snap["zone2_status"] == "Resting / Disconnected"

    def test_tc_px5_remote_sample_ingestion(self):
        payload = json.dumps({
            "sample": 0.88,
            "heart_rate": 155.0,
            "rr_intervals": [387.0, 386.8],
            "device_id": "Pixel-Tailscale-M3-GATT"
        })
        b64_payload = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        remote_post = (
            f"echo '{b64_payload}' | base64 -d | "
            f"curl --retry 3 --retry-connrefused -s -X POST -H 'Content-Type: application/json' --data-binary @- "
            f"http://{HOST_IP}:{HOST_PORT}/api/biometrics/sample"
        )
        code, stdout, stderr = run_remote_pixel_cmd(remote_post)
        assert code == 0, f"Remote sample POST failed: {stderr}"
        res = json.loads(stdout)
        assert res["heart_rate_bpm"] == 155.0

    def test_tc_px6_remote_ui_html_audit(self):
        remote_curl = f"curl --retry 3 --retry-connrefused -s http://{HOST_IP}:{HOST_PORT}/ui"
        code, stdout, stderr = run_remote_pixel_cmd(remote_curl)
        assert code == 0, f"Remote UI curl failed: {stderr}"
        assert "LAUBURU" in stdout
        assert "connectPixelBluetooth()" in stdout
        assert "0% MOCK DATA" in stdout
        assert len(stdout) > 15000

    def test_tc_px7_remote_burst_load(self):
        remote_script = (
            f"for i in $(seq 1 10); do "
            f"  curl --retry 3 --retry-connrefused -s -o /dev/null -w '%{{http_code}}\\n' http://{HOST_IP}:{HOST_PORT}/health; "
            f"done"
        )
        code, stdout, stderr = run_remote_pixel_cmd(remote_script)
        assert code == 0, f"Remote burst test failed: {stderr}"
        codes = stdout.strip().split()
        assert len(codes) == 10
        assert all(c == "200" for c in codes)

if __name__ == "__main__":
    code = pytest.main(["-v", __file__])
    sys.exit(code)
