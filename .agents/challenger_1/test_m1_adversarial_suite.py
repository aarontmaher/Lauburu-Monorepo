#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Lauburu Mesh Ecosystem — Milestone 1 Adversarial Challenge & Stress Test Suite
Challenger: Challenger 1 (Empirical Challenger)
Target Subsystems:
  - 06_scripts_and_tooling/cloudflare_telemetry.py
  - 01_apps/canonical_port/tui/widgets/red_blue_arena_widget.py
  - 01_apps/canonical_port/backend/training_telemetry_collector.py
==============================================================================
"""

import os
import sys
import math
import json
import time
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

# Ensure project paths are in sys.path
PROJECT_ROOT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
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
    render_cli_dashboard,
)
from widgets.red_blue_arena_widget import (
    RedBlueArenaWidget,
    render_braille_sparkline,
)
from backend.training_telemetry_collector import (
    get_cloudflare_zero_trust_telemetry,
    get_red_blue_arena_telemetry,
)
from textual.app import App, ComposeResult
from rich.console import Console


# ==============================================================================
# Focus Area 1: Malformed GraphQL Error Payloads & Unexpected JSON Types
# ==============================================================================

class TestMalformedPayloads:
    """Stress-test resilience against broken, corrupted, or atypical GraphQL responses."""

    def test_graphql_explicit_errors_field(self):
        """Verify handling when GraphQL returns 200 with an 'errors' array."""
        collector = CloudflareTelemetryCollector(api_token="valid_token", zone_id="valid_zone")
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "errors": [
                    {"message": "Syntax Error: Unexpected Name 'invalid_field'", "path": ["query"]}
                ],
                "data": None
            }
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            threats = collector.fetch_waf_threats()
            assert threats == [], "Collector must return empty list on GraphQL errors payload"

    def test_graphql_null_data_hierarchy(self):
        """Verify handling when nested levels of GraphQL response are None/missing."""
        test_payloads = [
            {"data": None},
            {"data": {}},
            {"data": {"viewer": None}},
            {"data": {"viewer": {}}},
            {"data": {"viewer": {"zones": None}}},
            {"data": {"viewer": {"zones": []}}},
            {"data": {"viewer": {"zones": [{}]}}},
            {"data": {"viewer": {"zones": [{"firewallEventsAdaptive": None}]}}},
            {"data": {"viewer": {"zones": [{"firewallEventsAdaptive": []}]}}},
        ]

        collector = CloudflareTelemetryCollector(api_token="valid_token", zone_id="valid_zone")
        for payload in test_payloads:
            with patch("httpx.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__enter__.return_value = mock_client
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = payload
                mock_client.post.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                threats = collector.fetch_waf_threats()
                assert threats == [], f"Failed to handle null hierarchy: {payload}"

    def test_reproduce_bug_1_none_action_crashes_snapshot(self):
        """
        [BUG REPRODUCTION 1]
        Verify that an event with action=None does NOT crash get_telemetry_snapshot() with:
        TypeError: argument of type 'NoneType' is not iterable (line 579).
        """
        collector = CloudflareTelemetryCollector(api_token="valid_tok", zone_id="valid_zone")
        null_action_threat = WAFThreatEvent(
            timestamp="2026-08-28T19:00:00Z",
            action=None,  # Explicit None
            rule_id="rule_1",
            source="waf",
            client_ip="198.51.100.1",
            country="US",
            asn_description="ASN",
            host="openclaw-standalone.trycloudflare.com",
            method="POST",
            path="/api",
            query_string="",
            user_agent="Agent",
            edge_status=403,
            ray_id="ray_123",
            description="Null action probe",
        )

        with patch.object(collector, "fetch_waf_threats", return_value=[null_action_threat]), \
             patch.object(collector, "fetch_access_authentications", return_value=[]), \
             patch.object(collector, "fetch_red_team_thoughts", return_value=[]):
            
            # This must NOT raise TypeError
            snapshot = collector.get_telemetry_snapshot()
            assert snapshot.summary.total_threats_blocked == 0
            assert snapshot.summary.total_challenges_issued == 0

    def test_access_audit_logs_malformed_results(self):
        """Verify Zero Trust Access audit log endpoint resilience against broken payloads."""
        collector = CloudflareTelemetryCollector(api_token="valid_token", account_id="valid_acc")
        bad_access_payloads = [
            {"success": False, "errors": [{"code": 1001, "message": "Account forbidden"}]},
            {"result": None},
            {"result": [{}]},
            {"result": [{"created_at": None, "allowed": None, "user_email": None}]},
            [],
            "Non-JSON string",
        ]

        for payload in bad_access_payloads:
            with patch("httpx.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__enter__.return_value = mock_client
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                if isinstance(payload, str):
                    mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
                else:
                    mock_resp.json.return_value = payload
                mock_client.get.return_value = mock_resp
                mock_client_cls.return_value = mock_client

                logs = collector.fetch_access_authentications()
                assert isinstance(logs, list), "Must return list without unhandled exceptions"


# ==============================================================================
# Focus Area 2: Network Error Handling & HTTP Status Edge Cases
# ==============================================================================

class TestNetworkErrorHandling:
    """Stress-test network layer failure modes: timeouts, connection errors, HTTP codes."""

    @pytest.mark.parametrize("status_code", [401, 403, 404, 429, 500, 502, 503, 504])
    def test_waf_threats_http_error_statuses(self, status_code):
        """Verify all non-200 HTTP statuses return empty list cleanly without throwing."""
        collector = CloudflareTelemetryCollector(api_token="valid_token", zone_id="valid_zone")
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = status_code
            mock_resp.raise_for_status.side_effect = Exception(f"HTTP {status_code} Error")
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            threats = collector.fetch_waf_threats()
            assert threats == []

    @pytest.mark.parametrize("status_code", [401, 403, 404, 429, 500, 502, 503])
    def test_access_logs_http_error_statuses(self, status_code):
        """Verify Access audit logs HTTP error handling across all status codes."""
        collector = CloudflareTelemetryCollector(api_token="valid_token", account_id="valid_acc")
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = status_code
            mock_resp.raise_for_status.side_effect = Exception(f"HTTP {status_code} Error")
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            logs = collector.fetch_access_authentications()
            assert logs == []

    def test_network_connection_timeouts(self):
        """Verify handling of connection timeouts and DNS resolution failures."""
        collector = CloudflareTelemetryCollector(api_token="valid_token", zone_id="valid_zone")
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.post.side_effect = Exception("ConnectTimeout: connection timed out after 3.0s")
            mock_client.get.side_effect = Exception("ConnectError: DNS lookup failed for api.cloudflare.com")
            mock_client_cls.return_value = mock_client

            assert collector.fetch_waf_threats() == []
            assert collector.fetch_access_authentications() == []


# ==============================================================================
# Focus Area 3: High-Throughput Burst Stress & Memory Stability
# ==============================================================================

class TestHighThroughputAndMemory:
    """Stress-test high volume event streams (500+ events), ring buffers, and sparklines."""

    def test_high_volume_threat_events_aggregation(self):
        """Verify summary metrics and breakdown calculations with 1,000 threat events."""
        collector = CloudflareTelemetryCollector(api_token="test_tok", zone_id="test_zone")

        # Generate 1,000 synthetic threat events
        actions = ["block", "managed_challenge", "js_challenge", "log"]
        countries = ["US", "DE", "CN", "RU", "AU", "NL", "BR", "IN"]
        vectors = ["SQL Injection", "Prompt Injection", "Rate Limit Exceeded", "RPC Scan", "Path Traversal"]

        large_threat_list = [
            WAFThreatEvent(
                timestamp=f"2026-08-28T19:{(i % 60):02d}:{(i % 60):02d}Z",
                action=actions[i % len(actions)],
                rule_id=f"rule_{i % 20}",
                source="waf",
                client_ip=f"198.51.100.{(i % 250)}",
                country=countries[i % len(countries)],
                asn_description=f"ASN-{i % 10}",
                host="openclaw-standalone.trycloudflare.com",
                method="POST",
                path=f"/v1/api/endpoint_{i % 5}",
                query_string=f"q={i}",
                user_agent="BurstTester/1.0",
                edge_status=403 if actions[i % len(actions)] == "block" else 200,
                ray_id=f"ray_burst_{i:06d}",
                description=vectors[i % len(vectors)],
            )
            for i in range(1000)
        ]

        with patch.object(collector, "fetch_waf_threats", return_value=large_threat_list), \
             patch.object(collector, "fetch_access_authentications", return_value=[]), \
             patch.object(collector, "fetch_red_team_thoughts", return_value=[]):
            
            t0 = time.time()
            snapshot = collector.get_telemetry_snapshot(time_window_minutes=60)
            duration = time.time() - t0

            assert duration < 0.1, f"Aggregation took too long ({duration:.4f}s) for 1,000 events"
            assert snapshot.summary.total_threats_blocked == 250
            assert snapshot.summary.total_challenges_issued == 500
            assert snapshot.summary.threat_level == "CRITICAL"
            assert len(snapshot.top_attack_vectors) <= 5
            assert len(snapshot.geo_distribution) <= 5
            assert snapshot.status == "HEALTHY"

    def test_braille_sparkline_edge_cases(self):
        """Stress-test Unicode Braille sparkline generation under extreme numerical inputs."""
        # 1. Empty list
        assert render_braille_sparkline([]) == "⠂"

        # 2. Single element
        s1 = render_braille_sparkline([50.0])
        assert isinstance(s1, str) and len(s1) > 0

        # 3. All identical values (zero span protection)
        s_ident = render_braille_sparkline([42.0] * 20)
        assert isinstance(s_ident, str)
        assert len(s_ident) > 0

        # 4. Large series (5,000 items)
        large_series = [math.sin(i / 10.0) * 50.0 + 50.0 for i in range(5000)]
        t0 = time.time()
        spark = render_braille_sparkline(large_series)
        duration = time.time() - t0
        assert duration < 0.05, f"Sparkline rendering took too long ({duration:.4f}s)"
        assert len(spark) == 2500

        # 5. Negative values and extreme dynamic ranges
        s_neg = render_braille_sparkline([-100.0, -50.0, 0.0, 50.0, 100.0])
        assert isinstance(s_neg, str)

        # 6. min_val > max_val inversion
        s_inv = render_braille_sparkline([10.0, 20.0, 30.0], min_val=100.0, max_val=0.0)
        assert isinstance(s_inv, str)

    def test_widget_ring_buffer_memory_stability(self):
        """Verify bounded deque behavior in RedBlueArenaWidget over 200 consecutive updates."""
        widget = RedBlueArenaWidget()
        assert widget._waf_history.maxlen == 30
        assert widget._access_history.maxlen == 30
        assert widget._token_velocity_history.maxlen == 30

        dummy_cf_data = {
            "cloudflare_zero_trust": {
                "is_configured": True,
                "status": "HEALTHY",
                "summary": {"window_minutes": 60},
                "threat_events": [{"action": "block"}] * 10,
                "access_events": [{"allowed": True}] * 5,
                "red_team_thoughts": [{"thought_summary": "test"}] * 3,
            }
        }

        for i in range(200):
            widget.update_telemetry(dummy_cf_data)
            if dummy_cf_data["cloudflare_zero_trust"]["threat_events"]:
                widget._waf_history.append(float(len(dummy_cf_data["cloudflare_zero_trust"]["threat_events"])))
            if dummy_cf_data["cloudflare_zero_trust"]["access_events"]:
                widget._access_history.append(float(len(dummy_cf_data["cloudflare_zero_trust"]["access_events"])))

        assert len(widget._waf_history) == 30, "WAF history deque must remain strictly capped at maxlen=30"
        assert len(widget._access_history) == 30, "Access history deque must remain strictly capped at maxlen=30"


# ==============================================================================
# Focus Area 4: Cognitive Thought Stream & Visual Correlation
# ==============================================================================

class TestCognitiveThoughtCorrelation:
    """Stress-test <think> block parsing, temporal matching, and Ray ID attribution."""

    def test_correlation_exact_ray_id_attribution(self):
        """Verify Ray ID match takes precedence over timestamps."""
        collector = CloudflareTelemetryCollector()

        thought = RedTeamThoughtTrace(
            timestamp="2026-08-28T19:00:00Z",
            model_id="meta-llama-3.1-8b-instruct-abliterated",
            thought_summary="Probing debug endpoint with special characters",
            attack_vector="Input Sanitization Probe",
            target_endpoint="openclaw-standalone.trycloudflare.com",
            correlated_ray_id="ray_exact_match_999",
        )

        threat = WAFThreatEvent(
            timestamp="2026-08-28T19:05:00Z",
            action="block",
            rule_id="rule_waf_123",
            source="waf",
            client_ip="198.51.100.42",
            country="AU",
            asn_description="ASN",
            host="openclaw-standalone.trycloudflare.com",
            method="POST",
            path="/debug",
            query_string="",
            user_agent="Agent",
            edge_status=403,
            ray_id="ray_exact_match_999",
            description="Special Characters Filter Block",
        )

        correlated = collector.correlate_thoughts_with_threats([thought], [threat])
        assert len(correlated) == 1
        assert correlated[0].is_blocked is True
        assert correlated[0].correlated_waf_action == "block"
        assert correlated[0].correlated_ray_id == "ray_exact_match_999"

    def test_correlation_temporal_window_boundaries(self):
        """Verify +-15.0 second temporal correlation window boundary behavior."""
        collector = CloudflareTelemetryCollector()
        base_time = datetime(2026, 8, 28, 19, 30, 0, tzinfo=timezone.utc)

        thoughts = [
            RedTeamThoughtTrace(
                timestamp=base_time.isoformat(),
                model_id="llama",
                thought_summary="T0 (0s diff)",
                attack_vector="V0",
                target_endpoint="openclaw",
            ),
            RedTeamThoughtTrace(
                timestamp=(base_time + timedelta(seconds=14.9)).isoformat(),
                model_id="llama",
                thought_summary="T1 (14.9s diff)",
                attack_vector="V1",
                target_endpoint="openclaw",
            ),
            RedTeamThoughtTrace(
                timestamp=(base_time + timedelta(seconds=15.1)).isoformat(),
                model_id="llama",
                thought_summary="T2 (15.1s diff - outside window)",
                attack_vector="V2",
                target_endpoint="openclaw",
            ),
        ]

        threat = WAFThreatEvent(
            timestamp=base_time.isoformat(),
            action="managed_challenge",
            rule_id="rule_waf_99",
            source="waf",
            client_ip="198.51.100.42",
            country="AU",
            asn_description="ASN",
            host="openclaw-standalone.trycloudflare.com",
            method="POST",
            path="/api",
            query_string="",
            user_agent="Agent",
            edge_status=403,
            ray_id="ray_temp_001",
            description="JS Challenge",
        )

        correlated = collector.correlate_thoughts_with_threats(thoughts, [threat])
        assert correlated[0].is_blocked is True
        assert correlated[0].correlated_ray_id == "ray_temp_001"
        assert correlated[1].is_blocked is True
        assert correlated[1].correlated_ray_id == "ray_temp_001"
        assert correlated[2].is_blocked is False
        assert correlated[2].correlated_ray_id is None

    def test_correlation_corrupted_timestamp_strings(self):
        """Verify correlation does not crash when timestamps are invalid or '--'."""
        collector = CloudflareTelemetryCollector()
        thoughts = [
            RedTeamThoughtTrace(
                timestamp="--",
                model_id="llama",
                thought_summary="Invalid timestamp thought",
                attack_vector="V",
                target_endpoint="openclaw",
            ),
            RedTeamThoughtTrace(
                timestamp="Not-A-Date",
                model_id="llama",
                thought_summary="Corrupted string timestamp",
                attack_vector="V",
                target_endpoint="openclaw",
            ),
        ]
        threats = [
            WAFThreatEvent(
                timestamp="--",
                action="block",
                rule_id="r1",
                source="waf",
                client_ip="--",
                country="--",
                asn_description="--",
                host="openclaw",
                method="POST",
                path="/",
                query_string="",
                user_agent="",
                edge_status=403,
                ray_id="ray_invalid",
                description="desc",
            )
        ]
        correlated = collector.correlate_thoughts_with_threats(thoughts, threats)
        assert len(correlated) == 2
        assert correlated[0].is_blocked is False


# ==============================================================================
# Focus Area 5: TUI Markup Injection & Null Field Crash Reproductions
# ==============================================================================

class TestTUIMarkupAndNullSafety:
    """Stress-test TUI widget against unescaped Rich markup injection and null event fields."""

    @pytest.mark.asyncio
    async def test_reproduce_bug_2_and_3_tui_markup_and_null_crashes(self):
        """
        [BUG REPRODUCTION 2 & 3]
        Mount RedBlueArenaWidget in a Textual test app and feed:
        1. Mismatched Rich markup tags in thought stream ('[/blue]', '[/red]').
        2. None/null values in timestamp, action, ray_id, and percentage fields.
        Must NOT raise MarkupError or TypeError during DOM render.
        """
        class ArenaTestApp(App):
            def compose(self) -> ComposeResult:
                yield RedBlueArenaWidget(id="test-arena")

        app = ArenaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#test-arena", RedBlueArenaWidget)

            adversarial_payload = {
                "cloudflare_zero_trust": {
                    "is_configured": True,
                    "status": "HEALTHY",
                    "summary": {
                        "window_minutes": 60,
                        "total_threats_blocked": 1,
                        "total_challenges_issued": 0,
                        "block_rate_pct": None,  # Null percentage
                        "threat_level": "LOW",
                    },
                    "threat_events": [
                        {
                            "timestamp": None,  # Null timestamp
                            "action": None,     # Null action
                            "ray_id": None,     # Null ray_id
                            "path": "/api/v1/[model]/[/red]/query",  # Mismatched closing tag
                            "client_ip": "192.0.2.1",
                            "country": "US",
                            "description": "Malicious [/bold] probe",  # Mismatched closing tag
                            "edge_status": 403,
                        }
                    ],
                    "access_events": [
                        {
                            "timestamp": None,
                            "allowed": True,
                            "user_email": "user[/link]@example.com",
                            "ip_address": "100.1.2.3",
                            "country": None,
                        }
                    ],
                    "red_team_thoughts": [
                        {
                            "timestamp": None,
                            "thought_summary": "Adversarial payload with [/blue] and [invalid tag",
                            "attack_vector": "Vector [/green]",
                        }
                    ],
                    "top_attack_vectors": [{"vector": "SQLi [/red]", "count": 1}],
                    "geo_distribution": [{"country": "US", "count": 1, "pct": None}],
                }
            }

            # This reactive update must render without crashing
            widget.arena_data = adversarial_payload
            await pilot.pause()


# ==============================================================================
# Focus Area 6: Rule #0 Zero-Mock & Unconfigured Invariants
# ==============================================================================

class TestRuleZeroCompliance:
    """Audit for zero-mock invariants, absence of hardcoded fake data, and '--' fallbacks."""

    def test_unconfigured_collector_complete_zero_mock_audit(self):
        """Ensure every single metric field in unconfigured snapshot is '--' or 0."""
        collector = CloudflareTelemetryCollector(
            api_token="",
            zone_id="",
            account_id="",
            thought_log_paths=["/nonexistent/path/thoughts.jsonl"],
        )
        snapshot = collector.get_telemetry_snapshot(time_window_minutes=60)

        assert snapshot.is_configured is False
        assert snapshot.status == "NO_CREDENTIALS"
        assert snapshot.summary.top_attacked_host == "--"
        assert snapshot.summary.top_rule_triggered == "--"
        assert snapshot.summary.last_threat_timestamp == "--"
        assert snapshot.summary.threat_level == "--"
        assert snapshot.summary.total_threats_blocked == 0
        assert snapshot.summary.total_challenges_issued == 0
        assert snapshot.summary.block_rate_pct == 0.0
        assert snapshot.threat_events == []
        assert snapshot.access_events == []
        assert snapshot.top_attack_vectors == []
        assert snapshot.geo_distribution == []
        assert snapshot.tunnel_status == "DISCONNECTED"
        assert snapshot.latency_ms is None

    def test_backend_collector_zero_mock_fallback(self):
        """Verify get_cloudflare_zero_trust_telemetry returns pure zero-mock dict when offline."""
        data = get_cloudflare_zero_trust_telemetry()
        assert isinstance(data, dict)
        if not data.get("is_configured"):
            assert data["summary"]["top_attacked_host"] == "--"
            assert data["summary"]["top_rule_triggered"] == "--"
            assert data["summary"]["threat_level"] == "--"
            assert data["threat_events"] == []
            assert data["access_events"] == []
