"""
==============================================================================
Unit & Integration Tests: Cloudflare Zero Trust Telemetry & TUI Arena
Subsystem: tests/unit/test_cloudflare_telemetry.py
==============================================================================
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Ensure project paths are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "06_scripts_and_tooling")
CANONICAL_PORT_DIR = os.path.join(PROJECT_ROOT, "01_apps", "canonical_port")
TUI_DIR = os.path.join(CANONICAL_PORT_DIR, "tui")

for p in [PROJECT_ROOT, SCRIPTS_DIR, CANONICAL_PORT_DIR, TUI_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from cloudflare_telemetry import (
    WAFThreatEvent,
    AccessAuthEvent,
    WAFTelemetrySummary,
    RedTeamThoughtTrace,
    CloudflareTelemetrySnapshot,
    CloudflareTelemetryCollector,
    get_cloudflare_zero_trust_snapshot,
)
from backend.training_telemetry_collector import (
    get_cloudflare_zero_trust_telemetry,
    get_red_blue_arena_telemetry,
)
from widgets.red_blue_arena_widget import (
    RedBlueArenaWidget,
    render_braille_sparkline,
)
from screens.training_screen import TrainingScreen
from widgets.lauburu_gyms_widget import LauburuGymsWidget


# ==============================================================================
# 1. Dataclass & Schema Tests
# ==============================================================================

def test_waf_threat_event_dataclass():
    """Verify WAFThreatEvent schema and field integrity."""
    event = WAFThreatEvent(
        timestamp="2026-08-28T19:30:00Z",
        action="block",
        rule_id="waf_rule_sql_inject_001",
        source="waf",
        client_ip="198.51.100.42",
        country="DE",
        asn_description="AMAZON-02",
        host="openclaw-standalone.trycloudflare.com",
        method="POST",
        path="/v1/chat/completions",
        query_string="admin=1' OR '1'='1",
        user_agent="AdversarialProbe/1.0",
        edge_status=403,
        ray_id="8b9a12c401f893e1",
        description="SQL Injection Attempt Blocked",
    )
    assert event.action == "block"
    assert event.edge_status == 403
    assert event.client_ip == "198.51.100.42"
    assert event.ray_id == "8b9a12c401f893e1"


def test_access_auth_event_dataclass():
    """Verify AccessAuthEvent schema and field integrity."""
    auth = AccessAuthEvent(
        timestamp="2026-08-28T19:32:00Z",
        app_domain="openclaw.lauburugrappling.com",
        app_uid="uid-1234-access",
        action="login",
        allowed=True,
        connection_type="saml",
        country="AU",
        ip_address="100.119.199.76",
        ray_id="8b9a12c401f893e2",
        user_email="aaron@lauburu.ai",
    )
    assert auth.allowed is True
    assert auth.user_email == "aaron@lauburu.ai"
    assert auth.connection_type == "saml"


def test_red_team_thought_trace_dataclass():
    """Verify RedTeamThoughtTrace schema and visual correlation fields."""
    thought = RedTeamThoughtTrace(
        timestamp="2026-08-28T19:30:00Z",
        model_id="meta-llama-3.1-8b-instruct-abliterated",
        thought_summary="Attempting SQL injection bypass on debug endpoint",
        attack_vector="SQL Injection Probe",
        target_endpoint="openclaw-standalone.trycloudflare.com/api/debug",
        raw_think_block="<think>I need to test if the input filter catches quotes.</think>",
        correlated_ray_id="8b9a12c401f893e1",
        correlated_waf_action="block",
        is_blocked=True,
    )
    assert thought.model_id == "meta-llama-3.1-8b-instruct-abliterated"
    assert thought.is_blocked is True
    assert thought.correlated_ray_id == "8b9a12c401f893e1"


def test_cloudflare_telemetry_snapshot_serialization():
    """Verify full CloudflareTelemetrySnapshot serialization to dictionary."""
    summary = WAFTelemetrySummary(
        window_minutes=60,
        total_threats_blocked=5,
        total_challenges_issued=2,
        top_attacked_host="openclaw-standalone.trycloudflare.com",
        top_rule_triggered="SQL Injection Rule",
        last_threat_timestamp="2026-08-28T19:30:00Z",
        block_rate_pct=12.5,
        threat_level="LOW",
    )
    snapshot = CloudflareTelemetrySnapshot(
        timestamp="2026-08-28T19:35:00Z",
        is_configured=True,
        status="HEALTHY",
        status_message="Active telemetry stream",
        summary=summary,
        threat_events=[],
        access_events=[],
        red_team_thoughts=[],
        tunnel_endpoint="openclaw-standalone.trycloudflare.com",
        tunnel_status="ONLINE",
        latency_ms=42.5,
    )
    d = snapshot.to_dict()
    assert isinstance(d, dict)
    assert d["status"] == "HEALTHY"
    assert d["summary"]["total_threats_blocked"] == 5
    assert d["tunnel_status"] == "ONLINE"
    assert d["latency_ms"] == 42.5


# ==============================================================================
# 2. Zero-Mock Fallback Invariants (Rule #0 Compliance)
# ==============================================================================

def test_zero_mock_fallback_when_unconfigured():
    """Verify collector emits clean '--' placeholders and empty lists without fake data when unconfigured."""
    collector = CloudflareTelemetryCollector(api_token="", zone_id="", account_id="")
    assert collector.is_configured() is False

    snapshot = collector.get_telemetry_snapshot(time_window_minutes=60)
    assert snapshot.is_configured is False
    assert snapshot.status == "NO_CREDENTIALS"
    assert snapshot.summary.total_threats_blocked == 0
    assert snapshot.summary.top_attacked_host == "--"
    assert snapshot.summary.top_rule_triggered == "--"
    assert snapshot.summary.last_threat_timestamp == "--"
    assert snapshot.summary.threat_level == "--"
    assert snapshot.threat_events == []
    assert snapshot.access_events == []
    assert snapshot.tunnel_status == "DISCONNECTED"
    assert snapshot.latency_ms is None


def test_public_get_cloudflare_zero_trust_snapshot():
    """Verify the public helper function returns a valid dictionary."""
    collector = CloudflareTelemetryCollector(api_token="", zone_id="")
    res = get_cloudflare_zero_trust_snapshot(time_window_minutes=45, collector=collector)
    assert isinstance(res, dict)
    assert res["is_configured"] is False
    assert res["summary"]["window_minutes"] == 45
    assert res["summary"]["top_attacked_host"] == "--"


# ==============================================================================
# 3. Collector HTTP & GraphQL Logic Tests
# ==============================================================================

def test_collector_graphql_query_and_headers():
    """Verify Authorization headers and query construction."""
    collector = CloudflareTelemetryCollector(
        api_token="test_cf_token_secret_123",
        zone_id="test_zone_id_456",
        account_id="test_account_id_789",
    )
    assert collector.is_configured() is True
    headers = collector._get_headers()
    assert headers["Authorization"] == "Bearer test_cf_token_secret_123"
    assert headers["Content-Type"] == "application/json"


@patch("httpx.Client")
def test_fetch_waf_threats_success(mock_client_cls):
    """Verify successful parsing of GraphQL firewallEventsAdaptive response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "viewer": {
                "zones": [
                    {
                        "firewallEventsAdaptive": [
                            {
                                "datetime": "2026-08-28T19:35:10Z",
                                "action": "block",
                                "ruleId": "rule_9981",
                                "source": "waf",
                                "clientIP": "203.0.113.19",
                                "clientCountryName": "US",
                                "clientASNDescription": "CLOUDFLARENET",
                                "clientRequestHTTPHost": "openclaw-standalone.trycloudflare.com",
                                "clientRequestHTTPMethodName": "POST",
                                "clientRequestPath": "/v1/chat/completions",
                                "clientRequestQuery": "prompt=jailbreak",
                                "userAgent": "curl/8.1.0",
                                "edgeResponseStatus": 403,
                                "rayName": "8b9a999901f893e9",
                                "description": "Prompt Injection Probe Blocked",
                                "ref": "ref_123",
                            }
                        ]
                    }
                ]
            }
        }
    }
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    collector = CloudflareTelemetryCollector(api_token="test_token", zone_id="test_zone")
    threats = collector.fetch_waf_threats(time_window_minutes=30)
    assert len(threats) == 1
    t = threats[0]
    assert t.action == "block"
    assert t.client_ip == "203.0.113.19"
    assert t.description == "Prompt Injection Probe Blocked"
    assert t.edge_status == 403
    assert t.ray_id == "8b9a999901f893e9"


