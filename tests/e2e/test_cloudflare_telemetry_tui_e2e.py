"""
==============================================================================
E2E Integration & Stress Tests: Cloudflare Zero Trust & Red/Blue Arena
Subsystem: tests/e2e/test_cloudflare_telemetry_tui_e2e.py
==============================================================================
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# Ensure project paths are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "06_scripts_and_tooling")
CANONICAL_PORT_DIR = os.path.join(PROJECT_ROOT, "01_apps", "canonical_port")
TUI_DIR = os.path.join(CANONICAL_PORT_DIR, "tui")

for p in [PROJECT_ROOT, SCRIPTS_DIR, CANONICAL_PORT_DIR, TUI_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from cloudflare_telemetry import (
    CloudflareTelemetryCollector,
    WAFThreatEvent,
    AccessAuthEvent,
    RedTeamThoughtTrace,
)
from widgets.red_blue_arena_widget import RedBlueArenaWidget
from screens.training_screen import TrainingScreen
from backend.training_telemetry_collector import (
    get_red_blue_arena_telemetry,
    get_all_gyms_telemetry,
)


@pytest.mark.asyncio
async def test_cloudflare_telemetry_end_to_end_pipeline():
    """
    End-to-end verification of Cloudflare Zero Trust ingestion pipeline:
    1. Query collector with simulated live threat + access responses.
    2. Ingest into backend training_telemetry_collector.
    3. Update RedBlueArenaWidget state and verify reactive data model.
    """
    mock_threat_resp = {
        "data": {
            "viewer": {
                "zones": [
                    {
                        "firewallEventsAdaptive": [
                            {
                                "datetime": "2026-08-28T19:45:00Z",
                                "action": "block",
                                "ruleId": "waf_block_sqli",
                                "source": "waf",
                                "clientIP": "198.51.100.42",
                                "clientCountryName": "DE",
                                "clientASNDescription": "HETZNER",
                                "clientRequestHTTPHost": "openclaw-standalone.trycloudflare.com",
                                "clientRequestHTTPMethodName": "POST",
                                "clientRequestPath": "/v1/chat/completions",
                                "clientRequestQuery": "",
                                "userAgent": "AdversarialBot/2.0",
                                "edgeResponseStatus": 403,
                                "rayName": "8b9a111122223333",
                                "description": "SQL Injection Pattern Detected",
                                "ref": "",
                            }
                        ]
                    }
                ]
            }
        }
    }

    mock_access_resp = {
        "success": True,
        "result": [
            {
                "created_at": "2026-08-28T19:44:30Z",
                "app_domain": "openclaw.lauburugrappling.com",
                "app_uid": "app-uid-1",
                "action": "login",
                "allowed": True,
                "connection": "google",
                "country": "AU",
                "ip_address": "100.119.199.76",
                "ray_id": "8b9a444455556666",
                "user_email": "aaron@lauburugrappling.com",
            }
        ]
    }

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        
        def mock_post(*args, **kwargs):
            r = MagicMock()
            r.status_code = 200
            r.json.return_value = mock_threat_resp
            return r

        def mock_get(*args, **kwargs):
            r = MagicMock()
            r.status_code = 200
            r.json.return_value = mock_access_resp
            return r

        mock_client.post.side_effect = mock_post
        mock_client.get.side_effect = mock_get
        mock_client_cls.return_value = mock_client

        collector = CloudflareTelemetryCollector(
            api_token="test_valid_token",
            zone_id="test_zone_id",
            account_id="test_account_id",
        )
        snapshot = collector.get_telemetry_snapshot(time_window_minutes=60)

        assert snapshot.is_configured is True
        assert snapshot.status == "HEALTHY"
        assert len(snapshot.threat_events) == 1
        assert len(snapshot.access_events) == 1
        assert snapshot.summary.total_threats_blocked == 1
        assert snapshot.summary.top_attacked_host == "openclaw-standalone.trycloudflare.com"

        # Verify RedBlueArenaWidget ingests the snapshot cleanly
        widget = RedBlueArenaWidget()
        widget.update_telemetry({"cloudflare_zero_trust": snapshot.to_dict()})
        assert widget.arena_data["cloudflare_zero_trust"]["summary"]["total_threats_blocked"] == 1


def test_red_blue_arena_cognitive_correlation_stress():
    """
    Stress test visual correlation across 50 simulated thought traces and WAF events.
    Verifies zero-crash matching performance and accurate Ray ID attribution.
    """
    collector = CloudflareTelemetryCollector()

    thoughts = [
        RedTeamThoughtTrace(
            timestamp=f"2026-08-28T19:{i:02d}:00Z",
            model_id="meta-llama-3.1-8b-instruct-abliterated",
            thought_summary=f"Attack vector #{i} probe",
            attack_vector=f"Vector-{i}",
            target_endpoint="openclaw-standalone.trycloudflare.com",
            correlated_ray_id=f"ray_{i:04d}" if i % 2 == 0 else None,
        )
        for i in range(50)
    ]

    threats = [
        WAFThreatEvent(
            timestamp=f"2026-08-28T19:{i:02d}:02Z",
            action="block",
            rule_id=f"rule_{i}",
            source="waf",
            client_ip="198.51.100.42",
            country="DE",
            asn_description="ASN",
            host="openclaw-standalone.trycloudflare.com",
            method="POST",
            path="/api",
            query_string="",
            user_agent="Agent",
            edge_status=403,
            ray_id=f"ray_{i:04d}",
            description=f"Blocked attack #{i}",
        )
        for i in range(50)
    ]

    correlated = collector.correlate_thoughts_with_threats(thoughts, threats)
    assert len(correlated) == 50
    # Every even-indexed thought had an exact matching ray_id
    for i, c in enumerate(correlated):
        if i % 2 == 0:
            assert c.is_blocked is True
            assert c.correlated_waf_action == "block"
            assert c.correlated_ray_id == f"ray_{i:04d}"


def test_all_gyms_telemetry_aggregation():
    """Verify get_all_gyms_telemetry aggregates all 5 gyms without blocking."""
    gyms = get_all_gyms_telemetry()
    assert "red_blue_arena" in gyms
    assert "mesh_healing" in gyms
    assert "stealth_compute" in gyms
    assert "software_dev_game" in gyms
    assert "spatial_grappling" in gyms
    assert "cloudflare_zero_trust" in gyms["red_blue_arena"]
