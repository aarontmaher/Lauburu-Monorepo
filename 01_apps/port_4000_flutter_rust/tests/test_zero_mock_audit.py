#!/usr/bin/env python3
"""
Lauburu Port 4000 Console: Automated Zero-Mock Truth Audit Suite.
Forensic scanner detecting static and dynamic violations of Global Rule #0.
"""

import os
import re
import json
import sys
import urllib.request
import urllib.error
import pytest

REPO_ROOT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust"
HTML_PATH = os.path.join(REPO_ROOT, "flutter_ui/build/index.html")
RUST_SRC = os.path.join(REPO_ROOT, "rust_backend/src")
DART_SRC = os.path.join(REPO_ROOT, "flutter_ui/lib")

class TestZeroMockTruthAudit:
    def test_tc_zm1_compiled_html_audit(self):
        assert os.path.isfile(HTML_PATH), f"Compiled index.html not found at {HTML_PATH}"
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Check banned tokens
        assert "72.0" not in content, "Found banned token '72.0' in index.html"
        assert "48.5" not in content, "Found banned token '48.5' in index.html"
        assert "readiness = 50.0" not in content, "Found banned 'readiness = 50.0' in index.html"
        assert "alpha1 = 1.0;" not in content, "Found banned 'alpha1 = 1.0;' in index.html"
        assert "Closed Guard → Ashi Garami" not in content, "Found banned mock technique in index.html"

        # Check required zero-mock waiting tokens
        assert 'id="val-hr"' in content and '--' in content
        assert 'id="val-rmssd"' in content and '--' in content
        assert 'id="val-alpha1"' in content and '--' in content
        assert 'id="val-readiness"' in content and '--' in content
        assert "0% MOCK DATA" in content

    def test_tc_zm2_rust_source_audit(self):
        bio_mod_path = os.path.join(RUST_SRC, "biometrics/mod.rs")
        assert os.path.isfile(bio_mod_path), f"File not found: {bio_mod_path}"
        with open(bio_mod_path, "r", encoding="utf-8") as f:
            bio_code = f.read()
            assert "heart_rate_bpm: 0.0" in bio_code
            assert "hrv_rmssd_ms: 0.0" in bio_code
            assert "dfa_alpha1: 0.0" in bio_code
            assert "readiness_score: 0.0" in bio_code
            assert "connected: false" in bio_code

        spatial_path = os.path.join(RUST_SRC, "spatial.rs")
        assert os.path.isfile(spatial_path), f"File not found: {spatial_path}"
        with open(spatial_path, "r", encoding="utf-8") as f:
            spatial_code = f.read()
            assert '"Standby / Mat Empty"' in spatial_code
            assert '"No Athlete Detected"' in spatial_code

    def test_tc_zm3_dart_source_audit(self):
        models_path = os.path.join(DART_SRC, "src/models/biometrics_model.dart")
        assert os.path.isfile(models_path), f"File not found: {models_path}"
        with open(models_path, "r", encoding="utf-8") as f:
            dart_code = f.read()
            assert "heartRateBpm: 0.0" in dart_code
            assert "hrvRmssdMs: 0.0" in dart_code
            assert "dfaAlpha1: 0.0" in dart_code
            assert "readinessScore: 0.0" in dart_code
            assert "connected: false" in dart_code

    def test_tc_zm4_live_endpoint_zero_mock_contract(self):
        try:
            req = urllib.request.Request("http://127.0.0.1:4000/api/biometrics/snapshot")
            with urllib.request.urlopen(req, timeout=3) as resp:
                snap = json.loads(resp.read().decode("utf-8"))
                if not snap["connected"]:
                    assert snap["heart_rate_bpm"] == 0.0
                    assert snap["hrv_rmssd_ms"] == 0.0
                    assert snap["dfa_alpha1"] == 0.0
                    assert snap["readiness_score"] == 0.0
                    assert snap["zone2_status"] == "Resting / Disconnected"
                else:
                    assert snap["heart_rate_bpm"] > 0.0
        except urllib.error.URLError:
            pytest.skip("Port 4000 server not running on 127.0.0.1:4000")

if __name__ == "__main__":
    code = pytest.main(["-v", __file__])
    sys.exit(code)