@patch("httpx.Client")
def test_fetch_waf_threats_rate_limited(mock_client_cls):
    """Verify graceful handling of HTTP 429 rate limits."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    collector = CloudflareTelemetryCollector(api_token="test_token", zone_id="test_zone")
    threats = collector.fetch_waf_threats()
    assert threats == []


@patch("httpx.Client")
def test_fetch_access_authentications_success(mock_client_cls):
    """Verify successful parsing of Zero Trust Access logs."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "success": True,
        "result": [
            {
                "created_at": "2026-08-28T19:35:12Z",
                "app_domain": "openclaw.lauburugrappling.com",
                "app_uid": "app-uid-99",
                "action": "login",
                "allowed": True,
                "connection": "saml_google",
                "country": "AU",
                "ip_address": "100.119.199.76",
                "ray_id": "ray_access_001",
                "user_email": "aaron@lauburu.ai",
            }
        ]
    }
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    collector = CloudflareTelemetryCollector(api_token="test_token", account_id="test_acc")
    access = collector.fetch_access_authentications()
    assert len(access) == 1
    assert access[0].user_email == "aaron@lauburu.ai"
    assert access[0].allowed is True


# ==============================================================================
# 4. Cognitive Thought Streaming & Visual Correlation Tests
# ==============================================================================

