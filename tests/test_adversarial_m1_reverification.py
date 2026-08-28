#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Lauburu Mesh Ecosystem — Milestone 1 Adversarial Re-verification Suite (Round 2)
Challenger: Challenger 1 (Empirical Challenger)
Verification Target: Remediation of 5 Critical/Medium Defects from Round 1
==============================================================================
"""

import os
import sys
import json
import tempfile
import pytest
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
from textual.app import App, ComposeResult
from rich.console import Console


# ==============================================================================
# Verification 1: Bug 1 — Null action handling in snapshot calculation & correlation
# ==============================================================================

class TestBug1NullActionSafety:
    """Empirical verification that action=None or malformed actions never raise TypeError."""

    def test_null_action_in_snapshot(self):
        collector = CloudflareTelemetryCollector(api_token="test_token", zone_id="test_zone")
        threats = [
            WAFThreatEvent(
                timestamp="2026-08-28T20:00:00Z",
                action=None,
                rule_id="r1",
                source="waf",
                client_ip="192.0.2.1",
                country="US",
                asn_description="ASN",
                host="openclaw-standalone.trycloudflare.com",
                method="POST",
                path="/test",
                query_string="",
                user_agent="Agent",
                edge_status=403,
                ray_id="ray_null_1",
                description="desc",
            ),
            WAFThreatEvent(
                timestamp="2026-08-28T20:01:00Z",
                action="",
                rule_id="r2",
                source="waf",
                client_ip="192.0.2.2",
                country="AU",
                asn_description="ASN",
                host="openclaw-standalone.trycloudflare.com",
                method="GET",
                path="/test2",
                query_string="",
                user_agent="Agent",
                edge_status=403,
                ray_id="ray_null_2",
                description="desc",
            ),
            WAFThreatEvent(
                timestamp="2026-08-28T20:02:00Z",
                action="block",
                rule_id="r3",
                source="waf",
                client_ip="192.0.2.3",
                country="GB",
                asn_description="ASN",
                host="openclaw-standalone.trycloudflare.com",
                method="POST",
                path="/test3",
                query_string="",
                user_agent="Agent",
                edge_status=403,
                ray_id="ray_block_1",
                description="desc",
            ),
            WAFThreatEvent(
                timestamp="2026-08-28T20:03:00Z",
                action="managed_challenge",
                rule_id="r4",
                source="waf",
                client_ip="192.0.2.4",
                country="JP",
                asn_description="ASN",
                host="openclaw-standalone.trycloudflare.com",
                method="POST",
                path="/test4",
                query_string="",
                user_agent="Agent",
                edge_status=403,
                ray_id="ray_chal_1",
                description="desc",
            ),
        ]

        with patch.object(collector, "fetch_waf_threats", return_value=threats), \
             patch.object(collector, "fetch_access_authentications", return_value=[]), \
             patch.object(collector, "fetch_red_team_thoughts", return_value=[]):
            
            snapshot = collector.get_telemetry_snapshot()
            assert snapshot.summary.total_threats_blocked == 1
            assert snapshot.summary.total_challenges_issued == 1
            assert snapshot.status == "HEALTHY"

    def test_null_action_in_correlation_engine(self):
        collector = CloudflareTelemetryCollector()
        thought = RedTeamThoughtTrace(
            timestamp="2026-08-28T20:00:00Z",
            model_id="llama",
            thought_summary="thought summary",
            attack_vector="vector",
            target_endpoint="openclaw",
            correlated_ray_id="ray_match_null_action",
        )
        threat_null_action = WAFThreatEvent(
            timestamp="2026-08-28T20:00:00Z",
            action=None,
            rule_id="r",
            source="waf",
            client_ip="1.1.1.1",
            country="US",
            asn_description="ASN",
            host="openclaw",
            method="POST",
            path="/",
            query_string="",
            user_agent="",
            edge_status=403,
            ray_id="ray_match_null_action",
            description="desc",
        )
        correlated = collector.correlate_thoughts_with_threats([thought], [threat_null_action])
        assert len(correlated) == 1
        assert correlated[0].is_blocked is False
        assert correlated[0].correlated_waf_action is None


# ==============================================================================
# Verification 2: Bug 2 — Rich Markup Injection Escaping
# ==============================================================================

class TestBug2RichMarkupEscaping:
    """Empirical verification that hostile Rich markup strings never crash TUI or CLI."""

    @pytest.mark.asyncio
    async def test_adversarial_rich_markup_in_tui_widget(self):
        class ArenaApp(App):
            def compose(self) -> ComposeResult:
                yield RedBlueArenaWidget(id="arena")

        app = ArenaApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#arena", RedBlueArenaWidget)

            hostile_payload = {
                "cloudflare_zero_trust": {
                    "is_configured": True,
                    "status": "[/bold]HEALTHY[/red]",
                    "tunnel_endpoint": "openclaw[/blue].trycloudflare.com",
                    "tunnel_status": "[/green]ONLINE[/]",
                    "latency_ms": 35.4,
                    "summary": {
                        "window_minutes": 60,
                        "total_threats_blocked": 5,
                        "total_challenges_issued": 2,
                        "block_rate_pct": 12.5,
                        "threat_level": "CRITICAL[/red][/bold]",
                    },
                    "threat_events": [
                        {
                            "timestamp": "2026-08-28T20:00:00Z",
                            "action": "[/red]block[/]",
                            "client_ip": "[red]10.0.0.1[/red]",
                            "country": "[blue]AU[/blue]",
                            "path": "/v1/api/[model]/[/red]execute?eval=[/bold]",
                            "description": "Exploit: [/cyan]SQL Injection[/cyan] [1' OR '1'='1]",
                            "ray_id": "[yellow]ray_malicious_12345[/yellow]",
                            "edge_status": 403,
                        }
                    ],
                    "access_events": [
                        {
                            "timestamp": "2026-08-28T20:00:00Z",
                            "user_email": "attacker[/red][link]evil@domain.com",
                            "app_domain": "app[/blue].domain.com",
                            "allowed": False,
                            "ip_address": "[dim]10.1.1.1[/dim]",
                            "country": "[bold]US[/bold]",
                        }
                    ],
                    "red_team_thoughts": [
                        {
                            "timestamp": "2026-08-28T20:00:00Z",
                            "thought_summary": "Attempting payload: [/blue] [bold] <think>[/red] drop table users; --",
                            "attack_vector": "SQLi [/yellow][/magenta]",
                            "raw_think_block": "<think>Testing tag [link=https://evil.com]click me[/link]</think>",
                        }
                    ],
                    "top_attack_vectors": [
                        {"vector": "SQL Injection [/red]", "count": 10},
                        {"vector": "Prompt Bypass [/blue][/bold]", "count": 4},
                    ],
                    "geo_distribution": [
                        {"country": "AU[/green]", "count": 10, "pct": 71.4},
                        {"country": "US[/red]", "count": 4, "pct": 28.6},
                    ],
                }
            }

            widget.arena_data = hostile_payload
            await pilot.pause()
            # If no MarkupError was raised, test passes

    def test_adversarial_rich_markup_in_cli_dashboard(self):
        console = Console(record=True, width=120)
        snapshot = CloudflareTelemetrySnapshot(
            timestamp="2026-08-28T20:00:00Z",
            is_configured=True,
            status="HEALTHY[/red]",
            status_message="Active[/blue]",
            summary=WAFTelemetrySummary(
                window_minutes=60,
                total_threats_blocked=3,
                total_challenges_issued=1,
                top_attacked_host="openclaw[/bold].trycloudflare.com",
                top_rule_triggered="Rule [/yellow] 1234",
                last_threat_timestamp="2026-08-28T20:00:00Z",
                block_rate_pct=15.0,
                threat_level="CRITICAL[/red]",
            ),
            threat_events=[
                WAFThreatEvent(
                    timestamp="2026-08-28T20:00:00Z",
                    action="block[/red]",
                    rule_id="r1",
                    source="waf",
                    client_ip="192.0.2.1[/cyan]",
                    country="AU[/bold]",
                    asn_description="ASN",
                    host="openclaw[/blue]",
                    method="POST",
                    path="/api/[model]/[/red]query",
                    query_string="q=[/bold]",
                    user_agent="Agent[/yellow]",
                    edge_status=403,
                    ray_id="ray_cli_[/red]_123",
                    description="Malicious [/blue] probe",
                )
            ],
            access_events=[
                AccessAuthEvent(
                    timestamp="2026-08-28T20:00:00Z",
                    app_domain="app[/bold]",
                    app_uid="uid1",
                    action="login",
                    allowed=True,
                    connection_type="saml",
                    country="AU",
                    ip_address="192.0.2.1",
                    ray_id="ray_acc_1",
                    user_email="user[/red]@domain.com",
                )
            ],
            red_team_thoughts=[
                RedTeamThoughtTrace(
                    timestamp="2026-08-28T20:00:00Z",
                    model_id="llama-3.1[/red]",
                    thought_summary="Probing with [/blue] tags",
                    attack_vector="Vector [/green]",
                    target_endpoint="openclaw[/yellow]",
                    is_blocked=True,
                    correlated_waf_action="block[/red]",
                )
            ],
            tunnel_endpoint="openclaw[/cyan]",
            tunnel_status="ONLINE[/green]",
            latency_ms=45.0,
        )

        # Must not raise MarkupError
        render_cli_dashboard(snapshot, console)
        output = console.export_text()
        assert "LAUBURU CLOUDFLARE ZERO TRUST" in output


# ==============================================================================
# Verification 3: Bug 3 — None Safety in Formatting, Slicing, and Calculations
# ==============================================================================

class TestBug3NoneSafety:
    """Empirical verification that None values in percentages, timestamps, and ray IDs never crash."""

    @pytest.mark.asyncio
    async def test_all_none_fields_in_tui_widget(self):
        class ArenaApp(App):
            def compose(self) -> ComposeResult:
                yield RedBlueArenaWidget(id="arena")

        app = ArenaApp()
        async with app.run_test() as pilot:
            widget = app.query_one("#arena", RedBlueArenaWidget)

            all_none_payload = {
                "cloudflare_zero_trust": {
                    "is_configured": True,
                    "status": None,
                    "tunnel_endpoint": None,
                    "tunnel_status": None,
                    "latency_ms": None,
                    "summary": {
                        "window_minutes": None,
                        "total_threats_blocked": None,
                        "total_challenges_issued": None,
                        "block_rate_pct": None,
                        "threat_level": None,
                        "top_attacked_host": None,
                        "top_rule_triggered": None,
                        "last_threat_timestamp": None,
                    },
                    "threat_events": [
                        {
                            "timestamp": None,
                            "action": None,
                            "client_ip": None,
                            "country": None,
                            "path": None,
                            "description": None,
                            "rule_id": None,
                            "ray_id": None,
                            "edge_status": None,
                        }
                    ],
                    "access_events": [
                        {
                            "timestamp": None,
                            "user_email": None,
                            "app_domain": None,
                            "allowed": None,
                            "ip_address": None,
                            "country": None,
                        }
                    ],
                    "red_team_thoughts": [
                        {
                            "timestamp": None,
                            "thought_summary": None,
                            "attack_vector": None,
                            "raw_think_block": None,
                            "correlated_waf_action": None,
                        }
                    ],
                    "top_attack_vectors": [
                        {"vector": None, "count": None}
                    ],
                    "geo_distribution": [
                        {"country": None, "count": None, "pct": None}
                    ],
                }
            }

            widget.arena_data = all_none_payload
            await pilot.pause()

    def test_cli_dashboard_with_all_none_fields(self):
        console = Console(record=True, width=120)
        snapshot = CloudflareTelemetrySnapshot(
            timestamp="2026-08-28T20:00:00Z",
            is_configured=True,
            status=None,
            status_message=None,
            summary=WAFTelemetrySummary(
                window_minutes=60,
                total_threats_blocked=None,
                total_challenges_issued=None,
                top_attacked_host=None,
                top_rule_triggered=None,
                last_threat_timestamp=None,
                block_rate_pct=None,
                threat_level=None,
            ),
            threat_events=[
                WAFThreatEvent(
                    timestamp=None,
                    action=None,
                    rule_id=None,
                    source=None,
                    client_ip=None,
                    country=None,
                    asn_description=None,
                    host=None,
                    method=None,
                    path=None,
                    query_string=None,
                    user_agent=None,
                    edge_status=None,
                    ray_id=None,
                    description=None,
                )
            ],
            access_events=[],
            red_team_thoughts=[
                RedTeamThoughtTrace(
                    timestamp=None,
                    model_id=None,
                    thought_summary=None,
                    attack_vector=None,
                    target_endpoint=None,
                    raw_think_block=None,
                    correlated_ray_id=None,
                    correlated_waf_action=None,
                    is_blocked=False,
                )
            ],
            tunnel_endpoint=None,
            tunnel_status=None,
            latency_ms=None,
        )

        render_cli_dashboard(snapshot, console)
        output = console.export_text()
        assert "LAUBURU CLOUDFLARE ZERO TRUST" in output


# ==============================================================================
# Verification 4: Bug 4 — Per-Line Exception Handling in Thought Log Reading
# ==============================================================================

class TestBug4PerLineJsonParsing:
    """Empirical verification that corrupted lines in .jsonl do not drop valid records."""

    def test_corrupted_jsonl_partial_lines_resilience(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".jsonl", delete=False) as tf:
            # Line 1: Valid
            tf.write(json.dumps({
                "timestamp": "2026-08-28T20:00:00Z",
                "model_id": "llama-8b-abliterated",
                "thought_summary": "Valid thought 1",
                "attack_vector": "Vector 1",
                "target_endpoint": "openclaw",
            }) + "\n")
            # Line 2: Corrupted JSON (syntax error)
            tf.write("{\"timestamp\": \"2026-08-28T20:00:01Z\", \"broken\": \n")
            # Line 3: Valid
            tf.write(json.dumps({
                "timestamp": "2026-08-28T20:00:02Z",
                "model_id": "llama-8b-abliterated",
                "thought_summary": "Valid thought 2",
                "attack_vector": "Vector 2",
                "target_endpoint": "openclaw",
            }) + "\n")
            # Line 4: Non-dict valid JSON
            tf.write("\"just a json string\"\n")
            # Line 5: Empty line
            tf.write("\n")
            # Line 6: Valid
            tf.write(json.dumps({
                "timestamp": "2026-08-28T20:00:03Z",
                "model_id": "llama-8b-abliterated",
                "thought_summary": "Valid thought 3",
                "attack_vector": "Vector 3",
                "target_endpoint": "openclaw",
            }) + "\n")
            temp_path = tf.name

        try:
            collector = CloudflareTelemetryCollector(thought_log_paths=[temp_path])
            traces = collector.fetch_red_team_thoughts(limit=10)
            assert len(traces) == 3, f"Expected 3 valid traces to survive, got {len(traces)}"
            summaries = {t.thought_summary for t in traces}
            assert "Valid thought 1" in summaries
            assert "Valid thought 2" in summaries
            assert "Valid thought 3" in summaries
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


# ==============================================================================
# Verification 5: Bug 5 — Explicit JSON null fallback in dataclass instantiation
# ==============================================================================

class TestBug5ExplicitJsonNullFallback:
    """Empirical verification that JSON nulls in raw payloads produce clean default strings."""

    def test_graphql_explicit_null_fields_conversion(self):
        collector = CloudflareTelemetryCollector(api_token="test_tok", zone_id="test_zone")
        raw_null_graphql = {
            "data": {
                "viewer": {
                    "zones": [
                        {
                            "firewallEventsAdaptive": [
                                {
                                    "datetime": None,
                                    "action": None,
                                    "ruleId": None,
                                    "source": None,
                                    "clientIP": None,
                                    "clientCountryName": None,
                                    "clientASNDescription": None,
                                    "clientRequestHTTPHost": None,
                                    "clientRequestHTTPMethodName": None,
                                    "clientRequestPath": None,
                                    "clientRequestQuery": None,
                                    "userAgent": None,
                                    "edgeResponseStatus": None,
                                    "rayName": None,
                                    "description": None,
                                    "ref": None,
                                }
                            ]
                        }
                    ]
                }
            }
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = raw_null_graphql
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            threats = collector.fetch_waf_threats()
            assert len(threats) == 1
            t = threats[0]
            assert t.timestamp == "--"
            assert t.action == "unknown"
            assert t.rule_id == "--"
            assert t.source == "--"
            assert t.client_ip == "--"
            assert t.country == "--"
            assert t.asn_description == "--"
            assert t.host == "--"
            assert t.method == "--"
            assert t.path == "--"
            assert t.query_string == ""
            assert t.user_agent == "--"
            assert t.edge_status == 403
            assert t.ray_id == "--"
            assert t.description == "--"
            assert t.ref == ""

    def test_access_explicit_null_fields_conversion(self):
        collector = CloudflareTelemetryCollector(api_token="test_tok", account_id="test_acc")
        raw_null_access = {
            "result": [
                {
                    "created_at": None,
                    "app_domain": None,
                    "app_uid": None,
                    "action": None,
                    "allowed": None,
                    "connection": None,
                    "country": None,
                    "ip_address": None,
                    "ray_id": None,
                    "user_email": None,
                }
            ]
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = raw_null_access
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            access_logs = collector.fetch_access_authentications()
            assert len(access_logs) == 1
            a = access_logs[0]
            assert a.timestamp == "--"
            assert a.app_domain == "--"
            assert a.app_uid == "--"
            assert a.action == "login"
            assert a.allowed is False
            assert a.connection_type == "--"
            assert a.country == "--"
            assert a.ip_address == "--"
            assert a.ray_id == "--"
            assert a.user_email == "--"
