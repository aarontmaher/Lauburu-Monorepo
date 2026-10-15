import pytest
import json
import sys
from pathlib import Path
import tempfile
import os

# Add paths
sys.path.insert(0, str(Path("/Volumes/Lauburu-Monorepo/00_core_infrastructure/auth")))
sys.path.insert(0, str(Path("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/notifications")))

from workspace_dwd_gateway import DWDAuthGateway
from google_chat_mesh_bridge import GoogleChatBridge
from google_workspace_unified_manager import GoogleWorkspaceManager


def test_dwd_auth_gateway_initialization():
    gateway = DWDAuthGateway(subject="lauburu@lauburugrappling.com")
    health = gateway.get_gateway_health()
    
    assert health["workspace_domain"] == "lauburugrappling.com"
    assert health["default_subject"] == "lauburu@lauburugrappling.com"
    assert len(health["active_scopes"]) >= 8
    assert "https://www.googleapis.com/auth/chat.bot" in health["active_scopes"]
    assert "https://www.googleapis.com/auth/drive" in health["active_scopes"]


def test_dwd_token_request_offline_fallback():
    gateway = DWDAuthGateway(subject="lauburu@lauburugrappling.com")
    token_resp = gateway.get_bearer_token()
    
    assert token_resp is not None
    assert token_resp["subject"] == "lauburu@lauburugrappling.com"
    assert token_resp["token_type"] == "Bearer"


def test_google_chat_card_v2_schemas():
    bridge = GoogleChatBridge()
    
    # 1. Debate card
    debate_card = bridge.create_ai_debate_card(
        topic="Tri-Orchestrator Google Workspace Integration",
        consensus_summary="Consensus reached with DWD on Port 18802.",
        devils_advocate_verdict="Audited and validated under zero-mock.",
        kappa_score=0.994
    )
    assert "cardId" in debate_card
    assert "sections" in debate_card["card"]
    assert len(debate_card["card"]["sections"]) == 4
    
    # 2. Mesh telemetry card
    mesh_card = bridge.create_mesh_telemetry_card(
        node_count=7,
        pooled_vram_gb=82.8,
        total_ram_gb=108.0,
        tb4_latency_ms=0.277
    )
    assert "82.8 GB" in str(mesh_card)
    assert "0.277 ms RTT" in str(mesh_card)
    
    # 3. Biometrics card
    bio_card = bridge.create_biometrics_alert_card(
        heart_rate=142,
        zone="Zone 2",
        dfa_alpha1=0.85,
        alert_message="Steady state aerobic heart rate target achieved."
    )
    assert "142 BPM" in str(bio_card)
    assert "0.85" in str(bio_card)


def test_workspace_manager_formats():
    mgr = GoogleWorkspaceManager(subject="lauburu@lauburugrappling.com")
    
    # Gmail Alert
    gmail_alert = mgr.format_gmail_alert(
        recipient="ops@lauburugrappling.com",
        subject="High GPU Thermal Alert",
        body="L1 Host Mac Mini CPU temperature is 88C."
    )
    assert gmail_alert["from"] == "lauburu@lauburugrappling.com"
    assert "[LAUBURU-MESH]" in gmail_alert["subject"]
    assert gmail_alert["headers"]["X-Priority"] == "1"
    
    # Sheets Telemetry Row
    row = mgr.format_sheets_telemetry_row(
        metric_type="BIOMETRICS_ZONE2",
        values={"hr": 140, "dfa": 0.88, "status": "OPTIMAL"}
    )
    assert len(row) == 4
    assert row[1] == "BIOMETRICS_ZONE2"
    assert "lauburu@lauburugrappling.com" in row[3]


def test_workspace_manager_status_inspection():
    mgr = GoogleWorkspaceManager(subject="lauburu@lauburugrappling.com")
    status = mgr.get_full_workspace_status()
    
    assert status["domain"] == "lauburugrappling.com"
    assert status["primary_account"] == "lauburu@lauburugrappling.com"
    assert status["google_drive"]["status"] == "ENABLED"
    assert status["gmail_alert_bus"]["status"] == "ENABLED"
    assert status["sheets_telemetry"]["status"] == "ENABLED"