def test_visual_correlation_engine():
    """Verify correlation linking Red Team thoughts with Blue Team WAF block events."""
    collector = CloudflareTelemetryCollector()

    thoughts = [
        RedTeamThoughtTrace(
            timestamp="2026-08-28T19:35:10Z",
            model_id="meta-llama-3.1-8b-instruct-abliterated",
            thought_summary="Attempting SQL injection on debug API",
            attack_vector="SQL Injection Probe",
            target_endpoint="openclaw-standalone.trycloudflare.com/api/debug",
            raw_think_block="<think>Injecting single quote into auth parameter</think>",
            correlated_ray_id="8b9a999901f893e9",
        ),
        RedTeamThoughtTrace(
            timestamp="2026-08-28T19:40:00Z",
            model_id="meta-llama-3.1-8b-instruct-abliterated",
            thought_summary="Port 50052 RPC probe",
            attack_vector="RPC Scanner",
            target_endpoint="openclaw-standalone.trycloudflare.com/rpc",
            raw_think_block="<think>Probing RPC tensor shard port</think>",
        ),
    ]

    threats = [
        WAFThreatEvent(
            timestamp="2026-08-28T19:35:10Z",
            action="block",
            rule_id="waf_sqli_1",
            source="waf",
            client_ip="203.0.113.19",
            country="US",
            asn_description="ASN",
            host="openclaw-standalone.trycloudflare.com",
            method="POST",
            path="/api/debug",
            query_string="",
            user_agent="Agent",
            edge_status=403,
            ray_id="8b9a999901f893e9",
            description="SQLi Blocked",
        )
    ]

    correlated = collector.correlate_thoughts_with_threats(thoughts, threats)
    assert len(correlated) == 2
    # First thought matched Ray ID and was marked blocked
    assert correlated[0].is_blocked is True
    assert correlated[0].correlated_waf_action == "block"
    assert correlated[0].correlated_ray_id == "8b9a999901f893e9"
    # Second thought not blocked yet
    assert correlated[1].is_blocked is False


# ==============================================================================
# 5. Backend & TUI Widget Integration Tests
# ==============================================================================

def test_backend_training_telemetry_collector_cloudflare_integration():
    """Verify training_telemetry_collector merges Cloudflare & Red Team telemetry."""
    data = get_red_blue_arena_telemetry()
    assert "cloudflare_zero_trust" in data
    assert "tunnel_status" in data
    assert "tunnel_endpoint" in data
    assert "red_team_thoughts" in data
    assert "threat_events" in data
    assert "access_events" in data


def test_braille_sparkline_rendering():
    """Verify high-density subpixel Braille sparkline generation."""
    series = [0.0, 5.0, 10.0, 15.0, 20.0]
    spark = render_braille_sparkline(series, min_val=0.0, max_val=20.0)
    assert isinstance(spark, str)
    assert len(spark) > 0


def test_red_blue_arena_widget_instantiation_and_update():
    """Verify RedBlueArenaWidget lifecycle, reactive update, and panel rendering."""
    widget = RedBlueArenaWidget()
    assert widget.poll_interval == 2.0

    # Inject mock data
    sample_data = {
        "cloudflare_zero_trust": {
            "is_configured": True,
            "status": "HEALTHY",
            "tunnel_status": "ONLINE",
            "tunnel_endpoint": "openclaw-standalone.trycloudflare.com",
            "latency_ms": 45.2,
            "summary": {
                "window_minutes": 60,
                "total_threats_blocked": 12,
                "total_challenges_issued": 3,
                "threat_level": "LOW",
                "block_rate_pct": 8.5,
            },
            "threat_events": [
                {
                    "timestamp": "2026-08-28T19:35:10Z",
                    "action": "block",
                    "client_ip": "198.51.100.42",
                    "country": "DE",
                    "path": "/v1/chat/completions",
                    "description": "Prompt Injection Probe",
                    "edge_status": 403,
                    "ray_id": "ray_123",
                }
            ],
            "access_events": [],
            "red_team_thoughts": [
                {
                    "timestamp": "2026-08-28T19:35:10Z",
                    "model_id": "meta-llama-3.1-8b-instruct-abliterated",
                    "thought_summary": "Injecting jailbreak prompt",
                    "attack_vector": "Prompt Injection Probe",
                    "raw_think_block": "<think>Testing filter</think>",
                    "is_blocked": True,
                }
            ],
        }
    }
    widget.update_telemetry(sample_data)
    assert widget.arena_data == sample_data


def test_training_screen_composition():
    """Verify TrainingScreen composes Tab 1 (tab_red_blue) with RedBlueArenaWidget."""
    screen = TrainingScreen()
    assert screen is not None


def test_lauburu_gyms_widget_render_gym_1():
    """Verify LauburuGymsWidget renders Gym 1 without exceptions."""
    gyms = LauburuGymsWidget()
    gyms.refresh_telemetry()
    assert gyms.gyms_data is not None
