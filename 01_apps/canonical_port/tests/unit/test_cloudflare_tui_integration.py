"""
==============================================================================
Canonical Port Unit & Integration Tests: Cloudflare Zero Trust & TUI Integration
Subsystem: 01_apps/canonical_port/tests/unit/test_cloudflare_tui_integration.py
==============================================================================
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Ensure project paths are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
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
        )
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
    assert len(correlated) == 1
    assert correlated[0].is_blocked is True
    assert correlated[0].correlated_waf_action == "block"
    assert correlated[0].correlated_ray_id == "8b9a999901f893e9"


def test_backend_training_telemetry_collector_cloudflare_integration():
    """Verify training_telemetry_collector merges Cloudflare & Red Team telemetry."""
    data = get_red_blue_arena_telemetry()
    assert "cloudflare_zero_trust" in data
    assert "tunnel_status" in data
    assert "tunnel_endpoint" in data
    assert "red_team_thoughts" in data
    assert "threat_events" in data
    assert "access_events" in data


def test_red_blue_arena_widget_instantiation():
    """Verify RedBlueArenaWidget lifecycle and reactive update."""
    widget = RedBlueArenaWidget()
    assert widget.poll_interval == 2.0
    widget.refresh_telemetry()
    assert widget.arena_data is not None
