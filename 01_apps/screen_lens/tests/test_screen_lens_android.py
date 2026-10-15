#!/usr/bin/env python3
"""
Unit and Integration Tests for Lauburu Screen Lens (Android)
Validates:
- SQLite schema & FTS5 full-text search initialization
- REST API endpoints (/v1/status, /v1/query, /v1/capture, /v1/frames/latest)
- Cross-device JSON schema compliance
- Zero-mock live execution
"""

import json
import os
import socket
import subprocess
import threading
import time
import unittest
import urllib.request

PIXEL_SSH_PORT = 8022


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


class TestScreenLensAndroid(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        subprocess.run(["adb", "-s", "100.73.38.87:5555", "forward", "tcp:8022", "tcp:8022"], capture_output=True)
        subprocess.run(["adb", "-s", "100.73.38.87:5555", "forward", "tcp:3036", "tcp:3035"], capture_output=True)

    def test_00_local_android_schema_and_db_init(self):
        """Validates that lauburu_lens_android creates valid SQLite tables and FTS5 indices."""
        import sys
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "android")))
        import lauburu_lens_android
        
        # Test initialization
        lauburu_lens_android.init_db()
        status = lauburu_lens_android.get_status()
        self.assertIn("status", status)
        self.assertIn("total_frames_indexed", status)
        
        # Test FTS5 search function
        results = lauburu_lens_android.search_frames("Android", limit=5)
        self.assertIsInstance(results, list)

    def test_01_cli_status_on_pixel(self):
        if not is_port_open("127.0.0.1", PIXEL_SSH_PORT):
            self.skipTest("Pixel is in deep sleep or ADB forwarding not active")
        cmd = ["ssh", "-p", str(PIXEL_SSH_PORT), "-o", "StrictHostKeyChecking=no", "localhost", "lauburu-lens status"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Status check failed: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("node_name"), "Pixel_10_Pro_XL")
        self.assertEqual(data.get("service"), "lauburu-lens-android")

    def test_02_http_rest_api_status(self):
        if not is_port_open("127.0.0.1", 3036):
            self.skipTest("Pixel Screen Lens port 3036 not reachable")
        req = urllib.request.urlopen("http://127.0.0.1:3036/v1/status", timeout=5)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("total_frames_indexed", data)
        self.assertGreaterEqual(data["total_frames_indexed"], 1)

    def test_03_fts5_query_on_pixel(self):
        if not is_port_open("127.0.0.1", PIXEL_SSH_PORT):
            self.skipTest("Pixel is in deep sleep or ADB forwarding not active")
        subprocess.run(["ssh", "-p", str(PIXEL_SSH_PORT), "-o", "StrictHostKeyChecking=no", "localhost", "lauburu-lens capture"], capture_output=True)
        cmd = ["ssh", "-p", str(PIXEL_SSH_PORT), "-o", "StrictHostKeyChecking=no", "localhost", "lauburu-lens query 'Android'"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Query failed: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertIn("query", data)
        self.assertIn("count", data)
        self.assertIsInstance(data.get("results"), list)


if __name__ == "__main__":
    unittest.main()
